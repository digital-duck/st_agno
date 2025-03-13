#!/usr/bin/env python3
import os
import shutil
import argparse

def create_directory(path):
    """Create a directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")

def create_file(path, content=""):
    """Create a file with optional content."""
    with open(path, 'w') as f:
        f.write(content)
    print(f"Created file: {path}")

def setup_project(base_dir="."):
    """Set up the entire project structure."""
    # Create base directory if it doesn't already exist
    if base_dir != "." and not os.path.exists(base_dir):
        os.makedirs(base_dir)
        print(f"Created project directory: {base_dir}")
    
    # Create main project directories
    directories = [
        os.path.join(base_dir, ".streamlit"),
        os.path.join(base_dir, "db"),
        os.path.join(base_dir, "pages"),
        os.path.join(base_dir, "utils"),
    ]
    
    for directory in directories:
        create_directory(directory)
    
    # Create empty __init__.py files
    init_files = [
        os.path.join(base_dir, "db", "__init__.py"),
        os.path.join(base_dir, "utils", "__init__.py"),
    ]
    
    for init_file in init_files:
        create_file(init_file)
    
    # Create empty module files
    module_files = [
        os.path.join(base_dir, "db", "sqlite_manager.py"),
        os.path.join(base_dir, "db", "vector_store.py"),
        os.path.join(base_dir, "utils", "ollama_utils.py"),
        os.path.join(base_dir, "utils", "rag_utils.py"),
        os.path.join(base_dir, "pages", "1_Chat.py"),
        os.path.join(base_dir, "pages", "2_History.py"),
    ]
    
    for module_file in module_files:
        create_file(module_file)
    
    # Create main app file
    create_file(os.path.join(base_dir, "app.py"))
    
    # Create configuration files
    streamlit_config = """
[theme]
primaryColor="#FF4B4B"
backgroundColor="#FFFFFF"
secondaryBackgroundColor="#F0F2F6"
textColor="#262730"
font="sans serif"
    """
    create_file(os.path.join(base_dir, ".streamlit", "config.toml"), streamlit_config)
    
    env_content = """# Ollama API configuration
OLLAMA_BASE_URL=http://localhost:11434

# Database paths
SQLITE_DB_PATH=./chat_history.db
CHROMA_DB_PATH=./chroma_db

# Default model
DEFAULT_MODEL=llama3.1

# RAG settings
DEFAULT_RAG_ENABLED=true
DEFAULT_CONTEXT_RESULTS=3
"""
    create_file(os.path.join(base_dir, ".env"), env_content)
    
    # Create requirements.txt
    requirements = """streamlit>=1.29.0
agno>=0.1.0
chromadb>=0.4.18
langchain>=0.1.0
langchain-community>=0.0.13
pydantic>=2.5.0
sqlalchemy>=2.0.0
uuid>=1.30
requests>=2.31.0
python-dotenv>=1.0.0
"""
    create_file(os.path.join(base_dir, "requirements.txt"), requirements)
    
    # Create placeholder for database directories
    create_directory(os.path.join(base_dir, "chroma_db"))
    
    print("\nProject structure created successfully!")
    print(f"Run 'cd {base_dir} && streamlit run app.py' to start the application (after adding code to the files)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up Agno Streamlit project structure")
    parser.add_argument("--dir", default="src", help="Base directory for the project")
    args = parser.parse_args()
    
    setup_project(args.dir)