import os
import sqlite3
import uuid
from datetime import datetime
import json
import threading

class SQLiteManager:
    _instance = None
    _lock = threading.Lock()
    _local = threading.local()
    
    def __new__(cls, db_path="chat_history.db"):
        """Implement a thread-safe singleton pattern"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SQLiteManager, cls).__new__(cls)
                cls._instance.db_path = db_path
                cls._instance._connections = {}
            return cls._instance
    
    def __init__(self, db_path="chat_history.db"):
        """Initialize database path (only happens once due to singleton)"""
        self.db_path = db_path
    
    @property
    def conn(self):
        """Get a thread-specific connection to the database"""
        thread_id = threading.get_ident()
        
        # Create a new connection for this thread if it doesn't exist
        if thread_id not in self._connections:
            connection = sqlite3.connect(self.db_path)
            connection.row_factory = sqlite3.Row  # Return rows as dictionaries
            self._connections[thread_id] = connection
            
            # Initialize tables for this connection
            self._create_tables(connection)
            
        return self._connections[thread_id]
    
    def _create_tables(self, connection):
        """Create necessary tables if they don't exist."""
        try:
            cursor = connection.cursor()
            
            # Create conversations table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT,
                model TEXT,
                updated_at TEXT
            )
            ''')
            
            # Create messages table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
            ''')
            
            connection.commit()
        except sqlite3.Error as e:
            print(f"Table creation error: {e}")
    
    def create_conversation(self, title="New Conversation", model="llama3.1"):
        """Create a new conversation and return its ID."""
        try:
            conversation_id = str(uuid.uuid4())
            ts_now = datetime.now().isoformat()
            
            cursor = self.conn.cursor()
            sql_stmt = """
INSERT INTO conversations 
(id, title, created_at, model, updated_at) 
VALUES (?, ?, ?, ?, ?)
"""
            cursor.execute(
                sql_stmt,
                (conversation_id, title, ts_now, model, ts_now)
            )
            self.conn.commit()
            return conversation_id
        except sqlite3.Error as e:
            print(f"Error creating conversation: {e}")
            return None
    
    def add_message(self, conversation_id, role, content):
        """Add a message to a conversation."""
        try:
            message_id = str(uuid.uuid4())
            ts_now = datetime.now().isoformat()
            
            cursor = self.conn.cursor()
            sql_stmt = """
INSERT INTO messages 
(id, conversation_id, role, content, created_at) 
VALUES (?, ?, ?, ?, ?)
"""
            cursor.execute(sql_stmt,
                (message_id, conversation_id, role, content, ts_now)
            )
            
            self.conn.commit()
            return message_id
        except sqlite3.Error as e:
            print(f"Error adding message: {e}")
            return None
    
    def get_conversation(self, conversation_id):
        """Get a conversation by ID with all its messages."""
        try:
            cursor = self.conn.cursor()
            
            # Get conversation details
            cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            conversation = dict(row)
            
            # Get all messages for this conversation
            cursor.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at", (conversation_id,))
            messages = [dict(row) for row in cursor.fetchall()]
            
            conversation['messages'] = messages
            return conversation
        except sqlite3.Error as e:
            print(f"Error retrieving conversation: {e}")
            return None
    
    def get_all_conversations(self, limit=50, offset=0):
        """Get all conversations with pagination."""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT c.*, COUNT(m.id) as message_count, 
                (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY created_at LIMIT 1) as first_message
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            conversations = [dict(row) for row in cursor.fetchall()]
            return conversations
        except sqlite3.Error as e:
            print(f"Error retrieving conversations: {e}")
            return []
    
    def search_conversations(self, query, limit=20):
        """Search conversations by content."""
        try:
            cursor = self.conn.cursor()
            
            # Use LIKE for simple text search
            search_term = f"%{query}%"
            cursor.execute("""
                SELECT DISTINCT c.id, c.title, c.created_at, c.model, c.updated_at
                FROM conversations c
                JOIN messages m ON c.id = m.conversation_id
                WHERE m.content LIKE ?
                ORDER BY c.updated_at DESC
                LIMIT ?
            """, (search_term, limit))
            
            conversations = [dict(row) for row in cursor.fetchall()]
            return conversations
        except sqlite3.Error as e:
            print(f"Error searching conversations: {e}")
            return []
    
    def delete_conversation(self, conversation_id):
        """Delete a conversation and all its messages."""
        try:
            cursor = self.conn.cursor()
            
            # Delete messages first (due to foreign key constraint)
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            
            # Delete the conversation
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting conversation: {e}")
            return False
    
    def close_all(self):
        """Close all database connections."""
        for conn in self._connections.values():
            if conn:
                conn.close()
        self._connections.clear()
    
    def __del__(self):
        """Ensure connections are closed when the object is garbage collected."""
        self.close_all()