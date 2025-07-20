# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
from fastapi.middleware.cors import CORSMiddleware # Added for CORS
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled # Added for transcript fetching
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Initialize FastAPI app
app = FastAPI(
    title="YouTube Video Insights API",
    description="API to generate insights from YouTube video transcripts using Gemini LLM."
)

templates_directory = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_directory)
static_files_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_files_path), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


origins = [
    "http://localhost",
    "http://localhost:8000",  # Your FastAPI app's common local origin
    "http://127.0.0.1:8000",  # Another common local origin for FastAPI
    "http://127.0.0.1:8002",  # Added: Explicitly allow the new API port 8002
    "http://localhost:5500",  # Common port for Live Server in VS Code or Python's http.server
    "null",                   # Some browsers send 'null' as origin for file://
    "file://",                # Explicitly allow file:// protocol (less secure, but helps for direct file opening)
    "http://127.0.0.1:5500",   # Explicitly allow the frontend's origin
    "https://yt-transcript-summariser.onrender.com/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # List of allowed origins
    allow_credentials=True,      # Allow cookies to be included in cross-origin requests
    allow_methods=["*"],         # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],         # Allow all headers
)
# --- End CORS Configuration ---


# Pydantic model for request body validation
class VideoRequest(BaseModel):
    video_url: str

# Configure the Google Generative AI client
# IMPORTANT: In a production environment, NEVER hardcode your API key directly.
# Always load it from environment variables or a secure configuration management system.
# For this Canvas environment, the API key for 'gemini-2.0-flash' is automatically
# provided by the runtime when the fetch call is made to generativelanguage.googleapis.com.
# If running locally, set an environment variable like:
#export GEMINI_API_KEY="AIzaSyDUSSdmReWXe3_ObTmArXWMYi_R6-T-u4k" (replace with your actual key)
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Warning: GEMINI_API_KEY environment variable not set. This might be fine in Canvas, but required for local execution.")

genai.configure(api_key=API_KEY)




# Function to extract YouTube video ID (not strictly needed for simulated transcript, but good practice)
def get_youtube_video_id(url: str) -> str | None:
    """Extracts the YouTube video ID from a given URL."""
    import re
    regex = r"(?:https?:\/\/)?(?:www\.)?(?:m\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=|embed\/|v\/|)([\w-]{11})(?:\S+)?"
    match = re.search(regex, url)
    return match.group(1) if match else None

@app.post("/get-insights")
async def get_video_insights(request: VideoRequest):
    """
    Generates insights for a given YouTube video URL.
    Fetches the actual transcript from YouTube.
    """
    video_url = request.video_url
    video_id = get_youtube_video_id(video_url)

    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube video URL provided.")

    # --- Fetching Actual Transcript ---
    transcript_content = ""
    try:
        # Get the transcript for the video
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        # Join the text parts to form a single string
        transcript_content = " ".join([entry['text'] for entry in transcript_list])
    except NoTranscriptFound:
        raise HTTPException(status_code=404, detail="No transcript available for this video (e.g., no captions, private video).")
    except TranscriptsDisabled:
        raise HTTPException(status_code=403, detail="Transcripts are disabled for this video.")
    except Exception as e:
        # Catch any other potential errors during transcript fetching
        print(f"Error fetching transcript: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch transcript: {str(e)}")

    if not transcript_content:
        raise HTTPException(status_code=404, detail="Transcript was fetched but is empty.")

    try:
        # Initialize the Generative Model
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Generate content using the fetched transcript
        prompt = f"""
            Analyze the following video content (transcript) and provide key insights,
            summarize the main points, and suggest potential discussion topics or related areas.
            Video Content: "{transcript_content}"
        """
        response = model.generate_content(prompt)

        # Extract the generated text
        if response.candidates and response.candidates[0].content.parts:
            insights = response.candidates[0].content.parts[0].text
            return {"video_id": video_id, "insights": insights}
        else:
            raise HTTPException(status_code=500, detail="Failed to generate insights from the LLM.")

    except Exception as e:
        print(f"Error generating insights: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while generating insights: {str(e)}")
