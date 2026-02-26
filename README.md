# 🧠 DocuSenseAI v3: Full-Stack Agentic Reasoning Engine

![Status](https://img.shields.io/badge/Status-v3.0_Stable-brightgreen)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Frontend](https://img.shields.io/badge/Frontend-React_Vite-61dafba)
![API](https://img.shields.io/badge/API-FastAPI-009688)

**DocuSenseAI v3** is the production-grade evolution of privacy-first local reasoning. It combines a high-performance **FastAPI** backend, a **React/Vite** premium dashboard, and an **Agentic CRAG (Corrective RAG)** brain to provide a complete, air-gapped solution for document intelligence and local file scouting.

Unlike standard RAG (Retrieval-Augmented Generation) wrappers, this project implements a custom **"Lazy Discovery" architecture** that allows users to query their local hard drive *without* pre-indexing the entire disk, ensuring maximum privacy and minimal resource footprint.

---

## 🚀 Key Differentiators

### 1. Privacy-by-Constraint ("The Glass Box")
* **Zero Telemetry:** The system runs fully offline. Network calls to external APIs are architecturally impossible in the inference layer.
* **Transparency:** Every answer provides citations (Source Chunks). If the model "reads" a file, the user sees it in the Transparency Panel.

### 2. The "Disk Scout" Architecture (Novelty)
Instead of building a massive vector database of the user's entire hard drive (invasive & slow), DocuSenseAI does it as and when needed:
1.  **Intent Parsing:** A lightweight LLM extracts specific target keywords from natural language queries.
2.  **Deterministic Filtering:** The system scans file metadata in allowed folders.
3.  **Lazy Loading:** Only relevant files are opened, tokenized, and injected into the context window at query time.

### 3. Agentic Brain (CRAG)
Unlike linear RAG, v3 implements **Corrective RAG** via LangGraph. The system doesn't just retrieve context—it **grades** it. If the retrieved information is irrelevant, the Agent automatically rewrites the query and tries again, significantly reducing hallucinations.

### 4. Full-Stack Architecture
Separating the **Reasoning API** from the **Frontend Dashboard** allows for professional deployment, external tool integration, and a premium user experience beyond basic script interfaces.

---

## 🔄 Why DocuSenseAI v3? (The Evolution)

**v3** transforms the project from an interactive prototype into a professional-grade software stack.

| Feature | v2 (The Engine) | v3 (The Full-Stack Release) |
| :--- | :--- | :--- |
| **Architecture** | Monolithic Streamlit App | **Decoupled:** FastAPI Backend + React Frontend. |
| **RAG Logic** | Linear Retrieval | **Agentic CRAG:** Self-correcting retrieval using LangGraph. |
| **UI/UX** | Standard Streamlit Layout | **Premium Dashboard:** Custom Glassmorphism, real-time message animations, and dedicated source modals. |
| **Transparency** | Basic text citations | **Reasoning Trace Panel:** Visual breakdown of chunk relevance grading and decision logic. |
| **Interoperability** | UI-only | **RESTful API:** Can be queried by external apps via standard POST requests. |

---

## 🛠️ Tech Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Logic Layer** | FastAPI + Python | High-performance REST API and process management. |
| **Agentic Brain** | LangGraph (CRAG) | Agentic Corrective RAG state machine for self-correcting retrieval. |
| **Frontend** | React + Vite | Premium, reactive web dashboard with glassmorphism. |
| **Inference** | Ollama (Phi-3 / Llama 3.2) | Local LLM serving and context management. |
| **Vector Store** | FAISS + BM25 | Hybrid Ensemble Retriever (Semantic + Keyword). |
| **Legacy UI** | Streamlit | Quick-turnaround prototyping interface. |

---

## ⚡ Feature Spotlight: Smart Data Ingestion

LLMs notoriously struggle with **Excel** and **CSV** files due to tokenization limits and lost headers. DocuSenseAI v2 implements a custom **Schema Injection Pipeline**:

* **Multi-Sheet Awareness:** Automatically iterates through all Excel sheets.
* **Header Anchoring:** Extracts `df.columns` and explicitly injects a "Data Card" (Schema) at the top of the context window.
* **Result:** The model can accurately identify column names and data relationships even in messy, merged-cell spreadsheets.

---

## 💻 Installation & Usage

### Prerequisites
1.  **Ollama** installed and running.
2.  **Python 3.10+**

### Setup
```bash
# 1. Clone the repository
git clone https://github.com/theraaajj/DocuSenseAI-v3.git
cd DocuSenseAI-v3

# 2. Create Virtual Environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Pull the Models
ollama pull phi3
ollama pull llama3.2
ollama pull nomic-embed-text

# 5. Run the Backend API
python main_api.py

# 6. Run the React Frontend (In a new terminal)
cd frontend
npm install
npm run dev
```

### Legacy Interface
If you prefer the original Streamlit interface:
```bash
streamlit run app.py
```

---

## 🚧Roadmap & Evaluation Status
This project is currently in further development and evaluation - **Raj Aryan**
