import os
import streamlit as st
from groq import Groq
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
    elif file.type in ["text/plain", "application/octet-stream"]:
        return file.getvalue().decode("utf-8")
    else:
        return "Unsupported file format"

# Function to call Groq API with LLaMA for summarization or question answering
def process_document(content, task="summarize", question=None):
    if task == "summarize":
        prompt_content = f"Summarize the following content:\n\n{content}"
    elif task == "ask_question" and question:
        prompt_content = f"Answer the following question based on the content provided:\n\nContent:\n{content}\n\nQuestion: {question}"
    else:
        prompt_content = f"Combine the following content without changing in it and make sur no detail is missed while com bining and the data should also be sorted this the the content:\n\n{content}"
    
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt_content}],
        model="llama-3.1-70b-versatile",
    )
    return chat_completion.choices[0].message.content

# Streamlit App UI
st.title("Enhanced Document Processing with LLaMA")
st.write("Upload your documents (PDF, PPTX, Word, Excel, C++, or programming files) and choose a task.")

# File upload
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

    # Initialize response variable
    response = ""

    # Process based on selected task
    if task == "Ask Questions":
        # Example hint questions based on content
        hint_questions = [
            "What are the main points?",
            "Can you explain the key findings?",
            "What are the recommendations?"
        ]

        question = st.text_input("Enter your question here or select one below:")
        for hint in hint_questions:
            if st.button(hint):
                st.text_input("Enter your question here or select one below:")                    
                question = hint

        if st.button("Submit Question"):
            response = process_document(combined_text, task="ask_question", question=question)
            st.write("Answer:", response)

    elif task == "Summarize":
        if st.button("Summarize Document"):
            response = process_document(combined_text, task="summarize")
            st.write("Summary:", response)
    
    elif task == "Combine":
        response = combined_text  # For Combine, response is simply the combined text
        st.write("Combined Document Content:")
        st.write(response)

    # Output format selection for download
    output_format = st.selectbox("Download as", ["PDF", "Word"])

    # Generate downloadable file based on response content
    if output_format == "PDF":
        pdf_bytes = BytesIO()
        pdf_doc = Document()
        pdf_doc.add_paragraph(response)
        pdf_doc.save(pdf_bytes)
        pdf_bytes.seek(0)
        st.download_button(label="Download PDF", data=pdf_bytes, file_name="output.pdf", mime="application/pdf")

    elif output_format == "Word":
        word_bytes = BytesIO()
        word_doc = Document()
        word_doc.add_paragraph(response)
        word_doc.save(word_bytes)
        word_bytes.seek(0)
        st.download_button(label="Download Word", data=word_bytes, file_name="output.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
