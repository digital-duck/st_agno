import streamlit as st
import uuid
import os
from pathlib import Path
from db.sqlite_manager import SQLiteManager
from db.vector_store import VectorStore
from utils.rag_utils import RAGSystem
from utils.ollama_utils import OllamaAPI
from utils.config import (
    DEFAULT_MODEL_LIST, DEFAULT_MODEL
)




# Initialize page configuration
st.set_page_config(
    page_title="Agno Chat Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App title in the main page
st.header("Agno LLM Chat Assistant")
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
# Wrap each initialization in its own try block to isolate errors
if "db" not in st.session_state:
    try:
        st.session_state.db = SQLiteManager()
    except Exception as e:
        st.error(f"Failed to initialize SQLite database: {str(e)}")
        st.session_state.db = None

if "vector_store" not in st.session_state:
    try:
        st.session_state.vector_store = VectorStore()
    except Exception as e:
        st.error(f"Failed to initialize Vector Store: {str(e)}")
        st.session_state.vector_store = None

if "rag_system" not in st.session_state:
    try:
        st.session_state.rag_system = RAGSystem()
    except Exception as e:
        st.error(f"Failed to initialize RAG system: {str(e)}")
        st.session_state.rag_system = None

if "ollama_api" not in st.session_state:
    try:
        st.session_state.ollama_api = OllamaAPI()
    except Exception as e:
        st.error(f"Failed to initialize Ollama API: {str(e)}")
        st.session_state.ollama_api = None

# Check Ollama connection and populate models
try:
    if st.session_state.ollama_api:
        with st.spinner("Connecting to Ollama API..."):
            connected = st.session_state.ollama_api.check_connection()
            st.session_state.ollama_connected = connected
            
            if connected:
                st.session_state.ollama_models = st.session_state.ollama_api.get_model_names()
                if not st.session_state.ollama_models:
                    st.warning("Connected to Ollama, but no models found. Please install models via Ollama.")
                    st.session_state.ollama_models = DEFAULT_MODEL_LIST  # Default fallback
            else:
                st.error("Could not connect to Ollama API. Please ensure Ollama is running on http://localhost:11434")
                st.session_state.ollama_models = DEFAULT_MODEL_LIST  # Default fallback
    else:
        st.warning("Ollama API not initialized. Using default models.")
        st.session_state.ollama_models = DEFAULT_MODEL_LIST
except Exception as e:
    st.error(f"Error connecting to Ollama: {str(e)}")
    st.session_state.ollama_connected = False
    st.session_state.ollama_models = DEFAULT_MODEL_LIST  # Default fallback

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


def init_config(cfg_path=".streamlit/config.toml"):
    """Create .streamlit directory and config file if not found"""

    # Convert string path to Path object
    config_path = Path(cfg_path)
    
    # Create parent directory with exists_ok=True
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Only create the config file if it doesn't exist
    if not config_path.exists():
        config_path.write_text("""
    [theme]
    primaryColor="#FF4B4B"
    backgroundColor="#FFFFFF"
    secondaryBackgroundColor="#F0F2F6"
    textColor="#262730"
    font="sans serif"
        """)