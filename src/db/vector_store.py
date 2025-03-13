import os
import chromadb
import shutil
from chromadb.config import Settings
import streamlit as st
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

# Create a global flag to track if we've shown ChromaDB warnings already
if "chroma_warnings_shown" not in st.session_state:
    st.session_state.chroma_warnings_shown = False

class VectorStore:
    def __init__(self, persist_directory="./chroma_db", collection_name="chat_history"):
        """Initialize ChromaDB vector store for semantic search capabilities."""
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.was_reset = False  # Track if the database was reset
        
        # Create directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        try:
            # Initialize the embedding function using Ollama
            self.embedding_function = OllamaEmbeddings(
                model="llama3.1:latest",
                base_url="http://localhost:11434"
            )
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Try to get or create the collection with error handling for dimension mismatch
            self.collection = None
            self.langchain_chroma = None
            self._initialize_collection()
                    
        except Exception as e:
            # Only show error once
            if not st.session_state.chroma_warnings_shown:
                st.error(f"Error initializing VectorStore: {str(e)}")
                st.session_state.chroma_warnings_shown = True
                
            # Initialize with dummy objects to prevent further errors
            self.client = None
            self.collection = None
            self.langchain_chroma = None
    
    def _initialize_collection(self):
        """Initialize the collection with proper handling of dimension mismatch errors."""
        try:
            # First try to get the collection
            self.collection = self.client.get_collection(name=self.collection_name)
            
            # Initialize LangChain's Chroma wrapper
            self.langchain_chroma = Chroma(
                client=self.client,
                collection_name=self.collection_name,
                embedding_function=self.embedding_function
            )
            
        except ValueError as ve:
            # Collection doesn't exist yet, create it
            if "does not exist" in str(ve):
                self.collection = self.client.create_collection(name=self.collection_name)
                self.langchain_chroma = Chroma(
                    client=self.client,
                    collection_name=self.collection_name,
                    embedding_function=self.embedding_function
                )
            else:
                raise ve
                
        except Exception as e:
            # Check for dimension mismatch error
            if "Embedding dimension" in str(e) and "does not match" in str(e):
                # Only show this message once
                if not st.session_state.chroma_warnings_shown:
                    st.warning(f"Embedding dimension mismatch. Recreating collection.")
                self._recreate_collection()
            else:
                raise e
    
    def _recreate_collection(self):
        """Delete and recreate the collection to fix dimension mismatch."""
        try:
            # Delete the collection if it exists
            try:
                self.client.delete_collection(name=self.collection_name)
            except Exception as delete_err:
                # Don't show this warning as it's expected sometimes
                pass
            
            # Create a new collection
            self.collection = self.client.create_collection(name=self.collection_name)
            
            # Initialize LangChain's Chroma wrapper
            self.langchain_chroma = Chroma(
                client=self.client,
                collection_name=self.collection_name,
                embedding_function=self.embedding_function
            )
            
            # Only show success message once
            if not st.session_state.chroma_warnings_shown:
                st.success("Vector database has been reset due to model changes. Previous embeddings have been cleared.")
                st.session_state.chroma_warnings_shown = True
                
            self.was_reset = True  # Mark as reset
            
        except Exception as e:
            # Last resort: delete the entire directory and start fresh
            try:
                if os.path.exists(self.persist_directory):
                    shutil.rmtree(self.persist_directory)
                os.makedirs(self.persist_directory, exist_ok=True)
                
                # Reinitialize client
                self.client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(anonymized_telemetry=False)
                )
                
                # Create new collection
                self.collection = self.client.create_collection(name=self.collection_name)
                
                # Initialize LangChain's Chroma wrapper
                self.langchain_chroma = Chroma(
                    client=self.client,
                    collection_name=self.collection_name,
                    embedding_function=self.embedding_function
                )
                
                # Only show success message once
                if not st.session_state.chroma_warnings_shown:
                    st.success("Vector database has been completely reset.")
                    st.session_state.chroma_warnings_shown = True
                    
                self.was_reset = True  # Mark as reset
            except Exception as reset_err:
                # Only show error once
                if not st.session_state.chroma_warnings_shown:
                    st.error(f"Failed to reset vector database: {str(reset_err)}")
                    st.session_state.chroma_warnings_shown = True
                    
                self.collection = None
                self.langchain_chroma = None
    
    def add_message(self, message_id, content, metadata=None):
        """Add a message to the vector store."""
        if not metadata:
            metadata = {}
        
        # Skip if ChromaDB is not properly initialized
        if not self.collection:
            return False
        
        try:
            self.collection.add(
                ids=[message_id],
                documents=[content],
                metadatas=[metadata]
            )
            return True
        except Exception as e:
            # Check if it's a dimension mismatch error and try to fix it
            if "Embedding dimension" in str(e) and "does not match" in str(e):
                try:
                    self._recreate_collection()
                    # Try adding again
                    if self.collection:
                        self.collection.add(
                            ids=[message_id],
                            documents=[content],
                            metadatas=[metadata]
                        )
                        return True
                except Exception as retry_err:
                    self.was_reset = True  # Mark as reset even if it failed
            else:
                # Only show non-dimension errors once
                if not st.session_state.chroma_warnings_shown:
                    st.warning(f"Error adding message to vector store: {e}")
                    st.session_state.chroma_warnings_shown = True
            
            return False
    
    def semantic_search(self, query, n_results=5):
        """Perform semantic search on stored messages."""
        # Skip if ChromaDB is not properly initialized
        if not self.langchain_chroma:
            return []
        
        try:
            # Using LangChain's similarity search which handles embeddings
            results = self.langchain_chroma.similarity_search(
                query=query,
                k=n_results
            )
            
            # Format results
            formatted_results = []
            for doc in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": doc.metadata.get("score", 0)
                })
            
            return formatted_results
        except Exception as e:
            # Check if it's a dimension mismatch error and try to fix it
            if "Embedding dimension" in str(e) and "does not match" in str(e):
                try:
                    self._recreate_collection()
                    # No need to retry search since the collection is now empty
                    # Only show info message once
                    if not st.session_state.chroma_warnings_shown:
                        st.info("Vector database was reset due to model changes. Please add new data first.")
                        st.session_state.chroma_warnings_shown = True
                        
                    self.was_reset = True  # Mark as reset
                except Exception as retry_err:
                    self.was_reset = True  # Mark as reset even if it failed
            else:
                # Only show non-dimension errors once
                if not st.session_state.chroma_warnings_shown:
                    st.warning(f"Error performing semantic search: {e}")
                    st.session_state.chroma_warnings_shown = True
            
            return []
    
    def delete_message(self, message_id):
        """Delete a message from the vector store."""
        # Skip if ChromaDB is not properly initialized
        if not self.collection:
            return False
        
        try:
            self.collection.delete(ids=[message_id])
            return True
        except Exception as e:
            # Only show errors once
            if not st.session_state.chroma_warnings_shown:
                st.warning(f"Error deleting message from vector store: {e}")
                st.session_state.chroma_warnings_shown = True
            return False
    
    def delete_conversation_messages(self, conversation_id):
        """Delete all messages from a conversation."""
        # Skip if ChromaDB is not properly initialized
        if not self.collection:
            return False
        
        try:
            # Query for all documents with this conversation_id in metadata
            results = self.collection.get(
                where={"conversation_id": conversation_id}
            )
            
            # Delete all found documents
            if results and results.get("ids"):
                self.collection.delete(ids=results["ids"])
            
            return True
        except Exception as e:
            # Only show errors once
            if not st.session_state.chroma_warnings_shown:
                st.warning(f"Error deleting conversation messages from vector store: {e}")
                st.session_state.chroma_warnings_shown = True
            return False