from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import openai
import io

app = FastAPI()

# Set OpenAI API Key
openai.api_key = "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"

# CORS settings (Add your allowed origins here)
origins = [
    "https://da93a30c-86aa-42bd-af64-68a8b5ce16e5.lovableproject.c",  # Frontend URL
    "http://localhost",  # For local development
    "http://127.0.0.1:8000",  # Localhost address for FastAPI server
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow requests from these origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Function to analyze audit with ChatGPT
def analyze_audit(audit_csv: UploadFile, bills: list[UploadFile]):
    # Read CSV file as bytes
    csv_contents = audit_csv.file.read()

    # Read bill files as raw binary data
    bill_files = {bill.filename: bill.file.read() for bill in bills}

    # ChatGPT Prompt
    prompt = f"""
    You are a financial auditor. Your job is to verify transactions in the audit file against the provided bills.

    **Instructions:**
    - Verify each transaction in the CSV file with the provided bills.
    - Identify missing or inconsistent bills.
    - Detect fraud, fake invoices, or altered documents.
    - Cross-check transaction details.
    - Provide an **Audit Score (0-100%)** based on completeness and legitimacy.
    - Provide structured **point-to-point analysis**.

    **Audit Transactions (CSV File):** The raw CSV file is attached.
    **Bills (PDFs, Images, etc.):** The raw bill files are attached.

    Return a structured JSON output with:
    - **Audit Score (0-100%)**
    - **Transactions with missing or inconsistent bills**
    - **Suspicious or fraudulent bills**
    - **Point-to-point analysis of inconsistencies**
    - **Final Recommendations**
    """

    # Attach CSV and bill files
    files = {
        "audit_csv": ("audit.csv", csv_contents, "text/csv"),
    }
    for filename, content in bill_files.items():
        files[filename] = (filename, content, "application/octet-stream")

    # Send request to OpenAI ChatGPT API
    response = openai.ChatCompletion.create(
        model="gpt-4-vision-preview",  # Use the appropriate model
        messages=[{"role": "system", "content": prompt}],
        files=list(files.values()),  # Attach files
    )

    return response["choices"][0]["message"]["content"]

@app.get("/")
async def home():
    return {"message": "FastAPI is working!"}

@app.post("/upload-audit/")
async def upload_audit(audit_csv: UploadFile = File(...), bills: list[UploadFile] = File(...)):
    result = analyze_audit(audit_csv, bills)
    return {"message": "Audit Completed", "ChatGPT Report": result}
