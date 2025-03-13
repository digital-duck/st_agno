import os
import chromadb
from chromadb.config import Settings
import streamlit as st
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

class VectorStore:
    def __init__(self, persist_directory="./chroma_db", collection_name="chat_history"):
        """Initialize ChromaDB vector store for semantic search capabilities."""
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
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
            
            # Get or create collection - this is where the error happens
            try:
                # Try to get the collection first
                self.collection = self.client.get_or_create_collection(
                    name=collection_name
                )
                
                # Initialize LangChain's Chroma wrapper for easier semantic search
                self.langchain_chroma = Chroma(
                    client=self.client,
                    collection_name=collection_name,
                    embedding_function=self.embedding_function
                )
            except Exception as e:
                st.warning(f"ChromaDB collection error: {str(e)}. Creating a new collection.")
                # If collection retrieval fails, create a new collection
                try:
                    self.collection = self.client.create_collection(name=collection_name)
                    
                    # Initialize LangChain's Chroma wrapper for easier semantic search
                    self.langchain_chroma = Chroma(
                        client=self.client,
                        collection_name=collection_name,
                        embedding_function=self.embedding_function
                    )
                except Exception as create_err:
                    st.error(f"Failed to create ChromaDB collection: {str(create_err)}")
                    # Initialize with dummy objects to prevent further errors
                    self.collection = None
                    self.langchain_chroma = None
                    
        except Exception as e:
            st.error(f"Error initializing VectorStore: {str(e)}")
            # Initialize with dummy objects to prevent further errors
            self.client = None
            self.collection = None
            self.langchain_chroma = None
    
    def add_message(self, message_id, content, metadata=None):
        """Add a message to the vector store."""
        if not metadata:
            metadata = {}
        
        # Skip if ChromaDB is not properly initialized
        if not self.collection:
            st.warning("ChromaDB not initialized. Message not stored in vector database.")
            return False
        
        try:
            self.collection.add(
                ids=[message_id],
                documents=[content],
                metadatas=[metadata]
            )
            return True
        except Exception as e:
            st.warning(f"Error adding message to vector store: {e}")
            return False
    
    def semantic_search(self, query, n_results=5):
        """Perform semantic search on stored messages."""
        # Skip if ChromaDB is not properly initialized
        if not self.langchain_chroma:
            st.warning("ChromaDB not initialized. Semantic search unavailable.")
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
            st.warning(f"Error performing semantic search: {e}")
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
            st.warning(f"Error deleting message from vector store: {e}")
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
            st.warning(f"Error deleting conversation messages from vector store: {e}")
            return False