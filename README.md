# Agno RAG-Enabled Chat Application

A Streamlit-based chat application that uses Agno (ex. phidata) to interact with Ollama models, featuring RAG capabilities with both SQLite and ChromaDB for context-aware responses.

**agno**: Build Multimodal AI Agents with memory, knowledge and tools. Simple, fast and model-agnostic.
- [source](https://github.com/agno-agi/agno)
- [docs](https://docs.agno.com/)

## Features

- **Multi-page Application**:
  - Chat interface for interacting with LLMs
  - History page to browse, search, and manage past conversations
  
- **Persistent Storage**:
  - SQLite database for structured conversation storage
  - ChromaDB vector store for semantic search capabilities
  
- **RAG System**:
  - Combines text search (SQLite) and semantic search (ChromaDB)
  - Provides relevant context from past conversations
  
- **Dynamic Model Selection**:
  - Automatically detects and lists models installed on your Ollama instance
  
- **Conversation Management**:
  - Create, view, edit titles, and delete conversations
  - Resume conversations from history

## Prerequisites

- Python 3.8+
- Ollama installed and running on your machine (https://ollama.ai)
- At least one model installed in Ollama (e.g., llama3.1)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/digital-duck/st_agno.git
   cd st_agno/src
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   streamlit run app.py
   ```

## Usage

1. **Chat Page**:
   - Select a model from the sidebar
   - Enable/disable streaming responses
   - Configure RAG settings
   - Start chatting with the AI

2. **History Page**:
   - Browse past conversations
   - Search by keywords
   - Filter by date
   - View, resume, or delete conversations

## Project Structure

```
src/
├── .env                     # Configuration environment variables
├── .streamlit/
│   └── config.toml          # Streamlit configuration
├── requirements.txt         # Dependencies
├── app.py                   # Main entry point
├── db/
│   ├── __init__.py
│   ├── sqlite_manager.py    # SQLite database operations
│   └── vector_store.py      # ChromaDB vector store operations
├── pages/
│   ├── 1_Chat.py            # Chat interface page
│   └── 2_History.py         # Chat history page
└── utils/
    ├── __init__.py
    ├── ollama_utils.py      # Ollama API utilities
    └── rag_utils.py         # RAG system utilities
```

## Customization

- Edit `.env` file to change default settings
- Modify `.streamlit/config.toml` to customize the app appearance

## Troubleshooting

- If you get an error connecting to Ollama, ensure Ollama is running: `ollama serve`
- If no models appear in the dropdown, install at least one model: `ollama pull llama3.1`
- For ChromaDB issues, try deleting the `chroma_db` directory and restarting

## License

Apache License 2.0
