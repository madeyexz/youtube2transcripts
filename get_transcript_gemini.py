import os
import google.generativeai as genai

from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def upload_to_gemini(path, mime_type=None):
  """Uploads the given file to Gemini.

  See https://ai.google.dev/gemini-api/docs/prompting_with_media
  """
  file = genai.upload_file(path, mime_type=mime_type)
  print(f"Uploaded file '{file.display_name}' as: {file.uri}")
  return file

# Create the model
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
)

# TODO Make these files available on the local file system
# You may need to update the file paths
files = [
  upload_to_gemini("Vertical AI Agents Could Be 10X Bigger Than SaaS.mp3", mime_type="audio/mpeg"),
]

chat_session = model.start_chat(
  history=[
    {
      "role": "user",
      "parts": [
        files[0],
        "Generate audio diarization, including transcriptions and speaker information for each transcription. Organize the transcription by the time they happened. No time stamps. Infer speaker name from the audio. Text output only, no JSON formatting.",
      ],
    }
  ]
)

response = chat_session.send_message("INSERT_INPUT_HERE")

print(response.text)