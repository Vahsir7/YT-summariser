# main.py
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai
import os
import io
import markdown2
from xhtml2pdf import pisa
from fastapi.middleware.cors import CORSMiddleware 
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled 
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pytube import YouTube # <-- Make sure pytube is imported

app = FastAPI(
    title="YouTube Video Insights API",
    description="API to generate insights from YouTube video transcripts using Gemini LLM."
)

# --- Static Files and Templates ---
templates_directory = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_directory)
static_files_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_files_path), name="static")

# --- CORS Middleware ---
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,     
    allow_credentials=True,       
    allow_methods=["*"],         
    allow_headers=["*"],         
)

# --- Environment Variables and API Key ---
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Warning: GEMINI_API_KEY environment variable not set.")
else:
    genai.configure(api_key=API_KEY)

# --- Pydantic Models ---
class VideoRequest(BaseModel):
    video_url: str

class JsonData(BaseModel):
    title: str
    markdown_content: str # <-- This was 'content' in your JS, now it matches

# --- Helper Function ---
def get_youtube_video_id(url: str) -> str | None:
    import re
    regex = r"(?:https?:\/\/)?(?:www\.)?(?:m\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=|embed\/|v\/|)([\w-]{11})(?:\S+)?"
    match = re.search(regex, url)
    return match.group(1) if match else None

# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/get-insights")
async def get_video_insights(request: VideoRequest):
    video_url = request.video_url
    video_id = get_youtube_video_id(video_url)

    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube video URL provided.")

    # --- (NEW) Robustly fetch title with its own error handling ---
    try:
        yt = YouTube(video_url)
        video_title = yt.title
    except Exception as e:
        print(f"Could not fetch title with pytube: {e}")
        video_title = "YouTube Video" # Fallback title

    # --- Fetch Transcript using the reliable library ---
    try: 
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_content = " ".join([entry['text'] for entry in transcript_list])
    except NoTranscriptFound:
        raise HTTPException(status_code=404, detail="No transcript available for this video.")
    except TranscriptsDisabled:
        raise HTTPException(status_code=403, detail="Transcripts are disabled for this video.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch transcript: {str(e)}")

    # --- Generate Insights with Gemini ---
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
            Analyze the following video transcript and generate a concise, well-structured summary in Markdown format.
            Include a brief summary, key insights in a bulleted list, and a few discussion topics.
            Transcript: "{transcript_content}"
        """
        response = model.generate_content(prompt)
        insights = response.text
        
        # --- (NEW) Return the fetched title along with the insights ---
        return {"title": video_title, "insights": insights}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while generating insights: {str(e)}")
    
@app.post("/download-pdf")
async def create_pdf(data: JsonData):
    # --- (UPDATED) PDF generation now includes title and subheading ---
    main_content_html = markdown2.markdown(data.markdown_content)
    
    title_html = f"<h1>{data.title}</h1>"
    subheading_html = f"<h3 style='color: #555;'><i>App made by rishavbairagya@gmail.com</i></h3>"
    
    final_html = title_html + subheading_html + main_content_html

    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(final_html, dest=pdf_buffer)

    if pisa_status.err:
        return Response(f"Error generating PDF: {pisa_status.err}", status_code=500)

    pdf_buffer.seek(0)
    
    headers = {
        'Content-Disposition': f'attachment; filename="[summarized]{data.title}.pdf"'
    }
    return Response(content=pdf_buffer.getvalue(), media_type="application/pdf", headers=headers)