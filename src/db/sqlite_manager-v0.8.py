import os
import sqlite3
import uuid
from datetime import datetime
import json

class SQLiteManager:
    def __init__(self, db_path="chat_history.db"):
        """Initialize SQLite database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.conn = self._create_connection()
        self._create_tables()
    
    def _create_connection(self):
        """Create a database connection to the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            return conn
        except sqlite3.Error as e:
            print(f"SQLite connection error: {e}")
            return None
    
    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        try:
            cursor = self.conn.cursor()
            
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
                timestamp TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
            ''')
            
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Table creation error: {e}")
    
    def create_conversation(self, title="New Conversation", model="llama3.1"):
        """Create a new conversation and return its ID."""
        try:
            conversation_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (id, title, created_at, model, updated_at) VALUES (?, ?, ?, ?, ?)",
                (conversation_id, title, now, model, now)
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
            now = datetime.now().isoformat()
            
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO messages (id, conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
                (message_id, conversation_id, role, content, now)
            )
            
            # Update conversation's updated_at timestamp
            cursor.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id)
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
            conversation = dict(cursor.fetchone())
            
            # Get all messages for this conversation
            cursor.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp", (conversation_id,))
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
                (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY timestamp LIMIT 1) as first_message
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
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()