import streamlit as st
import uuid
import os
from db.sqlite_manager import SQLiteManager
from db.vector_store import VectorStore
from utils.rag_utils import RAGSystem
from utils.ollama_utils import OllamaAPI

# Initialize page configuration
st.set_page_config(
    page_title="Agno Chat Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App title in the main page
st.title("Agno LLM Chat Assistant")
st.markdown("Welcome to the Agno Chat Assistant with RAG capabilities.")

# Initialize session state for app-wide variables
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.conversation_id = str(uuid.uuid4())
    st.session_state.conversation_title = "New Conversation"
    st.session_state.messages = []
    st.session_state.ollama_models = []
    st.session_state.ollama_connected = False

# Initialize database connections and API clients
if "db" not in st.session_state:
    st.session_state.db = SQLiteManager()
    st.session_state.vector_store = VectorStore()
    st.session_state.rag_system = RAGSystem()
    # Initialize the Ollama API - this was missing/incorrect
    st.session_state.ollama_api = OllamaAPI()

# Check Ollama connection and populate models
try:
    with st.spinner("Connecting to Ollama API..."):
        connected = st.session_state.ollama_api.check_connection()
        st.session_state.ollama_connected = connected
        
        if connected:
            st.session_state.ollama_models = st.session_state.ollama_api.get_model_names()
            if not st.session_state.ollama_models:
                st.warning("Connected to Ollama, but no models found. Please install models via Ollama.")
        else:
            st.error("Could not connect to Ollama API. Please ensure Ollama is running on http://localhost:11434")
            st.session_state.ollama_models = ["llama3.1", "mistral", "mixtral"]  # Default fallback
except Exception as e:
    st.error(f"Error connecting to Ollama: {str(e)}")
    st.session_state.ollama_connected = False
    st.session_state.ollama_models = ["llama3.1", "mistral", "mixtral"]  # Default fallback

# Display main page guidance
st.markdown("""
This is a multi-page Streamlit application:
1. **Chat**: Interact with the LLM model
2. **History**: View and search past conversations

The app features:
- Persistent conversation storage in SQLite
- Semantic search with ChromaDB
- RAG capabilities for context-aware responses
- Dynamic model selection from your Ollama installation
""")

# Add a button to create a new conversation
if st.button("Start New Conversation"):
    st.session_state.conversation_id = str(uuid.uuid4())
    st.session_state.conversation_title = "New Conversation"
    st.session_state.messages = []
    st.rerun()

# Create .streamlit directory and config file
os.makedirs(".streamlit", exist_ok=True)

with open(".streamlit/config.toml", "w") as f:
    f.write("""
[theme]
primaryColor="#FF4B4B"
backgroundColor="#FFFFFF"
secondaryBackgroundColor="#F0F2F6"
textColor="#262730"
font="sans serif"
    """)