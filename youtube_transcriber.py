import os
import logging
from tqdm import tqdm
import google.generativeai as genai
from dotenv import load_dotenv
import yt_dlp
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential
from ratelimit import limits, sleep_and_retry
from pydub import AudioSegment

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
CALLS_PER_SECOND = 1.8  # Slightly lower than 2 to add buffer
PERIOD = 1  # 1 second
MAX_WORKERS = 2  # Concurrent jobs limit

def sanitize_filename(filename):
    # Enhanced sanitization
    invalid_chars = '<>:"/\\|?*![]()\'&,'  # Added more problematic chars
    for char in invalid_chars:
        filename = filename.replace(char, '')
    filename = filename.replace(' ', '_')  # Replace spaces with underscores
    return filename.strip()

def download_audio(url, output_path="./audio"):
    
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    # First get the info without downloading
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info['title']
        # Sanitize the filename before download
        sanitized_title = sanitize_filename(title)
        
        # Check if file already exists
        expected_filepath = os.path.join(output_path, f"{sanitized_title}.mp3")
        if os.path.exists(expected_filepath):
            logger.info(f"File already exists: {expected_filepath}")
            return expected_filepath, title
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        # Use pre-sanitized filename
        'outtmpl': os.path.join(output_path, sanitized_title + '.%(ext)s'),
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        logger.info(f"Downloading: {url}")
        ydl.download([url])
        filename = f"{sanitized_title}.mp3"
        filepath = os.path.join(output_path, filename)
        logger.info(f"Downloaded: {filename}")
        return filepath, title

@sleep_and_retry
@limits(calls=CALLS_PER_SECOND, period=PERIOD)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def upload_to_gemini_with_retry(path, mime_type=None):
    try:
        logger.debug(f"Starting upload for: {os.path.basename(path)}")
        genai.configure(
            api_key=os.getenv("GEMINI_API_KEY"),
            transport="rest"
        )
        file = genai.upload_file(path, mime_type=mime_type)
        logger.debug(f"Upload complete: {os.path.basename(path)}")
        return file
    except Exception as e:
        logger.error(f"Upload failed for {os.path.basename(path)}: {str(e)}")
        raise

@sleep_and_retry
@limits(calls=CALLS_PER_SECOND, period=PERIOD)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def process_file_with_retry(chat_session, file):
    try:
        logger.debug(f"Processing: {file.display_name}")
        response = chat_session.send_message(
            "Generate audio diarization, including transcriptions and speaker information for each transcription. "
            "Organize the transcription by the time they happened. No time stamps. "
            "Infer speaker name from the audio. Text output only, no JSON formatting."
        )
        return response
    except Exception as e:
        logger.error(f"Processing failed for {file.display_name}: {str(e)}")
        raise

def process_audio_file(audio_path, original_title=None):
    try:
        generation_config = {
            "temperature": 0.3,
            "top_p": 0.95,
            "top_k": 40,
            "response_mime_type": "text/plain",
        }

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
        )

        # Split audio into 20-minute chunks (to be safe)
        chunk_duration = 20 * 60  # 20 minutes in seconds
        chunks = split_audio(audio_path, chunk_duration)
        
        all_transcripts = []
        
        # Process each chunk
        for i, chunk_path in enumerate(chunks, 1):
            logger.info(f"Processing chunk {i}/{len(chunks)}")
            file = upload_to_gemini_with_retry(chunk_path, mime_type="audio/mpeg")
            
            chat_session = model.start_chat(
                history=[
                    {
                        "role": "user",
                        "parts": [
                            file,
                            "Generate audio diarization, including transcriptions and speaker information for each transcription. "
                            "Organize the transcription by the time they happened. No time stamps. "
                            "Infer speaker name from the audio. Text output only, no JSON formatting."
                            "New line between each speaker's transcript."
                            "If it's a single speaker, break it into paragraphs."
                            f"This is part {i} of {len(chunks)}."
                        ],
                    }
                ]
            )

            response = process_file_with_retry(chat_session, file)
            all_transcripts.append(response.text)
            
            # Clean up chunk file
            os.remove(chunk_path)

        # Combine all transcripts
        combined_transcript = "\n\n=== Part Break ===\n\n".join(all_transcripts)

        # Save combined transcript
        transcript_dir = "transcripts_better"
        os.makedirs(transcript_dir, exist_ok=True)
        
        if original_title:
            base_name = sanitize_filename(original_title)
        else:
            base_name = sanitize_filename(os.path.splitext(os.path.basename(audio_path))[0])
            
        transcript_path = os.path.join(transcript_dir, f"transcript_{base_name}.md")
        
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(combined_transcript)
            
        logger.info(f"✓ Transcript saved: {transcript_path}")
        return combined_transcript  # Return the transcript content
        
    except Exception as e:
        logger.error(f"Failed to process {audio_path}: {str(e)}")
        return None

def split_audio(audio_path, chunk_duration):
    """Split audio file into chunks of specified duration."""
    audio = AudioSegment.from_mp3(audio_path)
    duration_ms = len(audio)
    chunk_duration_ms = chunk_duration * 1000
    
    chunks = []
    for i in range(0, duration_ms, chunk_duration_ms):
        chunk = audio[i:i + chunk_duration_ms]
        chunk_path = f"{audio_path}_chunk_{i//chunk_duration_ms}.mp3"
        chunk.export(chunk_path, format="mp3")
        chunks.append(chunk_path)
    
    return chunks

def process_youtube_url(url):
    try:
        audio_path, original_title = download_audio(url)
        if not audio_path:
            logger.error(f"Failed to download audio for {url}")
            return False, None
            
        # Get transcript content
        transcript_content = process_audio_file(audio_path, original_title)
        
        # Clean up the original audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"Cleaned up audio file: {audio_path}")
            
        return True, transcript_content
        
    except Exception as e:
        logger.error(f"Error processing {url}: {str(e)}")
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.remove(audio_path)
        return False, None

def main():
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables")
        return

    genai.configure(api_key=api_key)
    
    # Get YouTube URLs from user
    print("Enter YouTube URLs (one per line). Press Enter twice when done:")
    urls = []
    while True:
        url = input().strip()
        if not url:
            break
        urls.append(url)
    
    if not urls:
        logger.error("No URLs provided")
        return
        
    # Process URLs concurrently with rate limiting
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_url = {
            executor.submit(process_youtube_url, url): url 
            for url in urls
        }
        
        # Process results with progress bar
        try:
            for future in tqdm(as_completed(future_to_url, timeout=300), 
                             total=len(urls), 
                             desc="Processing URLs"):
                url = future_to_url[future]
                try:
                    success, transcript_content = future.result(timeout=60)
                    if success:
                        logger.info(f"Successfully processed: {url}")
                    else:
                        logger.error(f"Failed to process: {url}")
                except Exception as e:
                    logger.error(f"Exception processing {url}: {str(e)}")
        except TimeoutError:
            logger.error("Processing timed out")
            executor.shutdown(wait=False, cancel_futures=True)

if __name__ == "__main__":
    main() 