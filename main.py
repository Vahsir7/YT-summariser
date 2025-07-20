# main.py
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import google.generativeai as genai
import os
from fastapi.middleware.cors import CORSMiddleware 
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled 
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

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

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       
    allow_credentials=True,      
    allow_methods=["*"],         
    allow_headers=["*"],         
)
class VideoRequest(BaseModel):
    video_url: str
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Warning: GEMINI_API_KEY environment variable not set.")

genai.configure(api_key=API_KEY)

# Helper to extract YouTube video ID
def get_youtube_video_id(url: str) -> str | None:
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

    transcript_content = ""
    try: 
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_content = " ".join([entry['text'] for entry in transcript_list])

    except NoTranscriptFound:
        raise HTTPException(status_code=404, detail="No transcript available for this video (e.g., no captions, private video).")
    except TranscriptsDisabled:
        raise HTTPException(status_code=403, detail="Transcripts are disabled for this video.")
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch transcript: {str(e)}")

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""
            Analyze the following video content (transcript) and provide key insights,
            summarize the main points, and suggest potential discussion topics or related areas.
            Video Content: "{transcript_content}"
        """
        response = model.generate_content(prompt)

        if response.candidates and response.candidates[0].content.parts:
            insights = response.candidates[0].content.parts[0].text
            return {"video_id": video_id, "insights": insights}
        else:
            raise HTTPException(status_code=500, detail="Failed to generate insights from the LLM.")

    except Exception as e:
        print(f"Error generating insights: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while generating insights: {str(e)}")