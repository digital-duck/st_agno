import streamlit as st
import uuid
import time
from datetime import datetime
import traceback
from agno.agent import Agent
from agno.models.ollama import Ollama

from utils.config import (
    DEFAULT_MODEL_LIST, DEFAULT_MODEL
)

# Init page config
st.set_page_config(
    page_title="Agno Chat",
    page_icon="💬",
    layout="wide"
)

# Title and description
st.title("Chat with Agno LLM")

# Debug expander
with st.expander("Debug Information", expanded=False):
    st.subheader("Session State")
    if "conversation_id" in st.session_state:
        st.write(f"Current conversation ID: {st.session_state.conversation_id}")
    if "conversation_title" in st.session_state:
        st.write(f"Conversation title: {st.session_state.conversation_title}")
    if "messages" in st.session_state:
        st.write(f"Messages count: {len(st.session_state.messages)}")
    
    # Database status
    st.subheader("Database Status")
    if "db" in st.session_state:
        st.write("SQLite DB initialized: Yes")
        # Test direct database interaction
        try:
            cursor = st.session_state.db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM conversations")
            count = cursor.fetchone()[0]
            st.write(f"Total conversations in database: {count}")
            
            # Show messages count
            cursor.execute("SELECT COUNT(*) FROM messages")
            msg_count = cursor.fetchone()[0]
            st.write(f"Total messages in database: {msg_count}")
            
            # List last 5 conversations
            cursor.execute("SELECT id, title FROM conversations ORDER BY created_at DESC LIMIT 5")
            recent = cursor.fetchall()
            if recent:
                st.write("Recent conversations:")
                for r in recent:
                    # Count messages for this conversation
                    cursor.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (r['id'],))
                    this_msg_count = cursor.fetchone()[0]
                    st.write(f"- {r['title']} (ID: {r['id']}, Messages: {this_msg_count})")
            else:
                st.write("No recent conversations found.")
        except Exception as e:
            st.error(f"Database error: {str(e)}")
    else:
        st.write("SQLite DB initialized: No")
    
    # Test conversation saving
    if st.button("Force Save Current Conversation"):
        try:
            if "db" in st.session_state and "conversation_id" in st.session_state:
                # Create conversation if it doesn't exist
                existing = st.session_state.db.get_conversation(st.session_state.conversation_id)
                if not existing:
                    title = st.session_state.get("conversation_title", "Forced Save")
                    model = st.session_state.get("selected_model", DEFAULT_MODEL)
                    st.session_state.db.create_conversation(
                        title=title,
                        model=model
                    )
                    st.write(f"Created new conversation with ID: {st.session_state.conversation_id}")
                
                # Add messages
                if "messages" in st.session_state and st.session_state.messages:
                    for msg in st.session_state.messages:
                        msg_id = st.session_state.db.add_message(
                            st.session_state.conversation_id, 
                            msg["role"], 
                            msg["content"]
                        )
                        st.write(f"Added message: {msg_id} (role: {msg['role']}, length: {len(msg['content'])})")
                    
                    st.success("Conversation manually saved!")
                else:
                    st.warning("No messages to save")
        except Exception as e:
            st.error(f"Error saving: {str(e)}")
            st.code(traceback.format_exc())

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    # Model selection from Ollama API
    if "ollama_models" in st.session_state and st.session_state.ollama_models:
        ollama_model_list = st.session_state.ollama_models
        # st.info(ollama_model_list)  # DEBUG
        selected_model = st.selectbox(
            "Select Model",
            ollama_model_list,
            index=ollama_model_list.index(DEFAULT_MODEL)
        )
    else:
        selected_model = st.selectbox(
            "Select Model",
            DEFAULT_MODEL_LIST,
            index=DEFAULT_MODEL_LIST.index(DEFAULT_MODEL)
        )
        st.warning("Using default models. Connect to Ollama to see installed models.")
    
    # Store selected model in session state for other functions
    st.session_state.selected_model = selected_model
    
    # Ollama connection status
    if "ollama_connected" in st.session_state and st.session_state.ollama_connected:
        st.success("✅ Connected to Ollama")
    else:
        st.error("❌ Not connected to Ollama")
        st.info("Install Ollama and run it with `ollama serve`. Then restart this app.")
    
    # Streaming option
    stream_option = st.checkbox("Enable streaming", value=True)
    
    # RAG options
    st.subheader("RAG Settings")
    use_rag = st.checkbox("Use RAG for context", value=True)
    
    if use_rag:
        use_semantic = st.checkbox("Use semantic search", value=True)
        use_text = st.checkbox("Use text search", value=True)
        context_results = st.slider("Number of context results", 1, 10, 3)
    
    # Conversation title
    if "conversation_title" in st.session_state:
        new_title = st.text_input(
            "Conversation title", 
            value=st.session_state.conversation_title
        )
        if new_title != st.session_state.conversation_title:
            st.session_state.conversation_title = new_title
            # Update the title in the database if conversation exists
            if "db" in st.session_state and st.session_state.db:
                try:
                    cursor = st.session_state.db.conn.cursor()
                    cursor.execute(
                        "UPDATE conversations SET title = ? WHERE id = ?",
                        (new_title, st.session_state.conversation_id)
                    )
                    st.session_state.db.conn.commit()
                except Exception as e:
                    st.warning(f"Failed to update title: {str(e)}")
    
    st.markdown("---")
    
    # Clear conversation button
    if st.button("Clear Current Conversation"):
        # Create a new conversation
        st.session_state.conversation_id = str(uuid.uuid4())
        st.session_state.conversation_title = "New Conversation"
        st.session_state.messages = []
        st.rerun()

