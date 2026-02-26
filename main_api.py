from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import ollama
from processor import process_uploaded_file, query_local_model, extract_search_keyword
from disk_ops import DiskScout

app = FastAPI(title="DocuSenseAI API", version="2.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
class AppState:
    def __init__(self):
        self.retriever = None
        self.disk_scout = DiskScout()

state = AppState()

# Models
class QueryRequest(BaseModel):
    query: str
    mode: str = "Uploaded Documents" # "Uploaded Documents" or "Local Disk Scout"

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    grade_log: Optional[List[dict]] = None
    mode: str

class PathRequest(BaseModel):
    path: str

class ScoutRequest(BaseModel):
    query: str

@app.get("/")
async def root():
    return {"message": "Welcome to DocuSenseAI API v2.0", "status": "running"}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        content = await file.read()
        retriever, count = process_uploaded_file(file.filename, content)
        state.retriever = retriever
        return {"message": f"Successfully indexed {count} chunks from {file.filename}", "chunks": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query_ai(request: QueryRequest):
    if request.mode == "Uploaded Documents":
        if not state.retriever:
            raise HTTPException(status_code=400, detail="Please upload a document first.")
        
        answer, sources, grade_log = query_local_model(request.query, state.retriever)
        # Convert sources (list of Document) to list of strings
        source_texts = [doc.page_content for doc in sources]
        
        return QueryResponse(
            answer=answer,
            sources=source_texts,
            grade_log=grade_log,
            mode=request.mode
        )
    
    elif request.mode == "Local Disk Scout":
        keyword = extract_search_keyword(request.query)
        matches = state.disk_scout.scout_files(keyword)
        
        if not matches:
            return QueryResponse(
                answer=f"No files found containing '{keyword}'.",
                sources=[],
                mode=request.mode
            )
        
        file_contents = []
        source_paths = []
        for m in matches:
            content = state.disk_scout.read_file_lazy(m)
            file_contents.append(f"FILENAME: {m.name}\nCONTENT: {content[:4000]}...")
            source_paths.append(str(m))
            
        context_text = "\n\n".join(file_contents)
        system_prompt = f"""
        You are DocuSenseAI. 
        The user has asked a question about these specific local files.
        
        USER INSTRUCTION: {request.query}
        
        FILES FOUND:
        {context_text}
        
        Instructions:
        - If the user asks to "write the content", output the file content verbatim.
        - If the user asks for a summary, summarize.
        - Explicitly mention which file you are reading.
        """
        
        response = ollama.chat(model='phi3', messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': "Execute the instruction based on the files above."},
        ])
        
        return QueryResponse(
            answer=response['message']['content'],
            sources=source_paths,
            mode=request.mode
        )
    
    else:
        raise HTTPException(status_code=400, detail="Invalid search mode.")

@app.post("/disk/add-path")
async def add_disk_path(request: PathRequest):
    success, msg = state.disk_scout.add_path(request.path)
    if success:
        return {"message": msg, "path": request.path}
    else:
        raise HTTPException(status_code=400, detail=msg)

@app.get("/disk/paths")
async def get_disk_paths():
    return {"allowed_paths": [str(p) for p in state.disk_scout.allowed_paths]}

@app.delete("/memory")
async def clear_memory():
    state.retriever = None
    state.disk_scout = DiskScout()
    return {"message": "Memory cleared successfully."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
