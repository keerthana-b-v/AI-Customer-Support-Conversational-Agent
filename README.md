# 🛍️ Production-Aware E-Commerce Support Chatbot

This is a secure, production-patterned Retrieval-Augmented Generation (RAG) customer support agent. It is designed to safely answer customer questions about shipping, returns, and warranties strictly based on policy documentation while incorporating advanced routing, conversation memory, and automated guardrail evaluations.

---

## 🏗️ Technical Architecture & Systems Flow

This project is built using a modern decoupled architecture:
 
*   **Frontend**: A responsive **React (Vite)** single-page application that renders a conversational chat feed, handles real-time Server-Sent Events (SSE) streaming, generates persistent session IDs, and monitors backend online status.
*   **Backend**: A **FastAPI** web server that hosts streaming endpoints, processes incoming payloads, manages session states in-memory, and interacts with a local SQLite database.
*   **Lexical Retrieval & AI**: **LangChain** orchestrates document loading (`data/*.txt`), text chunking (`RecursiveCharacterTextSplitter`), and local keyword retrieval via an in-memory **rank-bm25** lexical retriever. LLM completion is powered by ChatGroq utilizing `llama-3.1-8b-instant`.
*   **Database Persistence**: **SQLite** (`.db/support.db`) records ticket data and conversation logs. The database is written inside a hidden directory to isolate changes and prevent local development servers (e.g. VS Code Live Server) from triggering hot-reload loops.
 
```
                         [User Inputs Query]
                                  │
                                  ▼
                        [React Frontend SPA]
               (Attaches CRM context + Session ID)
                                  │
                                  ▼
                   [FastAPI Backend (/chat route)]
            (Checks Client IP against Rate Limiter)
                                  │
                                  ▼
                  [LLM Analysis & Security Guard]
         (Checks for Prompt Injection, Intent & Sentiment)
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │ is_injection = true     │ sentiment = frustrated  │ normal query
        ▼                         ▼ OR intent = escalation  ▼
 [Canned Refusal]         [Multi-Turn Frustration]  [Retrieve RAG Context]
 (Blocks LLM calls)       (Logs Ticket to SQLite)    (Queries BM25 Index)
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  │
                                  ▼
                         [FastAPI SSE Stream]
                        (Yields text chunks)
                                  │
                                  ▼
                     [React DOM Incremental Render]
```
 
---
 
## 🔍 Retrieval Strategy & Architectural Rationale
 
To optimize the pipeline for memory, speed, and accuracy, we made several deliberate design decisions:
 
### 1. Multi-Document Indexing & Naive RAG Architecture
This system follows a **Naive RAG** (Retrieve-and-Generate) flow. The LLM does not perform document lookup. Instead:
* **Indexed Documents**: During startup, our pipeline reads all three policy documents (`shipping`, `returns`, and `warranty`), chunks them, and builds a **single unified BM25 search index**.
* **Keyword Matching**: When a user query is made, the search engine indexes across all document chunks simultaneously and extracts the relevant chunks based on keyword matching scores (TF-IDF/BM25).
* **Generation**: The retrieved text is pasted directly into the system prompt context, where the LLM reasons over the material to generate a response.
 
### 2. Chunk Retrieval Selection (Top-2 Chunks)
Our chunking configuration uses **1000-character segments** (with a 200-character sliding overlap). Because the source policy files are concise and highly structured:
* Individual policy terms (e.g., shipping costs or return windows) fit fully inside a single chunk.
* Retrieving the **top 2 matching chunks** provides a maximum of 2,000 characters of context, which is more than enough to fully cover the user's question without flooding the LLM's context window.
 
### 3. Trade-offs: Skipping MMR and Re-ranking
We explicitly chose not to implement complex re-ranking (like Cohere) or Maximal Marginal Relevance (MMR) algorithms:
* **No Re-ranking**: Re-ranking runs a neural cross-encoder over retrieved text to sort relevance. For our small 3-document dataset, this adds 200-500ms of extra latency and heavy processing overhead with zero quality improvements.
* **No MMR**: MMR filters out chunks with similar text to maximize diversity. In our concise policy sheets, there is minimal duplicate information, making MMR redundant.
Skipping these features keeps our search retrieval lookup times under 1ms, keeping the RAG pipeline lightweight.
 
---
 
## 🛡️ Implemented Security & Guardrail Layers

1.  **Double-Layer Prompt Injection Defense**:
    *   **Heuristics**: A local string matcher scans for common jailbreaking keywords (`"ignore previous instructions"`, `"system prompt"`, etc.).
    *   **LLM Guardrail**: A classification step evaluates user inputs for prompt override attempts. If flagged, the pipeline immediately halts and returns a canned secure refusal message: *"I'm sorry, I cannot perform that action. I am strictly authorized to assist only with shipping, returns, and warranties."*
