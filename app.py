import os
import streamlit as st
import json
import logging
from src.config import DATA_DIR, BASE_DIR
from src.classifier import PersonaClassifier
from src.rag_pipeline import RAGPipeline
from src.generator import ResponseGenerator
from src.escalator import Escalator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page Configurations
st.set_page_config(
    page_title="Persona Support AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling Injection
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

/* Apply custom font */
html, body, [class*="css"], .stMarkdown {
    font-family: 'Outfit', sans-serif;
}

/* Header Container Styling */
.header-container {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #9333ea 100%);
    padding: 2.5rem;
    border-radius: 20px;
    color: white;
    text-align: center;
    margin-bottom: 2rem;
    box-shadow: 0 10px 25px rgba(124, 58, 237, 0.15);
}

.header-title {
    font-size: 2.8rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.05em;
}

.header-subtitle {
    font-size: 1.2rem;
    opacity: 0.9;
    margin-top: 0.5rem;
    font-weight: 300;
}

/* Glassmorphic Metrics Card */
.metric-card {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
}

/* Chat bubble aesthetics */
.chat-row-user {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 1rem;
}

.chat-row-agent {
    display: flex;
    justify-content: flex-start;
    margin-bottom: 1rem;
}

.chat-bubble-user {
    background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
    color: white;
    padding: 12px 18px;
    border-radius: 18px 18px 4px 18px;
    max-width: 75%;
    box-shadow: 0 4px 15px rgba(79, 70, 229, 0.2);
    font-size: 1.05rem;
    line-height: 1.4;
}

.chat-bubble-agent {
    background-color: #1e1b4b;
    color: #f3f4f6;
    padding: 12px 18px;
    border-radius: 18px 18px 18px 4px;
    max-width: 75%;
    border: 1px solid #312e81;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    font-size: 1.05rem;
    line-height: 1.4;
}

/* Badges */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    margin-bottom: 6px;
}

.badge-tech {
    background-color: rgba(6, 182, 212, 0.2);
    color: #22d3ee;
    border: 1px solid #06b6d4;
}

.badge-frustrated {
    background-color: rgba(244, 63, 94, 0.2);
    color: #fb7185;
    border: 1px solid #f43f5e;
}

.badge-exec {
    background-color: rgba(16, 185, 129, 0.2);
    color: #34d399;
    border: 1px solid #10b981;
}

.badge-escalated {
    background-color: rgba(239, 68, 68, 0.25);
    color: #f87171;
    border: 1px solid #ef4444;
}
</style>
""", unsafe_allow_html=True)

# Initialize Session States
if "history" not in st.session_state:
    st.session_state.history = []
if "frustration_count" not in st.session_state:
    st.session_state.frustration_count = 0
if "escalated" not in st.session_state:
    st.session_state.escalated = False
if "handoff_summary" not in st.session_state:
    st.session_state.handoff_summary = None

# Initialize Core Services (cached to prevent re-instantiation on every render)
@st.cache_resource
def get_services():
    try:
        classifier = PersonaClassifier()
        rag_pipeline = RAGPipeline()
        generator = ResponseGenerator()
        escalator = Escalator()
        return classifier, rag_pipeline, generator, escalator
    except Exception as e:
        st.error(f"Failed to initialize core AI services: {e}")
        return None, None, None, None

classifier, rag_pipeline, generator, escalator = get_services()

# Auto-ingest Knowledge Base on startup if database is empty
if rag_pipeline:
    try:
        count = rag_pipeline.collection.count()
        if count == 0:
            with st.spinner("Initializing Knowledge Base for first run..."):
                rag_pipeline.ingest_knowledge_base()
    except Exception as e:
        logger.error(f"Error checking/initializing database count: {e}")

# Header Banner
st.markdown("""
<div class="header-container">
    <h1 class="header-title">Persona-Adaptive Support Center</h1>
    <p class="header-subtitle">AI-Driven RAG Support Agent with Sentiment tone alignment & human handoff</p>
