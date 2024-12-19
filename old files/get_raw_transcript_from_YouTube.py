import argparse
import os
import asyncio
import logging
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import yt_dlp
from tqdm import tqdm
import aiohttp
import concurrent.futures

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_video_id(url):
    """Extract video ID from YouTube URL"""
    parsed_url = urlparse(url)
    if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        return parse_qs(parsed_url.query)['v'][0]
    elif parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    else:
        raise ValueError("Not a valid YouTube URL")

async def get_video_title(url, session):
    """Get video title using yt-dlp"""
    # Run yt-dlp in a thread pool since it's blocking
    loop = asyncio.get_running_loop()
    with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
        info = await loop.run_in_executor(None, 
            lambda: ydl.extract_info(url, download=False))
        return info.get('title', 'Untitled')

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename

async def get_transcript(url):
    """Get transcript from YouTube video"""
    # Run YouTubeTranscriptApi in a thread pool since it's blocking
    loop = asyncio.get_running_loop()
    try:
        video_id = get_video_id(url)
        transcript_list = await loop.run_in_executor(None,
            lambda: YouTubeTranscriptApi.list_transcripts(video_id))
        
        try:
            transcript = await loop.run_in_executor(None,
                lambda: transcript_list.find_manually_created_transcript())
        except:
            transcript = await loop.run_in_executor(None,
                lambda: transcript_list.find_generated_transcript(['en']))
        
        return await loop.run_in_executor(None, transcript.fetch)
    except Exception as e:
        logger.error(f"Error getting transcript for {url}: {str(e)}")
        return None

async def save_transcript(transcript, title, output_dir="transcripts"):
    """Save transcript to markdown file"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created output directory: {output_dir}")
        
    filename = sanitize_filename(title)
    filepath = os.path.join(output_dir, f"{filename}.md")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        for entry in tqdm(transcript, desc=f"Writing transcript for {title}", unit="lines"):
            f.write(f"{entry['text']}\n")
    logger.info(f"Saved transcript to: {filepath}")

async def process_url(url, output_dir, session):
    """Process a single URL asynchronously"""
    try:
        title = await get_video_title(url, session)
        logger.info(f"Processing: {title}")
        
        transcript = await get_transcript(url)
        if transcript:
            await save_transcript(transcript, title, output_dir)
        else:
            logger.warning(f"Could not get transcript for: {title}")
            
    except Exception as e:
        logger.error(f"Error processing {url}: {str(e)}")

async def main_async():
    parser = argparse.ArgumentParser(description='Download YouTube transcripts')
    parser.add_argument('urls', nargs='+', help='YouTube video URLs')
    parser.add_argument('-o', '--output', default='transcripts',
                      help='Output directory (default: transcripts)')
    
    args = parser.parse_args()
    
    async with aiohttp.ClientSession() as session:
        tasks = [process_url(url, args.output, session) for url in args.urls]
        await asyncio.gather(*tasks)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
