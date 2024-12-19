import os
import logging
from tqdm import tqdm
import google.generativeai as genai
from dotenv import load_dotenv
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from ratelimit import limits, sleep_and_retry
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up logging with a cleaner format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants for rate limiting
CALLS_PER_SECOND = 1.8  # Slightly lower than 2 to add buffer
PERIOD = 1  # 1 second
MAX_WORKERS = 2  # Concurrent jobs limit

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

def process_single_file(file_path):
    global model
    file = None
    try:
        # Upload file
        file = upload_to_gemini_with_retry(file_path, mime_type="audio/mpeg")
        
        # Create chat session
        chat_session = model.start_chat(
            history=[
                {
                    "role": "user",
                    "parts": [
                        file,
                        "Generate audio diarization, including transcriptions and speaker information for each transcription. "
                        "Organize the transcription by the time they happened. No time stamps. "
                        "Infer speaker name from the audio. Text output only, no JSON formatting.",
                    ],
                }
            ]
        )

        # Process file
        response = process_file_with_retry(chat_session, file)

        # Save output
        output_filename = os.path.join("transcript_better", os.path.splitext(os.path.basename(file_path))[0] + '.md')
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        logger.info(f"✓ Completed: {os.path.basename(file_path)}")
        return file_path, True
    except Exception as e:
        logger.error(f"✗ Failed: {os.path.basename(file_path)} - {str(e)}")
        return file_path, False
    finally:
        if file is not None:
            try:
                if hasattr(file, 'cleanup'):
                    file.cleanup()
            except Exception as cleanup_error:
                logger.debug(f"Cleanup failed for {os.path.basename(file_path)}: {cleanup_error}")

def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables")
        return
        
    genai.configure(api_key=api_key)
    
    # Check transcript directory permissions
    transcript_dir = "transcript_better"
    try:
        os.makedirs(transcript_dir, exist_ok=True)
        # Test write permissions
        test_file = os.path.join(transcript_dir, ".test")
        with open(test_file, 'w') as f:
            f.write("")
        os.remove(test_file)
    except Exception as e:
        logger.error(f"Cannot write to transcript directory: {e}")
        return
    
    # Set up the model
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    global model
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )

    # Get all mp3 files
    audio_folder = "./audio"
    if not os.path.exists(audio_folder):
        logger.error(f"Audio folder '{audio_folder}' does not exist")
        return
        
    file_paths = [os.path.join(audio_folder, f) for f in os.listdir(audio_folder) if f.endswith('.mp3')]
    
    if not file_paths:
        logger.warning("No MP3 files found in the audio folder")
        return

    # Process files concurrently with rate limiting
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_single_file, file_path): file_path 
            for file_path in file_paths
        }
        
        # Add timeout to as_completed
        try:
            for future in tqdm(as_completed(future_to_file, timeout=300), 
                             total=len(file_paths), 
                             desc="Processing files"):
                file_path = future_to_file[future]
                try:
                    _, success = future.result(timeout=60)  # Add timeout for individual results
                    if success:
                        logger.info(f"Successfully processed {file_path}")
                    else:
                        logger.error(f"Failed to process {file_path}")
                except Exception as e:
                    logger.error(f"Exception processing {file_path}: {str(e)}")
        except TimeoutError:
            logger.error("Processing timed out")
            executor.shutdown(wait=False, cancel_futures=True)

if __name__ == "__main__":
    main()