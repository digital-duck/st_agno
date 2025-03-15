import streamlit as st
import pandas as pd
from datetime import datetime
import traceback

# Init page config
st.set_page_config(
    page_title="Chat History",
    page_icon="📚",
    layout="wide"
)

# Title and description
st.title("Chat History")
st.markdown("View and search your previous conversations")

# Check if database is initialized
if "db" not in st.session_state:
    st.error("Database connection not initialized. Please return to the home page.")
    st.stop()

# Sidebar for search options
with st.sidebar:
    st.header("Search Options")
    
    search_query = st.text_input("Search conversations", placeholder="Enter keywords...")
    
    st.subheader("Filters")
    date_range = st.date_input(
        "Date range",
        value=(datetime.now().date(), datetime.now().date()),
        help="Filter conversations by date range"
    )
    
    # Debug info
    st.subheader("Debug Info")
    if st.button("Check Database Status"):
        try:
            # Test the database connection
            conn_status = "Connected" if st.session_state.db.conn else "Not Connected"
            st.info(f"SQLite Connection: {conn_status}")
            
            # Get database path
            db_path = st.session_state.db.db_path
            st.info(f"Database path: {db_path}")
            
            # Try to count the conversations
            cursor = st.session_state.db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM conversations")
            count = cursor.fetchone()[0]
            st.info(f"Total conversations in database: {count}")
            
            # Count messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            msg_count = cursor.fetchone()[0]
            st.info(f"Total messages in database: {msg_count}")
            
            # Check if tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            st.info(f"Tables in database: {[t[0] for t in tables]}")
            
            # Show schema for messages table
            cursor.execute("PRAGMA table_info(messages)")
            schema = cursor.fetchall()
            st.write("Messages table schema:")
            for col in schema:
                st.write(f"- {col['name']}: {col['type']}")
        except Exception as e:
            st.error(f"Database error: {str(e)}")
            st.code(traceback.format_exc())
    
    # Load button
    if st.button("Search History"):
        st.session_state.search_performed = True
        st.session_state.search_query = search_query
        st.session_state.date_range = date_range

# Function to load conversations from SQLite with better message counting
def load_conversations(query=None, date_range=None):
    if "db" not in st.session_state or not st.session_state.db:
        st.error("Database connection not initialized")
        return []
    
    try:
        if query:
            conversations = st.session_state.db.search_conversations(query)
        else:
            conversations = st.session_state.db.get_all_conversations(limit=100)
        
        # Add accurate message count to each conversation
        for conv in conversations:
            try:
                # Get actual message count from database
                cursor = st.session_state.db.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv["id"],))
                msg_count_row = cursor.fetchone()
                actual_msg_count = msg_count_row[0] if msg_count_row else 0
                
                # Update message count in conversation
                conv["message_count"] = actual_msg_count
                
                # If no first message but there are messages, fetch the first one
                if ("first_message" not in conv or not conv["first_message"]) and actual_msg_count > 0:
                    cursor.execute(
                        "SELECT content FROM messages WHERE conversation_id = ? AND role = 'user' ORDER BY created_at LIMIT 1", 
                        (conv["id"],)
                    )
                    first_msg_row = cursor.fetchone()
                    if first_msg_row:
                        conv["first_message"] = first_msg_row[0]
            except Exception as e:
                st.warning(f"Error retrieving message count: {str(e)}")
                conv["message_count"] = 0
        
        # Apply date filter if provided
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            filtered_conversations = []
            
            for conv in conversations:
                try:
                    conv_date = datetime.fromisoformat(conv["created_at"]).date()
                    if start_date <= conv_date <= end_date:
                        filtered_conversations.append(conv)
                except (ValueError, TypeError) as e:
                    st.warning(f"Date parsing error for conversation: {str(e)}")
            
            return filtered_conversations
        
        return conversations
    except Exception as e:
        st.error(f"Error loading conversations: {str(e)}")
        st.code(traceback.format_exc())
        return []

