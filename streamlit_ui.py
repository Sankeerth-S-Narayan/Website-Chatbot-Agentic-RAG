from __future__ import annotations
from typing import Literal, TypedDict
import asyncio
import os
import time

import streamlit as st
import json
from supabase import Client
from sentence_transformers import SentenceTransformer

# Import our simplified expert
from stanford_medical_facilities_expert import stanford_medical_facilities_expert, StanfordMedicalFacilitiesDeps

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize embedding model
embedding_model = SentenceTransformer('all-mpnet-base-v2')

supabase: Client = Client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

class ChatMessage(TypedDict):
    """Format of messages sent to the browser/API."""

    role: Literal['user', 'model']
    timestamp: str
    content: str

async def run_agent_with_streaming(user_input: str, container=None):
    """
    Run the agent with streaming text for the user_input prompt.
    Returns the complete response text for session state storage.
    """
    # Run the agent and get the result
    result = await stanford_medical_facilities_expert.run_stream(user_input)
    
    # We'll gather partial text to show incrementally
    partial_text = ""
    
    # Use provided container or create a new placeholder
    if container:
        message_placeholder = container.empty()
    else:
        message_placeholder = st.empty()

    # Render partial text as it arrives
    async for chunk in result.stream_text(delta=True):
        partial_text += chunk
        message_placeholder.markdown(partial_text)
    
    # Return the complete response text
    return partial_text

async def main():
    st.set_page_config(
        page_title="Standford Medical Facilities Assistant",
        page_icon="🏥",
        layout="wide"
    )
    
    # Custom CSS for medical branding and improved loading animations
    st.markdown("""
    <style>
    .main-header {
        color: #8C1515;
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        color: #4A4A4A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
    }
    
    /* Medical-themed loading animation */
    .medical-loading-container {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px;
        background: linear-gradient(135deg, #8C1515 0%, #B81D3A 100%);
        border-radius: 12px;
        margin: 8px 0;
        box-shadow: 0 4px 15px rgba(140, 21, 21, 0.2);
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .medical-spinner {
        width: 24px;
        height: 24px;
        border: 3px solid rgba(255,255,255,0.3);
        border-top: 3px solid white;
        border-radius: 50%;
        animation: medical-spin 1s linear infinite;
    }
    
    @keyframes medical-spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .medical-thinking-text {
        color: white;
        font-weight: 600;
        font-size: 14px;
        margin: 0;
        text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    }
    
    .medical-dots {
        display: flex;
        gap: 6px;
        margin-left: auto;
    }
    
    .medical-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: white;
        animation: medical-pulse 1.4s ease-in-out infinite both;
    }
    
    .medical-dot:nth-child(1) { animation-delay: -0.32s; }
    .medical-dot:nth-child(2) { animation-delay: -0.16s; }
    .medical-dot:nth-child(3) { animation-delay: 0s; }
    
    @keyframes medical-pulse {
        0%, 80%, 100% {
            transform: scale(0.8);
            opacity: 0.5;
        }
        40% {
            transform: scale(1);
            opacity: 1;
        }
    }
    
    /* Heartbeat animation for medical theme */
    .heartbeat {
        animation: heartbeat 1.5s ease-in-out infinite;
    }
    
    @keyframes heartbeat {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
    }
    
    /* Fix for message container stability */
    .stChatMessage {
        opacity: 1 !important;
        transition: none !important;
    }
    
    .stChatMessage[data-testid="chatMessage"] {
        background-color: transparent !important;
    }
    
    /* Prevent ghosting effect during streaming */
    .stChatMessage .stMarkdown {
        opacity: 1 !important;
        color: inherit !important;
    }
    
    /* Ensure stable message appearance */
    .stChatMessage[data-testid="chatMessage"] .stMarkdown {
        opacity: 1 !important;
        color: var(--text-color) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">Stanford Medical Facilities Assistant</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Ask any question about the medical facilities at Stanford University.</p>', unsafe_allow_html=True)
    
    # Initialize chat history in session state if not present
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display all messages from the conversation so far
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(msg["content"])
    
    # Create a stable container for the current assistant response
    if "current_response_container" not in st.session_state:
        st.session_state.current_response_container = None

    # Chat input for the user
    user_input = st.chat_input("What questions do you have about medical facilities?")

    if user_input:
        # Add user message to history
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": str(asyncio.get_event_loop().time())
        })
        
        # Display user prompt in the UI
        with st.chat_message("user"):
            st.markdown(user_input)

        # Create a stable assistant message container
        assistant_container = st.chat_message("assistant")
        
        # Show medical-themed loading animation
        loading_placeholder = assistant_container.empty()
        loading_placeholder.markdown("""
        <div class="medical-loading-container">
            <div class="medical-spinner"></div>
            <p class="medical-thinking-text">🏥 Searching medical facilities database...</p>
            <div class="medical-dots">
                <div class="medical-dot"></div>
                <div class="medical-dot"></div>
                <div class="medical-dot"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Brief pause to show the loading state
        await asyncio.sleep(2.0)
        
        # Clear the loading animation
        loading_placeholder.empty()
        
        # Run the agent once and capture the streaming response
        response_text = await run_agent_with_streaming(user_input, assistant_container)
        
        # Add assistant message to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "timestamp": str(asyncio.get_event_loop().time())
        })

if __name__ == "__main__":
    asyncio.run(main()) 