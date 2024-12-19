from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import tempfile
from youtube_transcriber import process_youtube_url

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
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
        # Set the API key from the request
        os.environ["GEMINI_API_KEY"] = request.api_key
        
        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["AUDIO_OUTPUT_DIR"] = temp_dir
            success = process_youtube_url(request.url)
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to process video")
            
            return JSONResponse({"status": "success", "message": "Video processed successfully"})
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"} 