# Function to save the current conversation to the database
def save_conversation_to_db(conversation_id, title, model, messages):
    """Save the current conversation to SQLite database."""
    if "db" not in st.session_state or not st.session_state.db:
        st.warning("Database not initialized. Conversation not saved.")
        return False
    
    try:
        # First, check if conversation exists
        existing = st.session_state.db.get_conversation(conversation_id)
        
        # Create conversation if it doesn't exist
        if not existing:
            st.session_state.db.create_conversation(title=title, model=model)
        
        # Now add all messages that aren't already in the database
        if existing and 'messages' in existing:
            existing_message_contents = {msg['content'] for msg in existing['messages']}
        else:
            existing_message_contents = set()
        
        # Add only new messages
        for msg in messages:
            # Skip if this exact message content already exists in the conversation
            if msg['content'] in existing_message_contents:
                continue
                
            # Add the message
            st.session_state.db.add_message(
                conversation_id,
                msg['role'],
                msg['content']
            )
        
        return True
    except Exception as e:
        st.error(f"Error saving conversation: {str(e)}")
        return False

# Initialize the agent (with error handling)
def get_agent(model_name):
    """Get an Agno agent with error handling."""
    try:
        agent = Agent(model=Ollama(id=model_name), markdown=True)
        # Quick test if the agent is working
        test_response = agent.run("test")
        if test_response is None:
            st.error(f"Could not initialize agent with model {model_name}. Check if Ollama is running and the model is installed.")
            return None
        return agent
    except Exception as e:
        st.error(f"Error initializing agent: {str(e)}")
        st.info("Make sure Ollama is running with `ollama serve` and the model is installed with `ollama pull {model_name}`")
        return None

# Ensure conversation ID and title exist
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

if "conversation_title" not in st.session_state:
    st.session_state.conversation_title = "New Conversation"

# Ensure messages list exists
if "messages" not in st.session_state:
    st.session_state.messages = []
elif len(st.session_state.messages) > 0:
    # If we have messages already, make sure they're saved to the database
    save_conversation_to_db(
        st.session_state.conversation_id, 
        st.session_state.conversation_title, 
        st.session_state.get("selected_model", DEFAULT_MODEL),
        st.session_state.messages
    )

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
prompt = st.chat_input("Type your message here...")

