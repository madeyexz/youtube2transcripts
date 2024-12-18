# YouTube Audio Transcriber

A Python tool that downloads YouTube videos as audio and generates detailed transcriptions using Google's Gemini AI. The tool supports batch processing of multiple URLs and includes speaker diarization.

## Features

- Downloads YouTube videos as MP3 audio files
- Splits long audio files into manageable chunks
- Generates detailed transcriptions with speaker identification
- Supports batch processing of multiple URLs
- Includes rate limiting and retry mechanisms
- Progress tracking with tqdm
- Concurrent processing with ThreadPoolExecutor

## Prerequisites

- Python 3.8+
- Google Gemini API key
- FFmpeg (for audio processing)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/youtube-transcriber.git
cd youtube-transcriber
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your Gemini API key:
```
GEMINI_API_KEY=your_api_key_here
```

## Usage

Run the script:
```bash
python youtube_transcriber.py
```

When prompted, enter YouTube URLs one per line. Press Enter twice when done:
```
https://youtube.com/watch?v=example1
https://youtube.com/watch?v=example2
[Press Enter twice to start processing]
```

The script will:
1. Download audio from each URL
2. Split audio into 20-minute chunks
3. Process each chunk through Gemini AI
4. Generate and save transcripts in the `transcripts_better` directory

## Output

Transcripts are saved as markdown files in the `transcripts_better` directory with the following naming convention:
```
transcript_[sanitized_video_title].md
```

## Configuration

Key constants that can be modified in the script:
- `CALLS_PER_SECOND`: API rate limit (default: 1.8)
- `MAX_WORKERS`: Maximum concurrent jobs (default: 2)
- `chunk_duration`: Audio chunk size in minutes (default: 20)

## Error Handling

The script includes:
- Automatic retries for failed API calls
- Rate limiting to prevent API throttling
- Comprehensive logging
- File existence checks to prevent duplicate downloads

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube download functionality
- [Google Gemini AI](https://ai.google.dev/) for transcription services
- [pydub](https://github.com/jiaaro/pydub) for audio processing

## Disclaimer

This tool is for educational purposes only. Please ensure you have the right to download and process any YouTube content before using this tool.
