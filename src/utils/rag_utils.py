from typing import List, Dict, Any
import streamlit as st
from db.sqlite_manager import SQLiteManager
from db.vector_store import VectorStore

class RAGSystem:
    def __init__(self):
        """Initialize RAG system with both text and semantic search capabilities."""
        self.db = SQLiteManager()
        self.vector_store = VectorStore()
    
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
        
        # Semantic search using ChromaDB
        if use_semantic:
            semantic_results = self.vector_store.semantic_search(query, n_results=limit)
            
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
        if not self.db.get_conversation(conversation_id):
            self.db.create_conversation(title=title, model=model)
            
            for msg in messages:
                self.db.add_message(conversation_id, msg["role"], msg["content"])
        
        # Then, store assistant messages in the vector store for semantic search
        for msg in messages:
            if msg["role"] == "assistant":
                message_id = msg.get("id", str(uuid.uuid4()))
                self.vector_store.add_message(
                    message_id=message_id,
                    content=msg["content"],
                    metadata={
                        "conversation_id": conversation_id,
                        "conversation_title": title,
                        "role": "assistant",
                        "timestamp": msg.get("timestamp", "")
                    }
                )
        
        return True
    
    def add_message_to_stores(self, conversation_id, role, content, conversation_title=""):
        """Add a single message to both SQLite and ChromaDB stores."""
        # Add to SQLite
        message_id = self.db.add_message(conversation_id, role, content)
        
        # Add assistant message to vector store for semantic search
        if role == "assistant" and message_id:
            self.vector_store.add_message(
                message_id=message_id,
                content=content,
                metadata={
                    "conversation_id": conversation_id,
                    "conversation_title": conversation_title,
                    "role": role,
                    "timestamp": ""  # SQLite adds timestamp internally
                }
            )
        
        return message_id
    
    def delete_conversation(self, conversation_id):
        """Delete a conversation from both stores."""
        # Delete from vector store first
        self.vector_store.delete_conversation_messages(conversation_id)
        
        # Then delete from SQLite
        return self.db.delete_conversation(conversation_id)