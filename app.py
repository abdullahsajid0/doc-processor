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
        prompt_content = f"Answer based on the content provided:\n\nContent:\n{content}\n\nThe question is: {question}"
    else:
        prompt_content = f"Combine the following content without changing it and make sure no detail is missed while combining and the data should also be sorted:\n\n{content}"
    
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt_content}],
        model="llama-3.1-70b-versatile",
    )
    return chat_completion.choices[0].message.content

# Function to generate PDF using reportlab
def generate_pdf(response):
    pdf_bytes = BytesIO()
    c = canvas.Canvas(pdf_bytes, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "Generated Response")
    
    c.setFont("Helvetica", 12)
    text = c.beginText(72, height - 100)
    text.setFont("Helvetica", 12)
    text.setTextOrigin(72, height - 120)
    
    # Add the content from the response
    for line in response.split('\n'):
        text.textLine(line)
    
    c.drawText(text)
    c.showPage()
    c.save()

    pdf_bytes.seek(0)
    return pdf_bytes

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
    task = st.radio("Choose a task", ["Summarize", "Ask Questions", "Combine"])

    # Initialize response variable
    response = ""

        # Process based on selected task
    if task == "Ask Questions":
        # Example hint questions based on content
        hint_questions = {
            0: "What are the main points?",
            1: "Can you explain the key findings?",
            2: "What are the recommendations?"
        }

        # Use segmented control for hint selection
        selected_hint = st.segmented_control(
            "Choose a hint question:",
            options=hint_questions.keys(),
            format_func=lambda option: hint_questions[option]
        )
        
        # Prepopulate the question input box with the selected hint
        question = hint_questions[selected_hint]
        st.text_input("Enter your question here or select one below:", value=question)

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

    # Generate downloadable PDF
    pdf_bytes = generate_pdf(response)
    st.download_button(label="Download PDF", data=pdf_bytes, file_name="output.pdf", mime="application/pdf")
  
