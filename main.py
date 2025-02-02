from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import os
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load OpenAI API key securely from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("⚠️ OpenAI API Key is missing. Set it as an environment variable.")

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

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
    try:
        # Read CSV file
        csv_contents = await audit_csv.read()
        try:
            df = pd.read_csv(io.BytesIO(csv_contents))
        except Exception as e:
            logging.error(f"❌ Invalid CSV file: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid CSV file: {str(e)}")

        # Get filenames of uploaded bill images
        bill_filenames = [bill.filename for bill in bills] if bills else ["No bills uploaded"]

        # Format CSV as text for OpenAI
        csv_text = df.to_string()

        # Construct GPT-4o-mini prompt
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

        **Bill Images Provided:** {', '.join(bill_filenames)}

        Analyze the transactions based on the bill images and return a structured JSON output with:
        - **Audit Score (0-100%)**
        - **Transactions with missing or inconsistent bills**
        - **Suspicious or fraudulent bills**
        - **Point-to-point analysis of inconsistencies**
        - **Final Recommendations**
        """

        # Prepare API request
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are an expert financial auditor."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 2000
        }

        logging.info("📡 Sending request to OpenAI API...")
        
        # Send request to OpenAI API
        response = requests.post(OPENAI_API_URL, json=payload, headers=headers)

        # Log API response status
        logging.info(f"🔍 OpenAI API Response Status: {response.status_code}")

        # Check for API errors
        if response.status_code != 200:
            logging.error(f"❌ OpenAI API Error: {response.text}")
            raise HTTPException(status_code=500, detail=f"OpenAI API Error: {response.text}")

        data = response.json()
        logging.info("✅ Successfully received response from OpenAI API")

        # Extract response content
        try:
            audit_result = data["choices"][0]["message"]["content"]
            request_id = data.get("id", "N/A")  # Get request ID if available
        except (KeyError, IndexError):
            logging.error(f"❌ Unexpected OpenAI API Response: {data}")
            raise HTTPException(status_code=500, detail=f"Unexpected response from OpenAI API: {data}")

        return {
            "Audit Report": audit_result,
            "Request ID": request_id  # OpenAI Request ID for tracking
        }

    except Exception as e:
        logging.error(f"❌ Unexpected server error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {str(e)}")

@app.get("/")
async def home():
    return {"message": "FastAPI is running successfully!"}

@app.post("/upload-audit/")
async def upload_audit(audit_csv: UploadFile = File(...), bills: list[UploadFile] = File([])):
    result = await analyze_audit(audit_csv, bills)
    return {"message": "Audit Completed", "Report": result}
