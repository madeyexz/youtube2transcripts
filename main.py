from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import tempfile
from youtube_transcriber import process_youtube_url
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "https://*.vercel.app",  # Allow all Vercel preview deployments
        "https://youtube2transcripts.vercel.app"  # Replace with your actual domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TranscriptionRequest(BaseModel):
    url: str
    api_key: str

@app.post("/api/transcribe")
async def transcribe_video(request: TranscriptionRequest):
    try:
        os.environ["GEMINI_API_KEY"] = request.api_key
        
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["AUDIO_OUTPUT_DIR"] = temp_dir
            success, transcript_content = process_youtube_url(request.url)
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to process video")
            
            # Clean up audio files
            audio_dir = "/tmp/audio"
            if os.path.exists(audio_dir):
                for file in os.listdir(audio_dir):
                    file_path = os.path.join(audio_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        logger.error(f"Error deleting file {file_path}: {str(e)}")
            
            return JSONResponse({
                "status": "success",
                "message": "Video processed successfully",
                "transcript": transcript_content
            })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"} 