</div>
""", unsafe_allow_html=True)

# Split Layout: Chat area (Left) and Metrics dashboard (Right)
col_chat, col_metrics = st.columns([2, 1])

with col_chat:
    st.subheader("💬 Support Conversation")
    
    # Render Chat History
    chat_container = st.container()
    with chat_container:
        for idx, chat in enumerate(st.session_state.history):
            # Customer bubble
            st.markdown(
                f'<div class="chat-row-user"><div class="chat-bubble-user">{chat["user"]}</div></div>', 
                unsafe_allow_html=True
            )
            
            # Agent bubble
            agent_msg = chat["agent"]
            st.markdown(
                f'<div class="chat-row-agent"><div class="chat-bubble-agent">{agent_msg}</div></div>', 
                unsafe_allow_html=True
            )

    # Escalated Status Banner
    if st.session_state.escalated:
        st.error("⚠️ This conversation has been escalated to a Human Support Representative. The AI agent is currently paused.")
    
    # Input Area (Disabled if Escalated)
    def handle_submit():
        user_input = st.session_state.chat_input
        if not user_input.strip():
            return
        
        # Clear input field immediately
        st.session_state.chat_input = ""
        
        # 1. Persona Detection
        classification = classifier.classify(user_input)
        persona = classification.get("persona", "Technical Expert")
        confidence = classification.get("confidence", 0.5)
        reasoning = classification.get("reasoning", "")
        
        # Track frustration state count
        if persona == "Frustrated User":
            st.session_state.frustration_count += 1
        else:
            st.session_state.frustration_count = 0

        # 2. Context Retrieval
        context_chunks = rag_pipeline.retrieve_context(user_input, top_k=3)
        
        # 3. Escalation Check
        should_esc, esc_reason = escalator.should_escalate(
            query=user_input,
            context_chunks=context_chunks,
            frustration_count=st.session_state.frustration_count
        )
        
        # Build history format for Escalator summary
        formatted_history = []
        for chat in st.session_state.history:
            formatted_history.append({"role": "user", "content": chat["user"]})
            formatted_history.append({"role": "assistant", "content": chat["agent"]})
        
        # Add current query
        formatted_history.append({"role": "user", "content": user_input})
        
        if should_esc:
            st.session_state.escalated = True
            # Generate Handoff Summary
            handoff = escalator.generate_handoff_summary(
                query=user_input,
                persona=persona,
                conversation_history=formatted_history,
                context_chunks=context_chunks
            )
            st.session_state.handoff_summary = handoff
            agent_response = (
                "⚠️ I apologize for any convenience caused. Due to the nature of your request, "
                "I am escalating this ticket to a live human representative. They will review our interaction "
                "history and be with you shortly."
            )
        else:
            # 4. Generate Tone-Adaptive Response
            agent_response = generator.generate_response(user_input, persona, context_chunks)
            if agent_response == "I could not find sufficient information in the knowledge base.":
                should_esc = True
                esc_reason = "The requested information could not be found in the support documentation."
                st.session_state.escalated = True
                
                # Generate Handoff Summary
                handoff = escalator.generate_handoff_summary(
                    query=user_input,
                    persona=persona,
                    conversation_history=formatted_history,
                    context_chunks=context_chunks
                )
                st.session_state.handoff_summary = handoff
                agent_response = (
                    "⚠️ I apologize for the inconvenience. I could not locate the necessary information in our "
                    "knowledge base to address your request. I am connecting you with a live human representative "
                    "who will review our conversation logs and assist you shortly."
                )
        
        # Store in History
        st.session_state.history.append({
            "user": user_input,
            "agent": agent_response,
            "persona": persona,
            "confidence": confidence,
            "reasoning": reasoning,
            "escalated": should_esc,
            "escalation_reason": esc_reason if should_esc else None,
            "retrieved_sources": context_chunks
        })

    # Chat Input Box
    st.text_input(
        "Type your message here...",
        key="chat_input",
        on_change=handle_submit,
        disabled=st.session_state.escalated,
        placeholder="e.g. What are the header parameter requirements for bearer token auth?"
    )

    # Action buttons
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Reset Conversation", use_container_width=True):
            st.session_state.history = []
            st.session_state.frustration_count = 0
            st.session_state.escalated = False
            st.session_state.handoff_summary = None
            st.rerun()
    
    with col_btn2:
        if st.session_state.escalated:
            if st.button("Resolve Escalation (Reset)", type="primary", use_container_width=True):
                st.session_state.escalated = False
                st.session_state.handoff_summary = None
                st.session_state.frustration_count = 0
                st.rerun()

# Sidebar / Panel diagnostics
with col_metrics:
    st.subheader("📊 Diagnostic Panel")
    
    # Collection count
    db_count = 0
    if rag_pipeline:
        try:
            db_count = rag_pipeline.collection.count()
        except Exception:
            pass
            
    st.markdown(f"""
    <div class="metric-card">
        <h5 style="margin:0; opacity:0.8;">Knowledge Base Index</h5>
        <h2 style="margin:5px 0 0 0; color:#818cf8;">{db_count} Chunks</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Ingestion Controls
    if st.button("Re-index Knowledge Base", use_container_width=True):
        if rag_pipeline:
            with st.spinner("Re-indexing support files from data/ directory..."):
                chunks_added = rag_pipeline.ingest_knowledge_base()
                st.success(f"Success! Indexed {chunks_added} document chunks.")
                st.rerun()

    # Diagnostics for latest chat turn
    if st.session_state.history:
        latest_turn = st.session_state.history[-1]
        
        st.markdown("Latest Turn Analytics")
        
        # Persona badge
        p = latest_turn["persona"]
        badge_class = "badge-tech"
        if p == "Frustrated User":
            badge_class = "badge-frustrated"
        elif p == "Business Executive":
            badge_class = "badge-exec"
            
        st.markdown(f"""
        <div class="metric-card">
            <span class="badge {badge_class}">{p}</span>
            <h4 style="margin:5px 0 0 0;">Confidence: {latest_turn['confidence'] * 100:.1f}%</h4>
            <p style="font-size:0.9rem; opacity:0.8; margin-top:5px;"><b>Reasoning:</b> {latest_turn['reasoning']}</p>
        </div>
        """, unsafe_allow_html=True)

        # Retrieval Sources Info
        sources = latest_turn["retrieved_sources"]
        with st.expander("📚 Retrieved RAG Sources (Top K)", expanded=True):
            if not sources:
                st.info("No sources retrieved for this message.")
            else:
                for idx, src in enumerate(sources):
                    st.markdown(f"""
                    **Chunk {idx+1}**
                    * Source: `{src['source']}` (Page {src['page']})
                    * Similarity Score: `{src['score']:.4f}`
                    ---
                    {src['text']}
                    """)

        # Escalation Detail
        if latest_turn["escalated"] or st.session_state.escalated:
            st.markdown("⚠️ Handoff Summary")
            st.markdown("""
            <div class="metric-card" style="border-color:#ef4444;">
                <span class="badge badge-escalated">Escalated</span>
                <p style="font-size:0.9rem; margin-top:5px;"><b>Trigger Reason:</b><br>
                <code>""" + (latest_turn.get("escalation_reason") or "Manual or Persistent Trigger") + """</code></p>
            </div>
            """, unsafe_allow_html=True)

            if st.session_state.handoff_summary:
                st.code(json.dumps(st.session_state.handoff_summary, indent=2), language="json")
    else:
        st.info("Awaiting customer interaction. Send a message to see real-time diagnostics.")
