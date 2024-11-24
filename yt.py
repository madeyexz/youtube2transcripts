import argparse
import yt_dlp
import os
from tqdm import tqdm

def sanitize_filename(filename):
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename

def download_audio(url, output_path=None):
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
            'keepvideo': True,
            'progress_hooks': [lambda d: print(f"\rDownloading: {d['_percent_str']}", end='') if d['status'] == 'downloading' else None],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        return True
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Download YouTube video as audio')
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('-o', '--output', help='Output directory (optional)')
    
    args = parser.parse_args()
    download_audio(args.url, args.output)

if __name__ == "__main__":
    main()
