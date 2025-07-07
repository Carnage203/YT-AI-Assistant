# -*- coding: utf-8 -*-
import streamlit as st
import asyncio
from langchain.schema import HumanMessage
from main import graph  
import time
import re


try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

# Function to convert URLs to clickable links
def make_urls_clickable(text):
    """
    Convert URLs in text to clickable HTML links
    """
    # Regular expression to match URLs
    url_pattern = r'https?://[^\s<>"\'(){}[\]]+|www\.[^\s<>"\'(){}[\]]+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s<>"\'(){}[\]]*)?'
    
    def replace_url(match):
        url = match.group(0)
        # Add https:// if not present
        if not url.startswith(('http://', 'https://')):
            href_url = 'https://' + url
        else:
            href_url = url
        
        # Create clickable link with styling
        return f'<a href="{href_url}" target="_blank" style="color: #ff6b6b; text-decoration: underline; font-weight: bold;">{url}</a>'
    
    # Replace URLs with clickable links
    return re.sub(url_pattern, replace_url, text)

# Async-safe runner for Streamlit thread
def run_async_task(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(coro)
    loop.close()
    return result

# Custom CSS for enhanced styling
st.markdown("""
<style>
    /* Main container styling */
    .main-container {
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    /* Title styling */
    .main-title {
        text-align: center;
        color: white;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .subtitle {
        text-align: center;
        color: #f0f0f0;
        font-size: 1.2rem;
        margin-bottom: 2rem;
        opacity: 0.9;
    }
    
    /* Input section styling */
    .input-section {
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem 0;
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    /* Input section headings */
    .input-section h3 {
        color: white !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
        margin-bottom: 1rem !important;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(45deg, #ff6b6b, #ee5a24);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.75rem 2rem;
        font-size: 1.1rem;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 5px 15px rgba(255,107,107,0.3);
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(255,107,107,0.4);
    }
    
    /* Spinning animation for processing button */
    .processing-button {
        animation: spin 1s linear infinite !important;
        background: linear-gradient(45deg, #ff6b6b, #ee5a24) !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.75rem 2rem !important;
        font-size: 1.1rem !important;
        font-weight: bold !important;
        cursor: not-allowed !important;
        box-shadow: 0 5px 15px rgba(255,107,107,0.3) !important;
        width: 100% !important;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* Disabled button styling */
    .stButton > button:disabled {
        background: #666 !important;
        cursor: not-allowed !important;
        transform: none !important;
        box-shadow: none !important;
    }
    
    /* Result section styling */
    .result-container {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        border-radius: 15px;
        padding: 2rem;
        margin: 2rem 0;
        border: 1px solid rgba(255,255,255,0.2);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    
    /* Progress bar styling */
    .progress-container {
        background: rgba(255,255,255,0.15);
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    /* Progress container headings */
    .progress-container h3 {
        color: white !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    }
    
    /* Progress status text */
    .progress-container p, .progress-container strong {
        color: white !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    }
    
    /* Card styling */
    .info-card {
        background: rgba(255,255,255,0.15);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #ff6b6b;
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    /* Card text styling */
    .info-card h4 {
        color: white !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
        margin-bottom: 0.5rem !important;
    }
    
    .info-card ul, .info-card li {
        color: white !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    }
    
    /* Radio button styling */
    .stRadio > div {
        background: rgba(255,255,255,0.15);
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    /* Radio button labels */
    .stRadio label {
        color: white !important;
        font-weight: bold !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    }
    
    /* Radio button options */
    .stRadio div[role="radiogroup"] label {
        color: white !important;
    }
    
    /* Text area styling */
    .stTextArea > div > div > textarea {
        background: rgba(30,30,30,0.9) !important;
        color: white !important;
        border-radius: 10px;
        border: 2px solid rgba(255,255,255,0.3);
        transition: all 0.3s ease;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #ff6b6b !important;
        box-shadow: 0 0 15px rgba(255,107,107,0.3) !important;
        background: rgba(40,40,40,0.95) !important;
    }
    
    .stTextArea > div > div > textarea::placeholder {
        color: rgba(255,255,255,0.7) !important;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Animation for results */
    .fade-in {
        animation: fadeIn 0.8s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Success message styling */
    .success-message {
        background: linear-gradient(45deg, #56ab2f, #a8e6cf);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        font-weight: bold;
    }
    
    /* Error message styling */
    .error-message {
        background: linear-gradient(45deg, #ff416c, #ff4b2b);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        font-weight: bold;
    }
    
    /* Link styling for clickable URLs */
    a {
        color: #ff6b6b !important;
        text-decoration: underline !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
    }
    
    a:hover {
        color: #ee5a24 !important;
        text-shadow: 0 0 5px rgba(255,107,107,0.3) !important;
    }
    
    /* Copy feedback styling */
    .copy-feedback {
        background: linear-gradient(45deg, #4CAF50, #45a049);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        text-align: center;
        font-weight: bold;
        animation: slideIn 0.3s ease-in;
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
</style>
""", unsafe_allow_html=True)


st.set_page_config(
    page_title="YT AI Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)


if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'result_history' not in st.session_state:
    st.session_state.result_history = []
if 'current_output' not in st.session_state:
    st.session_state.current_output = ""
if 'copy_success' not in st.session_state:
    st.session_state.copy_success = False


with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 1rem;">
        <h2 style="color: #667eea;">YT Assistant</h2>
        <p style="color: #666;">Your AI-powered YouTube companion</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Quick tips
    st.markdown("""
    <div class="info-card">
        <h4>Quick Tips:</h4>
        <ul>
            <li>Paste any YouTube URL</li>
            <li>Ask questions about videos</li>
            <li>Choose your preferred summary length</li>
            <li>Get instant AI-powered insights</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    
    if st.session_state.result_history:
        st.markdown("### Recent Results")
        for i, result in enumerate(st.session_state.result_history[-3:]):
            with st.expander(f"Result {len(st.session_state.result_history) - i}"):
                st.write(result[:100] + "..." if len(result) > 100 else result)

# Main content
st.markdown("""
<div class="main-container">
    <div class="main-title">YouTube AI Assistant</div>
    <div class="subtitle">Transform any YouTube video into actionable insights</div>
</div>
""", unsafe_allow_html=True)


st.markdown('<div class="input-section">', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("### Enter YouTube URL or Question")
    user_input = st.text_area(
        "",
        placeholder="Paste your YouTube video URL here or ask a question about a video...",
        height=120,
        key="user_input"
    )

with col2:
    st.markdown("### Summary Settings")
    summary_length = st.radio(
        "",
        options=["short", "medium", "long"],
        index=1,
        format_func=lambda x: {
            "short": "Quick (1-2 min)",
            "medium": "Balanced (3-5 min)", 
            "long": "Detailed (5+ min)"
        }[x]
    )

st.markdown('</div>', unsafe_allow_html=True)


col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.session_state.processing:
        
        st.markdown("""
        <div style="text-align: center;">
            <button class="processing-button" disabled>
                🔄 Processing...
            </button>
        </div>
        """, unsafe_allow_html=True)
        submit_button = False
    else:
        submit_button = st.button("🚀 Process Video", key="submit")


if submit_button:
    if not user_input.strip():
        st.markdown('<div class="error-message">Please enter a valid YouTube URL or question!</div>', unsafe_allow_html=True)
    else:
        
        st.session_state.processing = True
        st.session_state.copy_success = False  
        
        
        st.markdown('<div class="progress-container">', unsafe_allow_html=True)
        st.markdown("### Processing Your Request...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        
        progress_steps = [
            (20, "Analyzing video content..."),
            (40, "Processing with AI..."),
            (60, "Generating summary..."),
            (80, "Finalizing results..."),
            (100, "Complete!")
        ]
        
        try:
            for i, (progress, message) in enumerate(progress_steps[:-1]):
                progress_bar.progress(progress)
                status_text.markdown(f"**{message}**")
                time.sleep(0.5)  
            
            
            State = {
                "messages": [HumanMessage(content=user_input)],
                "summary_length": summary_length
            }
            
            response_state = run_async_task(graph.ainvoke(State))
            
            
            progress_bar.progress(100)
            status_text.markdown("**Complete!**")
            
            
            st.session_state.processing = False
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            
            output = response_state["messages"][-1].content if "messages" in response_state else "⚠️ No final output found."
            st.session_state.current_output = output  
            
            st.markdown('<div class="result-container fade-in">', unsafe_allow_html=True)
            st.markdown("### 🎯 AI-Generated Summary")
            
            
            formatted_output = output.replace('\n', '<br>')
            
            formatted_output = make_urls_clickable(formatted_output)
            
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.98); padding: 1.5rem; border-radius: 10px; color: #2c3e50; line-height: 1.6; border: 1px solid rgba(255,255,255,0.5); box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                {formatted_output}
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Add to history
            st.session_state.result_history.append(output)
            
        except Exception as e:
            progress_bar.progress(0)
            st.session_state.processing = False  
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="error-message">Error: {str(e)}</div>', unsafe_allow_html=True)
            
            
            st.markdown("### Try These Solutions:")
            st.markdown("""
            - Check if the YouTube URL is valid and accessible
            - Ensure your internet connection is stable
            - Try with a different video
            - Contact support if the issue persists
            """)


if st.session_state.current_output:
    
    if st.session_state.copy_success:
        st.markdown('<div class="copy-feedback">✅ Summary copied to clipboard!</div>', unsafe_allow_html=True)
        
        st.session_state.copy_success = False
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        
        if st.button("📋 Copy to Clipboard", key="copy_btn"):
            if PYPERCLIP_AVAILABLE:
                try:
                    pyperclip.copy(st.session_state.current_output)
                    st.session_state.copy_success = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Copy failed: {str(e)}")
                    
                    st.info("📋 Copy the text from the box below:")
                    st.text_area("Select all and copy (Ctrl+A, Ctrl+C):", 
                               value=st.session_state.current_output, 
                               height=100, 
                               key="copy_fallback_error")
            else:
                
                st.info("📋 Copy the text from the box below:")
                st.text_area("Select all and copy (Ctrl+A, Ctrl+C):", 
                           value=st.session_state.current_output, 
                           height=100, 
                           key="copy_fallback_manual")
    
    with col2:
        if st.button("🔄 Process Another"):
            st.session_state.processing = False
            st.session_state.current_output = ""
            st.session_state.copy_success = False
            st.rerun()
            
    with col3:
        
        st.download_button(
            label="💾 Download Summary",
            data=st.session_state.current_output,
            file_name=f"youtube_summary_{int(time.time())}.txt",
            mime="text/plain",
            key="download_summary"
        )

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; color: #666;">
    <p>Powered by Advanced AI • YouTube Video Intelligence • Lightning Fast Processing</p>
</div>
""", unsafe_allow_html=True)