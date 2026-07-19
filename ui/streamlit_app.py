"""
Streamlit UI for Agentic Compliance Auditor
Interactive demo interface
"""
import streamlit as st
import requests
import sys
from pathlib import Path
import json

# Add src to path
#sys.path.append(str(Path(__file__).parent.parent / "src"))

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings

# Page configuration
st.set_page_config(
    page_title="Agentic Compliance Auditor",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API endpoint
API_URL = f"http://localhost:{settings.API_PORT}"

def check_api_health():
    """Check if API is running"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def query_api(query: str, session_id: str):
    """Send query to API"""
    payload = {
        "query": query,
        "session_id": session_id,
    }

    response = requests.post(f"{API_URL}/query", json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        return None


def get_conversation_history(session_id: str):
    """Get conversation history"""
    try:
        response = requests.get(f"{API_URL}/conversation/{session_id}")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []


def main():
    # Header
    st.title("⚖️ Agentic Compliance Auditor")
    st.markdown("*AI-powered compliance checking with autonomous agents*")

    # Check API health
    if not check_api_health():
        st.error("""
         **API Server Not Running**

        Please start the API server first:
        ```bash
        cd src/api
        python main.py
        ```
        """)
        return

    st.success(" Connected to API")

    # Sidebar
    with st.sidebar:
        st.header(" Settings")

        # Session management
        if 'session_id' not in st.session_state:
            st.session_state.session_id = "default_session"

        session_id = st.text_input(
            "Session ID",
            value=st.session_state.session_id,
            help="Unique identifier for conversation tracking"
        )
        st.session_state.session_id = session_id

        # Clear conversation
        if st.button(" Clear Conversation"):
            try:
                requests.delete(f"{API_URL}/conversation/{session_id}")
                st.success("Conversation cleared!")
                st.rerun()
            except:
                st.error("Failed to clear conversation")

        st.divider()

        # System stats
        st.subheader(" System Stats")
        try:
            stats_response = requests.get(f"{API_URL}/stats")
            if stats_response.status_code == 200:
                stats = stats_response.json()
                st.metric("Documents", stats.get('total_chunks', 0))
                st.metric("Embedding Model", stats.get('embedding_model', 'N/A'))
        except:
            st.warning("Could not fetch stats")

        st.divider()

        # About
        st.subheader(" About")
        st.markdown("""
        This system uses:
        - **LangGraph** for agentic workflows
        - **ChromaDB** for vector storage
        - **OpenAI gpt-4o-mini** for LLM inference
        - **FastAPI** for backend API
        """)

    # Main content
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header(" Ask a Compliance Question")

        # Sample questions
        with st.expander(" Sample Questions"):
            st.markdown("""
            - What are the requirements for data retention under GDPR Article 17?
            - How does HIPAA define Protected Health Information?
            - What are the security safeguards required by SOC2?
            - Compare data breach notification requirements in GDPR and HIPAA
            - What is the right to erasure under GDPR?
            """)

        # Query input
        query = st.text_area(
            "Your Question",
            height=100,
            placeholder="e.g., What are the data retention requirements under GDPR?"
        )

        # Submit button
        if st.button(" Submit Query", type="primary"):
            if not query:
                st.warning("Please enter a question")
            else:
                with st.spinner(" Thinking..."):
                    result = query_api(query, session_id)

                    if result:
                        # Display answer
                        st.subheader("📄 Answer")
                        st.markdown(result['answer'])

                        # Display metadata
                        with st.expander("🔍 Details"):
                            if result.get('iterations'):
                                st.write(f"**Iterations:** {result['iterations']}")

                            if result.get('reflection'):
                                st.write(f"**Reflection:** {result['reflection']}")

                            st.write(f"**Timestamp:** {result['timestamp']}")

                        # Display sources
                        st.subheader("📚 Sources")
                        for i, source in enumerate(result.get('sources', [])[:5], 1):
                            with st.expander(f"Source {i}: {source.get('metadata', {}).get('filename', 'Unknown')}"):
                                st.write(f"**Citation:** {source.get('citation', '')}")
                                st.write(f"**Relevance:** {source.get('similarity_score', 0):.2%}")
                                st.write(f"**Section:** {source.get('metadata', {}).get('section', 'N/A')}")
                                st.text_area("Content", value=source['content'], height=150, disabled=True)
                    else:
                        st.error("Failed to get response from API")

    with col2:
        st.header("💭 Conversation History")

        # Get conversation history
        history = get_conversation_history(session_id)

        if history:
            for msg in history:
                role = msg['role']
                content = msg['content']

                if role == 'user':
                    st.info(f"**You:** {content}")
                elif role == 'assistant':
                    st.success(f"**Assistant:** {content[:200]}...")
        else:
            st.write("*No conversation history*")

    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center'>
        <p>Using LangGraph, ChromaDB, and OpenAI gpt-4o-mini</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
