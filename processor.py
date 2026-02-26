import tempfile
import os
import pandas as pd
import ollama  
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredExcelLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
try:
    from langchain.retrievers import EnsembleRetriever
except ImportError:
    from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.documents import Document
from graph import crag_graph   # Phase 1: LangGraph CRAG graph

# Uses local ollama nomic-embed-text model — no torch/HuggingFace required
embedding_model = OllamaEmbeddings(model="nomic-embed-text")

def process_uploaded_file(filename, content):
    """
    Ingests PDF, DOCX, XLSX, CSV, TXT, or MD.
    Handles multiple Excel sheets and merged cells better, and returns the vector store.
    """
    # save to temp file (preserving extension -crucial)
    file_ext = os.path.splitext(filename)[1].lower()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        tmp_file.write(content)
        tmp_path = tmp_file.name

    try:
        loader = None
        raw_docs = []

        # pdf
        if file_ext == ".pdf":
            loader = PyPDFLoader(tmp_path)
            raw_docs = loader.load()

        # excel with both extensions
        elif file_ext in [".xlsx", ".xls"]:
            xls = pd.read_excel(tmp_path, sheet_name=None)
            full_text = []
            
            for sheet_name, df in xls.items():
                # force headers to string to avoid type errors
                df.columns = df.columns.astype(str)
                
                # explicit schema extraction
                columns_list = ", ".join(list(df.columns))
                
                # clean NaN
                df = df.fillna("")
                
                # data card for the LLM
                sheet_content = f"""
                --- SHEET: {sheet_name} ---
                COLUMN HEADERS: [{columns_list}]
                
                FIRST 20 ROWS OF DATA:
                {df.head(20).to_markdown(index=False)}
                
                FULL DATA (Markdown):
                {df.to_markdown(index=False)}
                """
                full_text.append(sheet_content)
            
            text_content = "\n".join(full_text)
            raw_docs = [Document(page_content=text_content, metadata={"source": uploaded_file.name})]
        
        # CSV
        elif file_ext == ".csv":
            df = pd.read_csv(tmp_path)
            
            # Explicit Schema (as it threw error in finding column headers)
            df.columns = df.columns.astype(str)
            columns_list = ", ".join(list(df.columns))
            
            # Data Card
            df = df.fillna("")
            text_content = f"""
            FILE: {uploaded_file.name}
            COLUMN HEADERS: [{columns_list}]
            
            FIRST 20 ROWS SAMPLE:
            {df.head(20).to_markdown(index=False)}
            
            FULL DATA:
            {df.to_markdown(index=False)}
            """
            raw_docs = [Document(page_content=text_content, metadata={"source": uploaded_file.name})]

        # TXT, MD, PY
        elif file_ext in [".txt", ".md", ".py"]:
            try:
                loader = TextLoader(tmp_path, encoding="utf-8")
                raw_docs = loader.load()
            except Exception:
                # Fallback to latin-1 if utf-8 fails (common for some Windows files)
                loader = TextLoader(tmp_path, encoding="ISO-8859-1")
                raw_docs = loader.load()
        
        # Word
        elif file_ext == ".docx":
            from langchain_community.document_loaders import Docx2txtLoader
            loader = Docx2txtLoader(tmp_path)
            raw_docs = loader.load()

        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

        
        # Final Splitting & Vectorizing
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500, 
            chunk_overlap=150,
            add_start_index=True
        )
        chunks = text_splitter.split_documents(raw_docs)
        
        # 1. Semantic Retriever (FAISS)
        vector_store = FAISS.from_documents(chunks, embedding_model)
        faiss_retriever = vector_store.as_retriever(search_kwargs={"k": 5})

        # 2. Keyword Retriever (BM25)
        bm25_retriever = BM25Retriever.from_documents(chunks)
        bm25_retriever.k = 5

        # 3. Hybrid Ensemble (RRF)
        # Weights: 70% Semantic, 30% Keyword - good balance for documents
        hybrid_retriever = EnsembleRetriever(
            retrievers=[faiss_retriever, bm25_retriever], 
            weights=[0.7, 0.3]
        )

        return hybrid_retriever, len(chunks)

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def query_local_model(query, retriever):
    """
    Phase 1 Upgrade: Delegates to the LangGraph CRAG graph instead of a linear call.

    Returns:
        answer (str)      — the generated text
        sources (list)    — docs used for generation (relevant ones, or all retrieved as fallback)
        grade_log (list)  — [{chunk_preview, is_relevant, reason}, ...] for the UI trace
    """
    initial_state = {
        "query": query,
        "original_query": query,
        "retriever": retriever,
        "documents": [],
        "relevant_docs": [],
        "generation": "",
        "retries": 0,
        "grade_log": [],
    }

    final_state = crag_graph.invoke(initial_state)

    answer = final_state.get("generation", "No answer generated.")
    sources = final_state.get("relevant_docs") or final_state.get("documents", [])
    grade_log = final_state.get("grade_log", [])

    return answer, sources, grade_log


def extract_search_keyword(user_query):
    """
    Uses Llama 3 to turn a complex sentence into a simple filename keyword.
    Example: "Show me the notes about Solar" -> "Solar"
    """
    system_prompt = """
    You are a Search Query Extractor.
    Extract the single most likely FILENAME keyword or TOPIC from the user's request.
    
    Rules:
    - Return ONLY the keyword.
    - No explanations.
    - If the user asks "Show me the budget", return "budget".
    - If the user asks "Read the file named data.csv", return "data".
    
    User Query:
    """
    
    try:
        response = ollama.chat(model='llama3.2', messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_query},
        ])
        # extra whitespace or punctuation the model added, has to be removed
        keyword = response['message']['content'].strip().replace('"', '').replace("'", "")
        return keyword
    except Exception as e:
        return user_query # fallback