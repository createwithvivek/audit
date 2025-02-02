from fastapi import FastAPI, File, UploadFile, HTTPException
import pandas as pd
import io
import base64
import asyncio
import logging
from openai import OpenAI  # Using the new import style

# Set up logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Instantiate the OpenAI client with your API key.
client = OpenAI(api_key="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")


def get_audit_completion(prompt: str) -> dict:
    """
    Synchronous helper function that calls the new OpenAI API.
    """
    return client.chat.completions.create(
        model="gpt-4",  # Ensure this model is available in your account
        store=True,
        messages=[
            {"role": "system", "content": "You are a financial auditor."},
            {"role": "user", "content": prompt},
        ],
    )


async def audit_expenses_with_gpt4(csv_data: str, image_data: list[str]) -> str:
    """
    Constructs the prompt from CSV and image data, then calls the OpenAI API.
    Runs the synchronous API call in a thread using asyncio.to_thread.
    """
    prompt = (
        "You are a financial auditor. Below is a CSV file containing financing expenses and bills, "
        "along with images of the bills. Please audit the data and images, provide a score out of 10, "
        "and highlight any financial mistakes or discrepancies.\n\n"
        f"CSV Data:\n{csv_data}\n\n"
        "Images of Bills: (attached as base64 encoded images)\n"
    )
    for idx, img_base64 in enumerate(image_data):
        prompt += f"Image {idx + 1}: {img_base64[:100]}... (truncated)\n"

    try:
        # Run the synchronous API call in a separate thread.
        response = await asyncio.to_thread(get_audit_completion, prompt)
    except Exception as e:
        logging.error("Error during OpenAI API call: %s", e)
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

    logging.info("OpenAI API response: %s", response)

    try:
        # Adjust the extraction based on the new API response structure.
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error("Error parsing OpenAI API response: %s", e)
        raise HTTPException(status_code=500, detail="Failed to parse OpenAI API response.")


async def encode_image_to_base64(image: UploadFile) -> str:
    """
    Asynchronously reads an image file and encodes it to a base64 string.
    """
    image_bytes = await image.read()
    return base64.b64encode(image_bytes).decode("utf-8")


@app.post("/upload-audit/")
async def audit_expenses(
    audit_csv: UploadFile = File(...),
    bills: list[UploadFile] = File([])  # Defaults to an empty list if no images are provided
):
    """
    Endpoint to upload a CSV file and optionally image files (bills) for auditing.
    Field names:
      - audit_csv: CSV file
      - bills: image file(s)
    """
    # Validate CSV file format
    if not audit_csv.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid CSV file format.")

    # Validate image file formats
    for image in bills:
        if not image.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            raise HTTPException(
                status_code=400,
                detail="Invalid image format. Only PNG, JPG, and JPEG are allowed."
            )

    # Read and parse CSV file
    csv_contents = await audit_csv.read()
    try:
        df = pd.read_csv(io.StringIO(csv_contents.decode("utf-8")))
    except Exception as e:
        logging.error("Error parsing CSV file: %s", e)
        raise HTTPException(status_code=400, detail="Failed to parse CSV file.")
    csv_data = df.to_string(index=False)

    # Encode images to base64 (if any)
    image_data = []
    for image in bills:
        encoded = await encode_image_to_base64(image)
        image_data.append(encoded)

    # Call the OpenAI API via our helper
    audit_result = await audit_expenses_with_gpt4(csv_data, image_data)

    return {"audit_result": audit_result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
