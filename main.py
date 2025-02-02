from fastapi import FastAPI, File, UploadFile, HTTPException
import openai
import pandas as pd
import io
import base64
from PIL import Image
import requests

app = FastAPI()

# Set your OpenAI API key here
openai.api_key = "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"

def audit_expenses_with_gpt4(csv_data: str, image_data: list) -> str:
    """
    Sends the CSV data and images to GPT-4 for auditing.
    """
    # Prepare the prompt for GPT-4
    prompt = (
        "You are a financial auditor. Below is a CSV file containing financing expenses and bills, "
        "along with images of the bills. Please audit the data and images, provide a score out of 10, "
        "and highlight any financial mistakes or discrepancies.\n\n"
        f"CSV Data:\n{csv_data}\n\n"
        "Images of Bills: (attached as base64 encoded images)\n"
    )

    # Add image data to the prompt (base64 encoded)
    for idx, img_base64 in enumerate(image_data):
        prompt += f"Image {idx + 1}: {img_base64[:100]}... (truncated)\n"

    # Send the prompt to GPT-4
    response = openai.ChatCompletion.create(
        model="gpt-4",  # Use GPT-4
        messages=[
            {"role": "system", "content": "You are a financial auditor."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1000,
    )

    return response.choices[0].message["content"].strip()

async def encode_image_to_base64(image: UploadFile) -> str:
    """
    Encodes an uploaded image file to base64.
    """
    image_bytes = await image.read()
    return base64.b64encode(image_bytes).decode("utf-8")

@app.post("/upload-audit/")
async def audit_expenses(
    csv_file: UploadFile = File(...),
    bill_images: list[UploadFile] = File(...),
):
    """
    Endpoint to upload a CSV file and images of bills for auditing.
    """
    # Validate file formats
    if not csv_file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid CSV file format.")

    for image in bill_images:
        if not image.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            raise HTTPException(
                status_code=400,
                detail="Invalid image format. Only PNG, JPG, and JPEG are allowed.",
            )

    # Read the CSV file
    csv_contents = await csv_file.read()
    df = pd.read_csv(io.StringIO(csv_contents.decode("utf-8")))
    csv_data = df.to_string(index=False)

    # Encode images to base64
    image_data = []
    for image in bill_images:
        image_data.append(await encode_image_to_base64(image))

    # Audit the expenses and bills using GPT-4
    audit_result = audit_expenses_with_gpt4(csv_data, image_data)

    return {"audit_result": audit_result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
