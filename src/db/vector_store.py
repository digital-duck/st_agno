import os
import chromadb
from chromadb.config import Settings
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

class VectorStore:
    def __init__(self, persist_directory="./chroma_db", collection_name="chat_history"):
        """Initialize ChromaDB vector store for semantic search capabilities."""
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Create directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
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
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
        except ValueError:
            self.collection = self.client.create_collection(name=collection_name)
        
        # Initialize LangChain's Chroma wrapper for easier semantic search
        self.langchain_chroma = Chroma(
            client=self.client,
            collection_name=collection_name,
            embedding_function=self.embedding_function
        )
    
    def add_message(self, message_id, content, metadata=None):
        """Add a message to the vector store."""
        if not metadata:
            metadata = {}
        
        try:
            self.collection.add(
                ids=[message_id],
                documents=[content],
                metadatas=[metadata]
            )
            return True
        except Exception as e:
            print(f"Error adding message to vector store: {e}")
            return False
    
    def semantic_search(self, query, n_results=5):
        """Perform semantic search on stored messages."""
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
            print(f"Error performing semantic search: {e}")
            return []
    
    def delete_message(self, message_id):
        """Delete a message from the vector store."""
        try:
            self.collection.delete(ids=[message_id])
            return True
        except Exception as e:
            print(f"Error deleting message from vector store: {e}")
            return False
    
    def delete_conversation_messages(self, conversation_id):
        """Delete all messages from a conversation."""
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
            print(f"Error deleting conversation messages from vector store: {e}")
            return False