# Function to display a conversation with error handling
def display_conversation(conversation_id):
    if "db" not in st.session_state or not st.session_state.db:
        st.error("Database connection not initialized")
        return
    
    try:
        conversation = st.session_state.db.get_conversation(conversation_id)
        
        if not conversation:
            st.warning(f"Conversation not found: {conversation_id}")
            return
        
        # Display conversation metadata
        st.subheader(f"Conversation: {conversation['title']}")
        st.caption(f"Created: {conversation['created_at']} | Model: {conversation['model']}")
        
        # Count messages directly from database for verification
        cursor = st.session_state.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conversation_id,))
        db_msg_count = cursor.fetchone()[0]
        
        # Display conversation messages
        if "messages" in conversation and conversation["messages"]:
            st.caption(f"Messages: {len(conversation['messages'])} (database shows {db_msg_count})")
            for message in conversation["messages"]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        else:
            # If no messages in conversation object but db says there are messages
            if db_msg_count > 0:
                st.warning(f"Database indicates {db_msg_count} messages exist, but they couldn't be loaded. This may be a data inconsistency.")
                
                # Try to fetch messages directly
                cursor.execute("SELECT id, role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at", (conversation_id,))
                direct_messages = cursor.fetchall()
                
                if direct_messages:
                    st.info(f"Retrieved {len(direct_messages)} messages directly from database:")
                    for msg in direct_messages:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["content"])
                            st.caption(f"Message ID: {msg['id'][:8]}... | Time: {msg['created_at']}")
            else:
                st.info("No messages found in this conversation.")
        
        # Action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Load in Chat", key=f"load_{conversation_id}"):
                # Load this conversation into the chat page session
                st.session_state.conversation_id = conversation_id
                st.session_state.conversation_title = conversation["title"]
                
                # Convert messages to the format expected in the chat page
                if "messages" in conversation and conversation["messages"]:
                    st.session_state.messages = [
                        {"role": msg["role"], "content": msg["content"]}
                        for msg in conversation["messages"]
                    ]
                else:
                    # Try to fetch messages directly as fallback
                    st.session_state.messages = []
                    try:
                        cursor.execute("SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at", (conversation_id,))
                        for msg in cursor.fetchall():
                            st.session_state.messages.append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })
                    except Exception as e:
                        st.error(f"Error loading messages: {str(e)}")
                
                # Redirect to the chat page
                st.switch_page("pages/1_Chat.py")
        
        with col2:
            if st.button("Delete", key=f"delete_{conversation_id}"):
                if "rag_system" in st.session_state:
                    # Delete from both stores
                    success = st.session_state.rag_system.delete_conversation(conversation_id)
                    
                    if success:
                        st.success("Conversation deleted successfully")
                        st.rerun()
                    else:
                        st.error("Failed to delete conversation")
    except Exception as e:
        st.error(f"Error displaying conversation: {str(e)}")
        st.code(traceback.format_exc())

# Add a refresh button at the top
if st.button("Refresh Conversation List"):
    st.rerun()

# Main content area
# Check if there's a specific conversation to display
if "selected_conversation" in st.session_state:
    display_conversation(st.session_state.selected_conversation)
    
    if st.button("← Back to All Conversations"):
        del st.session_state.selected_conversation
        st.rerun()
else:
    # Display all conversations in a table
    conversations = load_conversations(
        query=st.session_state.get("search_query"),
        date_range=st.session_state.get("date_range")
    )
    
    if not conversations:
        st.info("No conversations found. Start chatting to create new conversations!")
        
        # Add debugging info
        with st.expander("Debugging Information"):
            st.write("If you've already had conversations but none are showing:")
            st.write("1. Check if the database file exists")
            st.write("2. Verify that conversations are being saved correctly")
            st.write("3. Check if conversation IDs are consistent between pages")
            
            if "conversation_id" in st.session_state:
                st.write(f"Current conversation ID: {st.session_state.conversation_id}")
            
            # Test direct database query
            try:
                if st.session_state.db and st.session_state.db.conn:
                    cursor = st.session_state.db.conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM conversations")
                    count = cursor.fetchone()[0]
                    st.write(f"Total conversations in database: {count}")
                    
                    if count > 0:
                        st.warning("Conversations exist in the database but aren't being loaded. This may be a query or filter issue.")
            except Exception as e:
                st.error(f"Error querying database: {str(e)}")
    else:
        # Convert to a DataFrame for display
        df_data = []
        for conv in conversations:
            # Format date for display
            try:
                created_date = datetime.fromisoformat(conv["created_at"]).strftime("%Y-%m-%d %H:%M")
                updated_date = datetime.fromisoformat(conv["updated_at"]).strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                created_date = "Unknown"
                updated_date = "Unknown"
            
            # Extract first message as a preview
            preview = conv.get("first_message", "")
            if preview and len(preview) > 100:
                preview = preview[:100] + "..."
            
            df_data.append({
                "ID": conv["id"],
                "Title": conv["title"],
                "Created": created_date,
                "Updated": updated_date,
                "Model": conv["model"],
                "Messages": conv.get("message_count", 0),
                "Preview": preview or "None"
            })
        
        df = pd.DataFrame(df_data)
        
        # Create a selection table
        st.dataframe(
            df.drop(columns=["ID"]),
            use_container_width=True,
            column_config={
                "Title": st.column_config.TextColumn("Title"),
                "Created": st.column_config.TextColumn("Created"),
                "Updated": st.column_config.TextColumn("Updated"),
                "Model": st.column_config.TextColumn("Model"),
                "Messages": st.column_config.NumberColumn("Messages"),
                "Preview": st.column_config.TextColumn("Preview")
            },
            hide_index=True
        )
        
        # Allow selecting a conversation to view
        selected_id = st.selectbox(
            "Select a conversation to view details:",
            options=[conv["id"] for conv in conversations],
            format_func=lambda x: next((c["title"] for c in conversations if c["id"] == x), x)
        )
        
        if st.button("View Conversation"):
            st.session_state.selected_conversation = selected_id
            st.rerun()