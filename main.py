from fastapi import FastAPI, File, UploadFile # type: ignore
import openai # type: ignore
import io

app = FastAPI()

# Set OpenAI API Key
openai.api_key = "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"

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
        model="gpt-4-vision-preview",
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
    return result
