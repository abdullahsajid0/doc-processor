import os
import streamlit as st
from groq import Groq
import pdfplumber
from pptx import Presentation
import pandas as pd
from docx import Document
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import time
from typing import Optional, Dict, List
import logging

# Configure custom theme and styling
st.set_page_config(
    page_title="Smart Document Processor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
        /* Main container styling */
        .main {
            padding: 2rem;
        }
        
        /* Custom title styling */
        .title-container {
            background: linear-gradient(90deg, #1E88E5 0%, #1565C0 100%);
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            color: white;
            text-align: center;
        }
        
        /* File uploader styling */
        .uploadedFile {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
            border: 2px dashed #1E88E5;
        }
        
        /* Custom card styling */
        .stCard {
            border-radius: 15px;
            padding: 2rem;
            background: white;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin: 1rem 0;
        }
        
        /* Button styling */
        .stButton>button {
            background: linear-gradient(90deg, #1E88E5 0%, #1565C0 100%);
            color: white;
            border-radius: 25px;
            padding: 0.5rem 2rem;
            border: none;
            transition: all 0.3s;
        }
        
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(30, 136, 229, 0.3);
        }
        
        /* Progress bar styling */
        .stProgress > div > div {
            background-color: #1E88E5;
        }
        
        /* Radio button styling */
        .stRadio > div {
            background-color: white;
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
        }
        
        /* Success message styling */
        .success-message {
            background-color: #4CAF50;
            color: white;
            padding: 1rem;
            border-radius: 10px;
            margin: 1rem 0;
        }
        
        /* Custom metrics styling */
        .metric-container {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 10px;
            text-align: center;
            margin: 0.5rem;
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: bold;
            color: #1E88E5;
        }
        
        .metric-label {
            color: #666;
            font-size: 0.9rem;
        }
    </style>
""", unsafe_allow_html=True)

class DocumentProcessor:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.logger = logging.getLogger(__name__)

    def process_file(self, file) -> dict:
        """Process a single file and return metadata"""
        start_time = time.time()
        text = self.extract_text(file)
        processing_time = time.time() - start_time
        
        return {
            'filename': file.name,
            'size': len(file.getvalue()),
            'text_length': len(text),
            'processing_time': processing_time,
            'content': text
        }

    def extract_text(self, file) -> str:
        try:
            if file.type == "application/pdf":
                with pdfplumber.open(file) as pdf:
                    return "\n".join(page.extract_text() or "" for page in pdf.pages)
            elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                doc = Document(file)
                return "\n".join(paragraph.text for paragraph in doc.paragraphs)
            elif file.type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
                ppt = Presentation(file)
                return "\n".join(shape.text for slide in ppt.slides 
                               for shape in slide.shapes if hasattr(shape, "text"))
            elif file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                df = pd.read_excel(file)
                return df.to_string(index=False)
            elif file.type in ["text/plain", "application/octet-stream"]:
                return file.getvalue().decode("utf-8")
            else:
                return "Unsupported file format"
        except Exception as e:
            self.logger.error(f"Error processing file: {str(e)}")
            return f"Error processing file: {str(e)}"

    def process_document(self, content: str, task: str = "summarize", 
                        question: Optional[str] = None) -> str:
        try:
            if not content.strip():
                return "No content to process"

            prompt_content = {
                "summarize": f"Summarize the following content concisely:\n\n{content}",
                "ask_question": f"Answer based on the content provided:\n\nContent:\n{content}\n\nQuestion: {question}",
                "combine": f"Combine and sort the following content without losing details:\n\n{content}"
            }.get(task, "Invalid task")

            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt_content}],
                model="llama-3.1-70b-versatile",
            )
            return chat_completion.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Error in API call: {str(e)}")
            return f"Error processing request: {str(e)}"

def main():
    # Custom title with gradient background
    st.markdown("""
        <div class="title-container">
            <h1>📄 Smart Document Processor</h1>
            <p>Upload your documents and let AI do the magic</p>
        </div>
    """, unsafe_allow_html=True)

    # Initialize processor
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("🔑 GROQ_API_KEY environment variable not set")
        return
        
    processor = DocumentProcessor(api_key)
    
    # Create two columns for layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
            <div class="stCard">
                <h3>📎 Upload Your Documents</h3>
            </div>
        """, unsafe_allow_html=True)
        
        uploaded_files = st.file_uploader(
            "", 
            type=["pdf", "pptx", "docx", "xlsx", "txt", "py", "js", "html", "java", "cpp"], 
            accept_multiple_files=True
        )

    with col2:
        st.markdown("""
            <div class="stCard">
                <h3>📊 Statistics</h3>
            </div>
        """, unsafe_allow_html=True)
        
        if uploaded_files:
            total_files = len(uploaded_files)
            total_size = sum(len(file.getvalue()) for file in uploaded_files)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"""
                    <div class="metric-container">
                        <div class="metric-value">{total_files}</div>
                        <div class="metric-label">Files Uploaded</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col_b:
                st.markdown(f"""
                    <div class="metric-container">
                        <div class="metric-value">{total_size/1024:.1f}KB</div>
                        <div class="metric-label">Total Size</div>
                    </div>
                """, unsafe_allow_html=True)

    if uploaded_files:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        
        # Process files with progress bar
        progress_text = "Processing your documents..."
        my_bar = st.progress(0)
        
        processed_files = []
        for idx, file in enumerate(uploaded_files):
            processed = processor.process_file(file)
            processed_files.append(processed)
            my_bar.progress((idx + 1) / len(uploaded_files))
            
        combined_text = "\n\n".join(file['content'] for file in processed_files)
        
        # Task selection with custom styling
        task = st.radio("🎯 Choose Your Task", ["Summarize", "Ask Questions", "Combine"],
                       help="Select what you want to do with your documents")
        
        if task == "Ask Questions":
            hint_questions = {
                "main_points": "What are the main points?",
                "findings": "What are the key findings?",
                "recommendations": "What are the recommendations?",
                "custom": "Ask your own question..."
            }
            
            # Custom question selection
            selected_hint = st.selectbox(
                "💭 Select a Question Type",
                options=list(hint_questions.keys()),
                format_func=lambda x: hint_questions[x]
            )
            
            if selected_hint == "custom":
                question = st.text_input("🤔 Enter Your Question:")
            else:
                question = hint_questions[selected_hint]
            
            if st.button("🚀 Get Answer"):
                with st.spinner("🔍 Analyzing your documents..."):
                    response = processor.process_document(
                        combined_text, 
                        task="ask_question",
                        question=question
                    )
                    
                st.markdown("""
                    <div class="stCard">
                        <h3>🎯 Answer</h3>
                        <p>{}</p>
                    </div>
                """.format(response), unsafe_allow_html=True)
                
        elif task == "Summarize":
            if st.button("📝 Generate Summary"):
                with st.spinner("✍️ Creating your summary..."):
                    response = processor.process_document(combined_text, task="summarize")
                    
                st.markdown("""
                    <div class="stCard">
                        <h3>📋 Summary</h3>
                        <p>{}</p>
                    </div>
                """.format(response), unsafe_allow_html=True)
                
        elif task == "Combine":
            st.markdown("""
                <div class="stCard">
                    <h3>📑 Combined Content</h3>
                    <p>{}</p>
                </div>
            """.format(combined_text), unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