# Process user input
if prompt:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Process with RAG if enabled
    context = ""
    if use_rag and (use_semantic or use_text) and "rag_system" in st.session_state:
        try:
            with st.spinner("Searching for relevant context..."):
                search_results = st.session_state.rag_system.search(
                    query=prompt,
                    use_semantic=use_semantic,
                    use_text=use_text,
                    limit=context_results
                )
                
                if search_results:
                    context = st.session_state.rag_system.format_context_for_prompt(search_results)
        except Exception as e:
            st.warning(f"Error retrieving context: {str(e)}")
    
    # Prepare full prompt with context if available
    full_prompt = prompt
    if context:
        full_prompt = f"{context}\n\nUser query: {prompt}\n\nPlease respond based on the above context and your knowledge:"
    
    # Get agent and generate response
    agent = get_agent(selected_model)
    
    # Display assistant response
    with st.chat_message("assistant"):
        if agent is None:
            error_message = "⚠️ Could not connect to Ollama. Please make sure Ollama is running and the selected model is installed."
            st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
        else:
            try:
                if stream_option:
                    # Create an empty placeholder
                    message_placeholder = st.empty()
                    full_response = ""
                    
                    # Stream the response with error handling
                    try:
                        # Use the run method instead of stream if there are issues
                        try:
                            # First try to use streaming
                            stream_response = agent.stream(full_prompt)
                            
                            # Check if stream_response is a proper generator
                            if hasattr(stream_response, '__iter__') and callable(getattr(stream_response, '__iter__')):
                                for chunk in stream_response:
                                    if chunk is None:
                                        continue
                                    full_response += chunk
                                    message_placeholder.markdown(full_response + "▌")
                                    time.sleep(0.01)
                            else:
                                # If stream_response is not iterable, switch to run
                                raise TypeError("Stream response is not iterable")
                                
                        except (TypeError, AttributeError) as stream_err:
                            st.warning(f"Error streaming response: {str(stream_err)}")
                            # Fallback to run method
                            with st.spinner("Generating response (no streaming)..."):
                                run_response = agent.run(full_prompt)
                                full_response = run_response.content if hasattr(run_response, 'content') else str(run_response)
                                
                        # Display the final response
                        message_placeholder.markdown(full_response)
                        # Add to messages
                        st.session_state.messages.append({"role": "assistant", "content": full_response})
                        
                    except Exception as e:
                        st.error(f"Error generating response: {str(e)}")
                        # Try non-streaming as fallback
                        try:
                            with st.spinner("Generating response (fallback mode)..."):
                                response = agent.run(full_prompt)
                                if response and hasattr(response, 'content'):
                                    st.markdown(response.content)
                                    # Add to messages
                                    st.session_state.messages.append({"role": "assistant", "content": response.content})
                                else:
                                    error_msg = "Failed to get response from Ollama"
                                    st.error(error_msg)
                                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                        except Exception as e2:
                            error_msg = f"Failed to communicate with Ollama: {str(e2)}"
                            st.error(error_msg)
                            st.session_state.messages.append({"role": "assistant", "content": error_msg})
                else:
                    # Generate the response without streaming
                    try:
                        with st.spinner("Generating response..."):
                            response = agent.run(full_prompt)
                            if response and hasattr(response, 'content'):
                                st.markdown(response.content)
                                # Add to messages
                                st.session_state.messages.append({"role": "assistant", "content": response.content})
                            else:
                                error_msg = "Failed to get response from Ollama"
                                st.error(error_msg)
                                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    except Exception as e:
                        error_msg = f"Failed to communicate with Ollama: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
            except Exception as e:
                error_message = f"⚠️ Error generating response: {str(e)}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})
    
    # Save the conversation now that we have the user message and response
    save_conversation_to_db(
        st.session_state.conversation_id,
        st.session_state.conversation_title,
        selected_model,
        st.session_state.messages
    )
    
    # Also try to save with RAG system
    if "rag_system" in st.session_state and st.session_state.messages:
        try:
            # Check if this is a new conversation
            is_new = len(st.session_state.messages) <= 2  # Just added user message and AI response
            
            if is_new:
                # Save entire conversation
                st.session_state.rag_system.add_conversation_to_stores(
                    conversation_id=st.session_state.conversation_id,
                    title=st.session_state.conversation_title,
                    model=selected_model,
                    messages=st.session_state.messages
                )
            else:
                # Just save the latest assistant message
                last_message = st.session_state.messages[-1]
                if last_message["role"] == "assistant":
                    st.session_state.rag_system.add_message_to_stores(
                        conversation_id=st.session_state.conversation_id,
                        role=last_message["role"],
                        content=last_message["content"],
                        conversation_title=st.session_state.conversation_title
                    )
        except Exception as e:
            st.warning(f"Failed to save conversation through RAG system: {str(e)}")