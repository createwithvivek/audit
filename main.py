from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import openai
import asyncio
import pandas as pd
import io
import os

# Load OpenAI API key securely (DO NOT HARDCODE)
OPENAI_API_KEY = os.getenv("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")
if not OPENAI_API_KEY:
    raise RuntimeError("⚠️ OpenAI API Key is missing. Set it as an environment variable.")

openai.api_key = OPENAI_API_KEY

app = FastAPI()

# CORS settings
origins = [
    "https://analysisdata.netlify.app",
    "https://your-frontend-url.com",
    "http://localhost",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def analyze_audit(audit_csv: UploadFile, bills: list[UploadFile]):
    # Read CSV file asynchronously
    csv_contents = await audit_csv.read()
    try:
        df = pd.read_csv(io.BytesIO(csv_contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV file: {str(e)}")

    # Read bill files asynchronously
    bill_files = {}
    for bill in bills:
        bill_contents = await bill.read()
        bill_files[bill.filename] = bill_contents

    # Format CSV as text for OpenAI
    csv_text = df.to_string()

    # Construct GPT-4 prompt
    prompt = f"""
    You are a financial auditor. Your job is to verify transactions in the audit file against the provided bills.

    **Instructions:**
    - Verify each transaction in the CSV file with the provided bills.
    - Identify missing or inconsistent bills.
    - Detect fraud, fake invoices, or altered documents.
    - Cross-check transaction details.
    - Provide an **Audit Score (0-100%)** based on completeness and legitimacy.
    - Provide structured **point-to-point analysis**.

    **Audit Transactions (CSV Data):**
    {csv_text}

    **Bills Received:**
    {', '.join(bill_files.keys()) if bill_files else "No bills uploaded"}

    Return a structured JSON output with:
    - **Audit Score (0-100%)**
    - **Transactions with missing or inconsistent bills**
    - **Suspicious or fraudulent bills**
    - **Point-to-point analysis of inconsistencies**
    - **Final Recommendations**
    """

    # OpenAI Chat Completion (Corrected API Call)
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are an expert financial auditor."},
                  {"role": "user", "content": prompt}],
        max_tokens=2000,
    )

    # Extract response
    audit_result = response["choices"][0]["message"]["content"]
    return {"Audit Report": audit_result}

@app.get("/")
async def home():
    return {"message": "FastAPI is running successfully!"}

@app.post("/upload-audit/")
async def upload_audit(audit_csv: UploadFile = File(...), bills: list[UploadFile] = File([])):
    result = await analyze_audit(audit_csv, bills)
    return {"message": "Audit Completed", "Report": result}
