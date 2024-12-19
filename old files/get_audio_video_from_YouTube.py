import argparse
import yt_dlp
import os
import concurrent.futures
from tqdm import tqdm

def sanitize_filename(filename):
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename

def download_audio(url, output_path="./audio"):
    try:
        if not output_path:
            output_path = os.getcwd()
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            # 'keepvideo': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading: {url}")
            ydl.download([url])
            print(f"Completed: {url}")
            
        return True
        
    except Exception as e:
        print(f"An error occurred with {url}: {str(e)}")
        return False

def main():
    vid_lst = ["https://www.youtube.com/watch?v=tnBQmEqBCY0",
               "https://www.youtube.com/watch?v=sYMqVwsewSg",
               "https://www.youtube.com/watch?v=VAUt2j6juHU",
               "https://www.youtube.com/watch?v=YH1txRfa0oY",
               "https://www.youtube.com/watch?v=Om5XuTbXP1U",
               "https://www.youtube.com/watch?v=vVnDE8wSrVo",
               "https://www.youtube.com/watch?v=qszGzNoopTc",
               "https://www.youtube.com/watch?v=8JoTw_JuE78",
               "https://www.youtube.com/watch?v=7D4fhLlnftA"]
               

    # Use ThreadPoolExecutor for concurrent downloads
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all download tasks
        futures = [executor.submit(download_audio, url) for url in vid_lst]
        # Wait for all downloads to complete
        concurrent.futures.wait(futures)

if __name__ == "__main__":
    main()