from fastapi import FastAPI
from pydantic import BaseModel
import base64
from google import genai
from PIL import Image
import io
import subprocess
import tempfile
import os
import time
from dotenv import load_dotenv

load_dotenv()

# ---------------- CONFIG ---------------- #

# Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPT = """
You are an assistive vision system for a visually impaired user.
Describe obstacles ahead in simple language.
Give safe navigation advice.
IMPORTANT: Limit response to 20 words only.
"""

# ---------------- FASTAPI ---------------- #

app = FastAPI()

class AnalyzeRequest(BaseModel):
    image: str  # base64 image string

# ---------------- ROUTES ---------------- #

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AI-FOR-BLIND Vision API",
        "timestamp": time.time()
    }

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    # ---------- IMAGE + GEMINI ----------
    try:
        image_data = req.image.strip()

        if image_data.startswith("data:"):
            image_data = image_data.split(",", 1)[1]

        image_data = "".join(image_data.split())

        img_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

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

    # ---------- ESPEAK-NG → PCM ----------
    wav_path = None
    pcm_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
            wav_path = wav_file.name

        with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as pcm_file:
            pcm_path = pcm_file.name

        # Generate WAV using espeak-ng
        subprocess.run(
            ["espeak-ng", "-v", "en-us", "-s", "150", "-w", wav_path, text],
            check=True
        )

        # Convert WAV → raw PCM (16-bit, 16kHz, mono)
        subprocess.run(
            ["sox", wav_path, "-t", "raw", "-r", "16000", "-b", "16", "-c", "1", pcm_path],
            check=True
        )

        with open(pcm_path, "rb") as f:
            audio_bytes = f.read()

        audio_b64 = base64.b64encode(audio_bytes).decode()

    except Exception as e:
        return {
            "error": str(e),
            "message": "espeak-ng TTS failed",
            "text": text
        }

    finally:
        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)
        if pcm_path and os.path.exists(pcm_path):
            os.remove(pcm_path)

    return {
        "text": text,
        "audio": audio_b64,
        "char_count": len(text)
    }

# ---------------- RUN ---------------- #
# uvicorn server:app --host 0.0.0.0 --port 8000
