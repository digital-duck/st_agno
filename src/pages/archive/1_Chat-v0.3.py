import streamlit as st
import uuid
import time
from datetime import datetime
from agno.agent import Agent
from agno.models.ollama import Ollama

# Init page config
st.set_page_config(
    page_title="Agno Chat",
    page_icon="💬",
    layout="wide"
)

# Title and description
st.header("Chat with Agno LLM")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    # Model selection from Ollama API
    if "ollama_models" in st.session_state and st.session_state.ollama_models:
        selected_model = st.selectbox(
            "Select Model",
            st.session_state.ollama_models,
            index=0
        )
    else:
        selected_model = st.selectbox(
            "Select Model",
            ["llama3.1", "mistral", "mixtral"],
            index=0
        )
        st.warning("Using default models. Connect to Ollama to see installed models.")
    
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
    
    st.markdown("---")
    
    # Clear conversation button
    if st.button("Clear Current Conversation"):
        # Keep the same conversation ID but clear messages
        st.session_state.messages = []
        st.rerun()

# Initialize the agent (cached to prevent recreation)
@st.cache_resource(show_spinner=False)
def get_agent(model_name):
    return Agent(model=Ollama(id=model_name), markdown=True)

# Ensure messages list exists
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
prompt = st.chat_input("Type your message here...")

# Process user input
if prompt:
    # Ensure we have a valid conversation ID
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = str(uuid.uuid4())
    
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Process with RAG if enabled
    context = ""
    if use_rag and (use_semantic or use_text) and "rag_system" in st.session_state:
        with st.spinner("Searching for relevant context..."):
            search_results = st.session_state.rag_system.search(
                query=prompt,
                use_semantic=use_semantic,
                use_text=use_text,
                limit=context_results
            )
            
            if search_results:
                context = st.session_state.rag_system.format_context_for_prompt(search_results)
    
    # Prepare full prompt with context if available
    full_prompt = prompt
    if context:
        full_prompt = f"{context}\n\nUser query: {prompt}\n\nPlease respond based on the above context and your knowledge:"
    
    # Get agent and generate response
    agent = get_agent(selected_model)
    
    # Display assistant response
    with st.chat_message("assistant"):
        if stream_option:
            # Create an empty placeholder
            message_placeholder = st.empty()
            full_response = ""
            
            # Stream the response
            for chunk in agent.stream(full_prompt):
                full_response += chunk
                message_placeholder.markdown(full_response + "▌")
                time.sleep(0.01)
            
            # Display the final response
            message_placeholder.markdown(full_response)
            # Add to messages
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        else:
            # Generate the response without streaming
            with st.spinner("Generating response..."):
                response = agent.run(full_prompt)
                st.markdown(response.content)
                # Add to messages
                st.session_state.messages.append({"role": "assistant", "content": response.content})
    
    # Save conversation and messages to both stores
    if "rag_system" in st.session_state and st.session_state.messages:
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