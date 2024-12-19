import streamlit as st
import os
import re
import pandas as pd
from PyPDF2 import PdfReader
from groq import Groq
import tempfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

st.set_page_config(page_title="ATS Resume Scanner")

# Initialize session state for storing results
if 'results' not in st.session_state:
    st.session_state.results = []

# Styling
st.markdown("""
    <style>
    .stTextArea textarea {
        height: 200px !important;
    }
    .main {
        padding: 2rem;
    }
    .stDataFrame {
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# Title and description
st.title("🕵🏻Application Tracking System")
st.markdown("Upload resumes and compare them against a job description.")


# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    try:
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"


# Function to get match score using Groq
def get_match_score(jd, resume_text, model="llama3-8b-8192"):
    prompt = f"""
    Job Description: {jd}
    Resume: {resume_text}

    Please provide only a match score (0-100) between the job description and resume.
    Return only the number, no additional text.
    """
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
        )
        score_text = response.choices[0].message.content
        # Extract number from response
        score_match = re.search(r'\d+', score_text)
        if score_match:
            return int(score_match.group())
        return 0
    except Exception as e:
        st.error(f"Error with Groq API: {str(e)}")
        return 0


# Job Description input
jd = st.text_area("Enter Job Description", height=200)

# File uploader
uploaded_files = st.file_uploader(
    "Upload Resumes (PDF)",
    type=['pdf'],
    accept_multiple_files=True
)

# Process button
if st.button("Process Resumes") and jd and uploaded_files:
    if not GROQ_API_KEY:
        st.error("GROQ API key not found in environment variables. Please check your .env file.")
    else:
        results = []
        progress_bar = st.progress(0)

        for index, file in enumerate(uploaded_files):
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(file.getvalue())
                tmp_file_path = tmp_file.name

            # Extract text and get match score
            resume_text = extract_text_from_pdf(tmp_file_path)
            match_score = get_match_score(jd, resume_text)

            # Store results
            results.append({
                "Resume": file.name,
                "Match Score": f"{match_score}%"
            })

            # Update progress
            progress_bar.progress((index + 1) / len(uploaded_files))

            # Clean up temporary file
            os.unlink(tmp_file_path)

        # Store results in session state
        st.session_state.results = results

# Display results
if st.session_state.results:
    st.subheader("Results")

    # Convert results to DataFrame
    df = pd.DataFrame(st.session_state.results)

    # Sort by match score (converting percentage string to number for sorting)
    df['Sort Score'] = df['Match Score'].str.rstrip('%').astype(int)
    df = df.sort_values('Sort Score', ascending=False)
    df = df.drop('Sort Score', axis=1)

    # Display as table
    st.dataframe(
        df,
        hide_index=True,
        column_config={
            "Resume": st.column_config.Column(
                "Resume Name",
                width="medium"
            ),
            "Match Score": st.column_config.Column(
                "Match Score",
                width="small"
            )
        }
    )

    # Download button for CSV
    csv = df.to_csv(index=False)
    st.download_button(
        "Download Results as CSV",
        csv,
        "ats_results.csv",
        "text/csv",
        key='download-csv'
    )

# Footer
st.markdown("---")
st.markdown("ATS Resume Scanner - Made With ❤️")