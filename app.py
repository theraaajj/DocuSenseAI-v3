import streamlit as st
from processor import process_uploaded_file, query_local_model
from disk_ops import DiskScout

st.set_page_config(page_title="DocuSenseAI v2.0", layout="wide")

# initialize session state initialization
if "disk_scout" not in st.session_state:
    st.session_state.disk_scout = DiskScout()
if "retriever" not in st.session_state:
    st.session_state.retriever = None

# sidebar for memory control and uploads, access!! 
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/artificial-intelligence.png", width=50)
    st.title("DocuSenseAI")
    st.caption("v2.0 | Local | Privacy-First | Agentic CRAG")
    st.divider()

    st.caption("Memory Control")
    # Clear Memory Button
    if st.button("🗑️ Forget All Data"):
        st.session_state.retriever = None
        st.session_state.disk_scout = DiskScout() # Re-init to clear paths
        st.rerun() # refreshes the app

    st.divider()
    
    # Uploads (Deep Read)
    uploaded_file = st.file_uploader("Upload Document", type=["pdf", "docx", "xlsx", "csv", "txt", "md"])    
    if uploaded_file and st.button("Process Upload"):
        with st.spinner("Ingesting..."):
            retriever, count = process_uploaded_file(uploaded_file.name, uploaded_file.getvalue())
            st.session_state.retriever = retriever
            st.success(f"Indexed {count} chunks.")

    st.divider()

    # Local Disk (The Scout)
    folder_path = st.text_input("Add Folder Path (e.g., C:/Projects)")
    if st.button("Grant Permission"):
        success, msg = st.session_state.disk_scout.add_path(folder_path)
        if success:
            st.success(msg)
        else:
            st.error(msg)
            
    # Show Active Permissions
    if st.session_state.disk_scout.allowed_paths:
        st.caption("✅ Active Folders:")
        for p in st.session_state.disk_scout.allowed_paths:
            st.code(str(p))

# main UI
st.subheader("Let's Reason! - Ask DocuSenseAI")
st.caption("Your AI-powered assistant who respects your privacy..")
st.divider()

# asks to select mode, from uploaded documents or local disk scout
search_mode = st.radio("Search Mode:", ["Uploaded Documents", "Local Disk Scout"], horizontal=True)
st.divider()

query = st.text_input("What are you looking for?")


if query and st.button("Ask AI"):
    
    # ── UPLOADED DOCUMENTS (Phase 1: CRAG Agentic Flow) ──────────────────────────
    if search_mode == "Uploaded Documents":
        if st.session_state.retriever:
            with st.spinner("🧠 Agent reasoning..."):
                answer, sources, grade_log = query_local_model(query, st.session_state.retriever)

            st.markdown("### 🤖 Answer:")
            st.write(answer)
            st.divider()

            # ── Agent Reasoning Trace ────────────────────────────────────────────
            if grade_log:
                relevant_count = sum(1 for g in grade_log if g["is_relevant"])
                total_count = len(grade_log)
                rewrites = 0
                # infer rewrites: if any query rewrite happened, sources < grade_log implies looping
                # (we can surface retry count when we add it to state later)

                with st.expander(f"🧠 Agent Reasoning Trace  —  {relevant_count}/{total_count} chunks passed grading"):
                    for i, entry in enumerate(grade_log):
                        icon = "✅" if entry["is_relevant"] else "❌"
                        relevance_label = "Relevant" if entry["is_relevant"] else "Irrelevant"
                        st.markdown(f"**Chunk {i+1}** {icon} `{relevance_label}`")
                        st.caption(f"💬 Grader: _{entry['reason']}_")
                        with st.expander(f"Preview chunk {i+1}", expanded=False):
                            st.text(entry["chunk_preview"])
                        st.divider()

                    if relevant_count == 0:
                        st.warning("⚠️ All chunks were graded irrelevant. A query rewrite was attempted before generating the final answer.")
                    elif relevant_count < total_count:
                        st.info(f"ℹ️ {total_count - relevant_count} chunk(s) were filtered out. Answer was generated from the {relevant_count} relevant chunk(s).")
                    else:
                        st.success("✅ All chunks passed grading. Answer generated from full context.")

            # ── Source Chunks ────────────────────────────────────────────────────
            with st.expander("📄 View Source Chunks Used"):
                for doc in sources:
                    st.info(doc.page_content)
        else:
            st.error("Please upload a document first.")

    # ── LOCAL DISK SCOUT (unchanged) ─────────────────────────────────────────────
    elif search_mode == "Local Disk Scout":
        from processor import extract_search_keyword
        
        with st.spinner("Deciding what to search for..."):
            keyword = extract_search_keyword(query)
            st.caption(f"🔍 Searching for files matching: **'{keyword}'**")

        # SCOUT
        with st.spinner(f"Scanning disk..."):
            matches = st.session_state.disk_scout.scout_files(keyword)
        
        if not matches:
            st.warning(f"No files found containing '{keyword}'. Try specifying the filename explicitly (e.g., 'Check the notes file').")
        else:
            st.success(f"Found {len(matches)} files.")
            
            # read and reason..
            file_contents = []
            for m in matches:
                content = st.session_state.disk_scout.read_file_lazy(m)
                # limited content size avoids crashing 
                file_contents.append(f"FILENAME: {m.name}\nCONTENT: {content[:4000]}...")
            
            with st.spinner("Reading & Generating Answer..."):
                import ollama
                context_text = "\n\n".join(file_contents)
                
                system_prompt = f"""
                You are DocuSenseAI. 
                The user has asked a question about these specific local files.
                
                USER INSTRUCTION: {query}
                
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
                
                st.markdown("### 🤖 Local Insight:")
                st.write(response['message']['content'])
                
                st.divider()
                st.write("📂 **Files Accessed:**")
                for m in matches:
                    st.code(str(m))