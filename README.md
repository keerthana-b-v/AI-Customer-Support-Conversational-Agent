# 🛍️ E-Commerce Return Policy Chatbot

This is a Retrieval-Augmented Generation (RAG) chatbot built with **Streamlit**, **LangChain**, and **Groq** to answer customer questions strictly based on a company's return policy. 

## Features
- **Instant Answers**: Get immediate responses to return policy questions.
- **Strict Guardrails**: Prevents AI hallucinations by strictly adhering to the provided policy document. 
- **Local Embeddings**: Uses `sentence-transformers` for fast, free local vector search via FAISS.

## Testing the Bot's Guardrails

I extensively tested the chatbot to ensure it handles various edge cases correctly and doesn't invent information. 

### 1. Handling Off-Topic Questions (Anti-Hallucination)
To ensure the bot acts purely as a customer service assistant and doesn't hallucinate, I implemented a strict system prompt. As you can see in my testing, if you ask it something completely unrelated (like how to fix a flat tire, the capital of France, or writing a poem), it safely catches it and politely refuses:

![Off-Topic Handling](off-topic.png)
*(The bot correctly responds: "I apologize, but I can only assist with questions related to our return and refund policy.")*

### 2. Tricky Policy Questions
I also tested the bot on specific, tricky rules from the policy to ensure it retrieves the exact conditions rather than giving generic answers:
- **Clearance Items**: When asked about clearance items, it correctly states they are final sale and cannot be returned.
- **Time Limits**: It enforces the 30-day limit for refunds.
- **Damaged Goods**: It correctly identifies the exception that the customer doesn't pay for return shipping if the item arrived damaged.

![Tricky Policy Handling](Tricky%20Policy.png)

### 3. Missing Information
If asked about a topic not covered in the text (like international returns), the bot gracefully falls back to the guardrail rather than making up a fake policy.

![Missing Info Handling](Missing%20Information.png)

---

## Tech Stack & Architecture
This project is built using a production-ready client-server architecture:
- **Backend (API Layer)**: Built with **FastAPI**, **LangChain**, and the **Groq API** (`llama-3.1-8b-instant`). It handles the RAG pipeline, semantic search (via local **FAISS** and **HuggingFace** embeddings), and interaction logging.
- **Frontend (UI Layer)**: A clean, modern **HTML/CSS/JS** single-page application that connects to the backend API. It features a sidebar for CRM simulation settings and a centered, sleek chat window.

---

## Getting Started

### 1. Setup Environment
Add your Groq API key to a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Backend API
Start the FastAPI server:
```bash
python -m uvicorn main:app --port 8000 --reload
```
The API documentation (Swagger UI) will be available at `http://127.0.0.1:8000/docs`.

### 4. Open the Frontend
Simply open the `index.html` file in any web browser! Alternatively, serve it locally:
```bash
python -m http.server 8080
```
Then visit `http://localhost:8080` in your browser.

---

## 🚀 Production Deployment Guide

This project is structured for easy cloud deployment using free-tier services.

### 1. Deploy the Backend (FastAPI) on Render
1. Create a free account at [Render](https://render.com).
2. Create a new **Web Service** and connect this GitHub repository.
3. Configure the following build settings:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m uvicorn main:app --host 0.0.0.0 --port 10000`
4. Under **Advanced**, add your environment variables:
   - Key: `GROQ_API_KEY`, Value: `[Your Actual Groq API Key]`
5. Click **Deploy Web Service**. Once running, copy your live backend URL (e.g., `https://your-app.onrender.com`).

### 2. Connect Frontend to the Live Backend
1. Open `app.js` and update the first line with your live Render backend URL:
   ```javascript
   const API_URL = 'https://your-app.onrender.com';
   ```
2. Commit and push this change to your GitHub repository.

### 3. Deploy the Frontend on GitHub Pages
1. Go to your repository settings on GitHub.
2. Click **Pages** in the left sidebar.
3. Under **Build and deployment**, set the source to **Deploy from a branch**.
4. Set the branch to `main` and folder to `/ (root)`, then click **Save**.
5. Your live frontend will be active at `https://[your-username].github.io/[your-repo-name]/` in a few moments!
