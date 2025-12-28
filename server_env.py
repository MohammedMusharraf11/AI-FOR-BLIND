from fastapi import FastAPI
from pydantic import BaseModel
import base64
from google import genai
from PIL import Image
import io
from elevenlabs.client import ElevenLabs
import os
import time

# ---------------- CONFIG ---------------- #

# Get API keys from environment variables (fallback to hardcoded for local dev)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCsP7F7HJ0rs9SYdUrAYXmRWEgkQkxf0Lg")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "sk_fe56d80e1f8b1016f1e9bc760d68f914b72f115436fddd73")
VOICE_ID = os.getenv("VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel voice

# Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

# ElevenLabs Client
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

PROMPT = """
You are an assistive vision system for a visually impaired user.
Describe obstacles ahead in simple language.
Give safe navigation advice.
Limit response to 20 words.
"""

# ---------------- FASTAPI ---------------- #

app = FastAPI()

class AnalyzeRequest(BaseModel):
    image: str  # base64 image string

# ---------------- API ROUTES ---------------- #

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AI-FOR-BLIND Vision API",
        "timestamp": time.time()
    }

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    try:
        # ---- CLEAN BASE64 STRING ---- #
        image_data = req.image.strip()

        if image_data.startswith("data:"):
            image_data = image_data.split(",", 1)[1]

        image_data = "".join(image_data.split())

        # ---- DECODE IMAGE ---- #
        img_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        # ---- GEMINI VISION ---- #
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[PROMPT, image]
        )

        text = response.text.strip()

    except Exception as e:
        return {
            "error": str(e),
            "message": "Image processing or Gemini call failed"
        }

    # ---- TEXT TO SPEECH (ELEVENLABS) ---- #
    try:
        response = elevenlabs_client.text_to_speech.with_raw_response.convert(
            text=text,
            voice_id=VOICE_ID,
            model_id="eleven_turbo_v2_5"  # Fast, high-quality model
        )
        
        # Get audio data from response
        audio_bytes = response.content
        
        # Convert to base64
        audio_b64 = base64.b64encode(audio_bytes).decode()
        
        # Optional: Get usage info from headers
        char_count = response.headers.get("x-character-count", "N/A")
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "ElevenLabs TTS failed",
            "text": text  # Still return text even if TTS fails
        }

    return {
        "text": text,
        "audio": audio_b64,
        "char_count": char_count
    }

# ---------------- RUN ---------------- #
# uvicorn server:app --host 0.0.0.0 --port 8000