2.  **IP-Based Rate Limiting**: An in-memory sliding window rate limiter restricts clients to **10 requests per 60 seconds** per client IP, protecting the Groq API key from brute-force spam or exhaustion.
3.  **SQL Injection & DoS Defense**: Input lengths are restricted to a maximum of 1,000 characters using Pydantic schemas, and all SQLite transactions use fully parameterized SQL statements (`?`).
4.  **Multi-Turn Frustration Persistence**: To prevent over-eager ticketing on a single frustrated keyword (e.g. *"This slow shipping is annoying, anyway what's the refund window?"*), the backend checks SQLite log history and only triggers automated escalation if the user exhibits frustration across **2 consecutive turns**.
5.  **Robust Fallback JSON Parsing**: A regex-based extraction utility pulls the first `{...}` JSON block from the router output, preventing parsing crashes if the LLM includes conversational pre-text.

---

## 🧪 Automated Evaluation Suite

To maintain high guardrail and routing accuracy, the repository includes an automated evaluation runner: **[eval.py](file:///d:/projects/chatbot/scripts/eval.py)**. It executes test assertions against the query router to ensure correct intent, sentiment, and injection classification.

To run the evaluations:
```bash
python scripts/eval.py
```

### 📊 Current Evaluation Metrics

#### 1. Guardrail & Intent Routing Accuracy (Classification)
Evaluates if user queries are correctly classified for prompt injection, sentiment, and escalation.

| Test Category | Target Metric | Metric Description | Current Result |
| :--- | :--- | :--- | :--- |
| **Intent Classification** | Accuracy | Routing query to RAG vs. Ticket Escalation | **100.00%** (8/8 cases) |
| **Sentiment Detection** | Accuracy | Detecting customer frustration | **100.00%** (8/8 cases) |
| **Prompt Injection Defense** | Recall / Block Rate | Detecting and blocking jailbreak attempts | **100.00%** (8/8 cases) |

To run the routing evaluations:
```bash
python scripts/eval.py
```

#### 2. RAG Answer Quality Metrics (Generation & Grounding)
Evaluates the pipeline using 18 golden Q&A pairs grounded across all policy documents. Measures performance using LLM-as-a-judge metrics modeled after the RAGAS framework:

| Metric | Target Value | Description | Current Score |
| :--- | :--- | :--- | :--- |
| **Faithfulness** | > 0.85 | Is the generated answer grounded strictly in the retrieved context? | **94.44%** (0.9444) |
| **Answer Relevancy** | > 0.85 | Does the generated answer directly address the user's question? | **97.78%** (0.9778) |
| **Context Precision** | > 0.85 | Is the retrieved context relevant and precise for the question? | **85.56%** (0.8556) |

To run the quality evaluation suite:
```bash
python scripts/eval_quality.py
```


---

## 📈 Production Readiness & Scaling Roadmap

For a public-facing, cloud-scale deployment, the stateful components of this architecture must be externalized. The following table represents the architecture's roadmap to serverless and highly available environments:

| Component | Current Demo Implementation | Production / Serverless Scale-Up |
| :--- | :--- | :--- |
| **Database** | Local SQLite (`.db/support.db`) | **Turso** (Distributed SQLite) or **Supabase / AWS Aurora** (PostgreSQL) |
| **Session Memory** | In-memory Python `dict` | **Upstash Redis** (Persists session logs across serverless function cycles) |
| **Rate Limiter** | In-memory IP tracking | **Upstash Redis Rate Limiting** or API Gateway Middleware |
| **Vector Storage** | Local FAISS (in-memory) | **Pinecone**, **pgvector**, or **Qdrant** |
| **Embeddings** | Local CPU `sentence-transformers` | **Hugging Face Inference API** or **OpenAI text-embedding-3-small** |
| **Auth & CORS** | Wildcard allowed (`*`) | **Auth0 / Clerk** integration, strict domain CORS restrictions |
| **Observability** | Python standard `print` logs | **LangSmith**, **Datadog**, or **Ariadne** (LLM monitoring & trace evaluations) |

---

## ⚙️ Running Locally

### 1. Setup Environment
Create a `.env` file in the root directory and add your Groq API Key:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
```

### 2. Start Backend API
```bash
pip install -r requirements.txt
python -m uvicorn main:app --port 8000
```

### 3. Start React Frontend
In a separate terminal:
```bash
cd frontend
npm install
npm run dev -- --port 3000
```
Then visit `http://localhost:3000` in your web browser.
