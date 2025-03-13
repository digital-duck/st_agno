import uuid
import time
from typing import List, Dict, Any
import streamlit as st
from db.sqlite_manager import SQLiteManager
from db.vector_store import VectorStore

# Create a global flag to track if we've shown ChromaDB warnings already
if "chroma_warnings_shown" not in st.session_state:
    st.session_state.chroma_warnings_shown = False

class RAGSystem:
    def __init__(self):
        """Initialize RAG system with both text and semantic search capabilities."""
        self.db = SQLiteManager()
        self.vector_store = VectorStore()
        # Flag to track if ChromaDB was reset
        self.chroma_reset = False
        
        # Check if vector store was reset during initialization
        if hasattr(self.vector_store, 'was_reset') and self.vector_store.was_reset:
            self.chroma_reset = True
            
            # Show the reset message only once per session
            if not st.session_state.chroma_warnings_shown:
                st.success("Vector database has been reset due to model changes. Previous embeddings have been cleared.")
                st.info("Vector database was reset due to model changes. Please add new data first.")
                st.session_state.chroma_warnings_shown = True
    
    def search(self, query: str, use_semantic: bool = True, use_text: bool = True, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant context using both text and semantic search.
        
        Args:
            query: Search query string
            use_semantic: Whether to use semantic search (ChromaDB)
            use_text: Whether to use text search (SQLite)
            limit: Maximum number of results to return
            
        Returns:
            List of relevant context items
        """
        results = []
        
        # Text search using SQLite
        if use_text:
            try:
                conversations = self.db.search_conversations(query, limit=limit)
                
                for conv in conversations:
                    # Get full conversation with messages
                    full_conv = self.db.get_conversation(conv["id"])
                    
                    if full_conv and "messages" in full_conv:
                        # Add each message as a separate result
                        for msg in full_conv["messages"]:
                            if msg["role"] == "assistant":  # Only include assistant responses
                                results.append({
                                    "content": msg["content"],
                                    "source": "text_search",
                                    "conversation_id": conv["id"],
                                    "conversation_title": conv["title"],
                                    "timestamp": msg["timestamp"]
                                })
            except Exception as e:
                # Only show warning if not already shown
                if not st.session_state.chroma_warnings_shown:
                    st.warning(f"Text search error: {e}. Using semantic search only.")
                    st.session_state.chroma_warnings_shown = True
        
        # Semantic search using ChromaDB
        if use_semantic and not self.chroma_reset:
            try:
                semantic_results = self.vector_store.semantic_search(query, n_results=limit)
                
                # Check if the vector store was reset during the search
                if hasattr(self.vector_store, 'was_reset') and self.vector_store.was_reset:
                    self.chroma_reset = True
                    # Only show reset message once
                    if not st.session_state.chroma_warnings_shown:
                        st.session_state.chroma_warnings_shown = True
                else:
                    for result in semantic_results:
                        # Add semantic search results
                        results.append({
                            "content": result["content"],
                            "source": "semantic_search",
                            "conversation_id": result["metadata"].get("conversation_id", "unknown"),
                            "conversation_title": result["metadata"].get("conversation_title", "Unknown"),
                            "timestamp": result["metadata"].get("timestamp", "unknown"),
                            "score": result.get("score", 0)
                        })
            except Exception as e:
                # Skip showing warnings entirely after first occurrence
                if not st.session_state.chroma_warnings_shown:
                    st.session_state.chroma_warnings_shown = True
                self.chroma_reset = True  # Mark as reset to avoid repeated warnings
        
        # Deduplicate and sort results
        unique_results = {}
        for r in results:
            # Create a unique key for each result
            key = f"{r['conversation_id']}_{r['content'][:50]}"
            if key not in unique_results:
                unique_results[key] = r
        
        # Return the top results
        return list(unique_results.values())[:limit]
    
    def format_context_for_prompt(self, results: List[Dict[str, Any]]) -> str:
        """Format search results into a context string for the prompt."""
        if not results:
            return ""
        
        context = "Based on previous conversations, here is some relevant information:\n\n"
        
        for i, result in enumerate(results, 1):
            source = "Text Search" if result["source"] == "text_search" else "Semantic Search"
            context += f"[{i}] From conversation '{result['conversation_title']}' ({source}):\n"
            context += f"{result['content']}\n\n"
        
        return context
    
    def add_conversation_to_stores(self, conversation_id, title, model, messages):
        """Add a complete conversation to both SQLite and ChromaDB stores."""
        # First, store in SQLite
        try:
            if not self.db.get_conversation(conversation_id):
                self.db.create_conversation(title=title, model=model)
                
                for msg in messages:
                    self.db.add_message(conversation_id, msg["role"], msg["content"])
                
            # Then, store assistant messages in the vector store for semantic search
            if not self.chroma_reset:  # Only try to add to vector store if it wasn't reset
                for msg in messages:
                    if msg["role"] == "assistant":
                        message_id = str(uuid.uuid4())
                        try:
                            success = self.vector_store.add_message(
                                message_id=message_id,
                                content=msg["content"],
                                metadata={
                                    "conversation_id": conversation_id,
                                    "conversation_title": title,
                                    "role": "assistant",
                                    "timestamp": ""
                                }
                            )
                            # Update chroma_reset flag if vector store was reset
                            if hasattr(self.vector_store, 'was_reset') and self.vector_store.was_reset:
                                self.chroma_reset = True
                                # Show reset message only once
                                if not st.session_state.chroma_warnings_shown:
                                    st.session_state.chroma_warnings_shown = True
                        except Exception as e:
                            # Skip showing warnings after first occurrence
                            if not st.session_state.chroma_warnings_shown:
                                st.session_state.chroma_warnings_shown = True
                            self.chroma_reset = True
        except Exception as e:
            if not st.session_state.chroma_warnings_shown:
                st.error(f"Error saving conversation: {e}")
                st.session_state.chroma_warnings_shown = True
            return False
            
        return True
    
    def add_message_to_stores(self, conversation_id, role, content, conversation_title=""):
        """Add a single message to both SQLite and ChromaDB stores."""
        try:
            # Add to SQLite
            message_id = self.db.add_message(conversation_id, role, content)
            
            # Add assistant message to vector store for semantic search
            if role == "assistant" and message_id and not self.chroma_reset:
                try:
                    success = self.vector_store.add_message(
                        message_id=message_id,
                        content=content,
                        metadata={
                            "conversation_id": conversation_id,
                            "conversation_title": conversation_title,
                            "role": role,
                            "timestamp": ""  # SQLite adds timestamp internally
                        }
                    )
                    # Update chroma_reset flag if vector store was reset
                    if hasattr(self.vector_store, 'was_reset') and self.vector_store.was_reset:
                        self.chroma_reset = True
                        # Show reset message only once
                        if not st.session_state.chroma_warnings_shown:
                            st.session_state.chroma_warnings_shown = True
                except Exception as e:
                    # Skip showing warnings after first occurrence
                    if not st.session_state.chroma_warnings_shown:
                        st.session_state.chroma_warnings_shown = True
                    self.chroma_reset = True
            
            return message_id
        except Exception as e:
            if not st.session_state.chroma_warnings_shown:
                st.error(f"Error saving message: {e}")
                st.session_state.chroma_warnings_shown = True
            return None
    
    def delete_conversation(self, conversation_id):
        """Delete a conversation from both stores."""
        try:
            # Delete from vector store first
            if not self.chroma_reset:
                self.vector_store.delete_conversation_messages(conversation_id)
            
            # Then delete from SQLite
            return self.db.delete_conversation(conversation_id)
        except Exception as e:
            if not st.session_state.chroma_warnings_shown:
                st.error(f"Error deleting conversation: {e}")
                st.session_state.chroma_warnings_shown = True
            return False