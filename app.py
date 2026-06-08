import os
import streamlit as st
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv()

# Streamlit App Title
st.title("🛍️ E-Commerce Return Policy Chatbot")
st.write("Ask me anything about our return and refund policies!")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

@st.cache_resource
def setup_rag_pipeline():
    # 1. Load the document
    loader = TextLoader("return_policy.txt", encoding="utf-8")
    docs = loader.load()

    # 2. Split the document into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = text_splitter.split_documents(docs)

    # 3. Create embeddings and vector store
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(splits, embeddings)
    retriever = vectorstore.as_retriever()

    # 4. Setup LLM
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)

    # 5. Create System Prompt Guardrail
    system_prompt = (
        "You are a helpful customer support assistant for an e-commerce store. "
        "You must ONLY answer questions based on the provided context (the return policy). "
        "If the user asks a question that is not covered in the return policy, you must say: "
        "'I apologize, but I can only assist with questions related to our return and refund policy.' "
        "Do not guess or make up answers.\n\n"
        "Context: {context}"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    # 6. Create the chain
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    
    return rag_chain

# Check for API Key
if not os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY") == "your_api_key_here":
    st.warning("⚠️ Please add your GROQ_API_KEY to the .env file to continue.")
    st.stop()

# Setup pipeline
try:
    rag_chain = setup_rag_pipeline()
except Exception as e:
    st.error(f"Error setting up the application: {e}")
    st.stop()

# React to user input
if prompt := st.chat_input("Ask a question (e.g., What is your return policy?)"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get bot response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = rag_chain.invoke({"input": prompt})
            answer = response["answer"]
            st.markdown(answer)
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": answer})
