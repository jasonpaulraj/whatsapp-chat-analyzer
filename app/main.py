from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import zipfile, os, shutil
from pathlib import Path

from utils import analyze_chat

app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
MEDIA_PREVIEWS_DIR = BASE_DIR / "static" / "media_previews"
UPLOAD_DIR.mkdir(exist_ok=True)
MEDIA_PREVIEWS_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile = File(...), media_options: str = Form("analyze_media")):
    original_filename = file.filename
    file_stem = Path(original_filename).stem
    saved_filepath = UPLOAD_DIR / original_filename

    with open(saved_filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    chat_txt_path = None
    media_folder_path = None

    if original_filename.endswith(".zip"):
        # Create a unique directory for this zip's contents
        extract_dir = UPLOAD_DIR / file_stem
        extract_dir.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(saved_filepath, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            # Find the _chat.txt file, assuming it's directly in the zip or a subfolder
            for member in zip_ref.namelist():
                if member.endswith("_chat.txt") or member.endswith(".txt"): # Handle both _chat.txt and general .txt
                    chat_txt_path = extract_dir / member
                    break
            if chat_txt_path and chat_txt_path.exists():
                media_folder_path = extract_dir # The folder containing all media
            else:
                # Fallback or error: if no chat.txt found in zip
                # For now, let's assume if a .txt is not found, we might try to find one in UPLOAD_DIR as a fallback
                # or handle as an error. For simplicity, we'll assume _chat.txt is present.
                # If not, analyze_chat will likely raise an error or return an error message.
                pass 
    elif original_filename.endswith(".txt"):
        chat_txt_path = saved_filepath
        # No separate media folder if it's just a .txt file, media would be ignored by parser or handled if paths are absolute

    if not chat_txt_path or not chat_txt_path.exists():
        # Handle error: chat file not found or not provided correctly
        return templates.TemplateResponse("result.html", {
            "request": request,
            "filename": original_filename,
            "analysis": {"error": "Chat file (.txt) not found in the upload."}
        })

    # MEDIA_PREVIEWS_DIR is already created at startup.
    # Pass it to analyze_chat for storing previews.
    result = analyze_chat(
        file_path=chat_txt_path, 
        media_options=media_options, 
        media_folder_path=str(media_folder_path) if media_folder_path else None,
        static_previews_dir=MEDIA_PREVIEWS_DIR
    )

    return templates.TemplateResponse("result.html", {
        "request": request,
        "filename": file.filename,
        "analysis": result
    })

@app.get("/api/analyze", response_class=JSONResponse)
async def api_analyze(media_options: str = "analyze_media"): # Added media_options for consistency, though not used by glob
    results = []
    # This API endpoint might need more thought if it's to support zip files and media from UPLOAD_DIR directly
    # For now, it will only process .txt files found directly in UPLOAD_DIR without specific media folders
    for file_path in UPLOAD_DIR.glob("*.txt"):
        # Assuming no specific media folder for these, or media is co-located / handled by paths in txt
        # Pass MEDIA_PREVIEWS_DIR for consistency, though it might not be used if no media_folder_path
        results.append(analyze_chat(file_path=file_path, media_options=media_options, media_folder_path=None, static_previews_dir=MEDIA_PREVIEWS_DIR))
    
    # If you want to analyze chats within extracted zip folders as well:
    # for potential_chat_dir in UPLOAD_DIR.iterdir():
    #     if potential_chat_dir.is_dir():
    #         # Try to find a _chat.txt or .txt file within this directory
    #         chat_files = list(potential_chat_dir.glob("*_chat.txt")) + list(potential_chat_dir.glob("*.txt"))
    #         if chat_files:
    #             # Assuming the first one found is the main chat file
    #             # The media_folder_path would be potential_chat_dir
    #             results.append(analyze_chat(str(chat_files[0]), media_options=media_options, media_folder_path=str(potential_chat_dir)))
    return results
