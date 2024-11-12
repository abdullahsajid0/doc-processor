import os
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF for PDF
import pdfplumber
from pptx import Presentation
import pandas as pd
from docx import Document
from io import BytesIO

# Access the secret API key
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

# Function to extract text from different file formats
def extract_text(file):
    if file.type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            return "\n".join(page.extract_text() for page in pdf.pages)
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(file)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    elif file.type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
        ppt = Presentation(file)
        return "\n".join(shape.text for slide in ppt.slides for shape in slide.shapes if hasattr(shape, "text"))
    elif file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        df = pd.read_excel(file)
        return df.to_string(index=False)
    elif file.type in ["text/plain", "application/octet-stream"]:  # For plain text and C++ files
        return file.getvalue().decode("utf-8")
    else:
        return "Unsupported file format"

# Function to call Groq API with LLaMA
def process_document(content, task="summarize"):
    prompt_content = f"{task} the following content:\n\n{content}"
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt_content}],
        model="llama-3.1-70b-versatile",
    )
    return chat_completion.choices[0].message.content

# Streamlit App UI
st.title("Enhanced Document Processing with LLaMA")
st.write("Upload your documents (PDF, PPTX, Word, Excel, C++, or programming files) and choose a task.")

# File upload with added support for C++ files
uploaded_files = st.file_uploader(
    "Upload Files", 
    type=["pdf", "pptx", "docx", "xlsx", "txt", "py", "js", "html", "java", "cpp"], 
    accept_multiple_files=True
)

if uploaded_files:
    combined_text = ""
    for file in uploaded_files:
        combined_text += extract_text(file) + "\n\n"
    
    # Task selection
    task = st.selectbox("Choose a task", ["Summarize", "Ask Questions", "Combine"])
    
    # Generate LLaMA response
    if st.button("Process Document"):
        task_choice = "summarize" if task == "Summarize" else "provide information on"
        response = process_document(combined_text, task=task_choice)
        
        st.subheader("Your Processed Document")
        st.write(response)
        
        # Output format selection
        output_format = st.selectbox("Download as", ["PDF", "Word"])
        
        # Generate downloadable file
        if output_format == "PDF":
            pdf_bytes = BytesIO()
            pdf = Document()
            pdf.add_paragraph(response)
            pdf.save(pdf_bytes)
            st.download_button(label="Download PDF", data=pdf_bytes, file_name="output.pdf", mime="application/pdf")
        
        elif output_format == "Word":
            word_doc = Document()
            word_doc.add_paragraph(response)
            word_bytes = BytesIO()
            word_doc.save(word_bytes)
            st.download_button(label="Download Word", data=word_bytes, file_name="output.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
