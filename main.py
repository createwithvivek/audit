from fastapi import FastAPI, File, UploadFile, HTTPException
import pandas as pd
import io
import base64
import asyncio
from openai import OpenAI  # New import style from the latest OpenAI package

app = FastAPI()

# Instantiate the OpenAI client.
# For production, store your API key securely (e.g., in environment variables).
client = OpenAI(api_key="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")


def get_audit_completion(prompt: str) -> dict:
    """
    Synchronous helper function that calls the new OpenAI API interface.
    """
    return client.chat.completions.create(
        model="gpt-4o",  # Use the new model identifier if needed
        store=True,
        messages=[
            {"role": "system", "content": "You are a financial auditor."},
            {"role": "user", "content": prompt},
        ]
    )


async def audit_expenses_with_gpt4(csv_data: str, image_data: list[str]) -> str:
    """
    Constructs the prompt using the CSV data and image data (base64 encoded)
    and calls the OpenAI API asynchronously using a thread executor.
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

    # Run the synchronous API call in a thread to avoid blocking the event loop.
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(None, lambda: get_audit_completion(prompt))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

    return response["choices"][0]["message"]["content"].strip()


async def encode_image_to_base64(image: UploadFile) -> str:
    """
    Asynchronously reads an image and encodes it to a base64 string.
    """
    image_bytes = await image.read()
    return base64.b64encode(image_bytes).decode("utf-8")


@app.post("/upload-audit/")
async def audit_expenses(
    audit_csv: UploadFile = File(...),
    bills: list[UploadFile] = File([])  # Defaults to empty list if no images provided
):
    """
    Endpoint to upload a CSV file and optionally images (bills) for auditing.
    Field names:
      - audit_csv: CSV file
      - bills: image file(s)
    """
    # Validate CSV file
    if not audit_csv.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid CSV file format.")

    # Validate image file(s)
    for image in bills:
        if not image.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            raise HTTPException(
                status_code=400,
                detail="Invalid image format. Only PNG, JPG, and JPEG are allowed."
            )

    # Read and parse the CSV file
    csv_contents = await audit_csv.read()
    try:
        df = pd.read_csv(io.StringIO(csv_contents.decode("utf-8")))
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to parse CSV file.")
    csv_data = df.to_string(index=False)

    # Encode images to base64 (if any)
    image_data = []
    for image in bills:
        encoded = await encode_image_to_base64(image)
        image_data.append(encoded)

    # Audit the expenses using GPT-4 with the new API interface.
    audit_result = await audit_expenses_with_gpt4(csv_data, image_data)

    return {"audit_result": audit_result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
