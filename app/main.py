from fastapi import FastAPI, UploadFile, File, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import zipfile, os, shutil, uuid # Added uuid for unique folder names
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
async def upload(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...), media_options: str = Form("text_only")):
    session_id = str(uuid.uuid4())
    session_upload_dir = UPLOAD_DIR / session_id
    session_upload_dir.mkdir(exist_ok=True)

    original_filename = file.filename
    # Sanitize filename to prevent directory traversal or other issues, though Path helps.
    # For simplicity, assuming filenames are generally safe for now.
    saved_filepath = session_upload_dir / original_filename

    try:
        with open(saved_filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        # Clean up session directory if file saving fails
        shutil.rmtree(session_upload_dir)
        return templates.TemplateResponse("result.html", {
            "request": request,
            "filename": original_filename,
            "analysis": {"error": f"Failed to save uploaded file: {e}"}
        })

    chat_txt_path = None
    media_folder_path = None

    if original_filename.endswith(".zip"):
        # extract_dir is now session_upload_dir where the zip is saved and extracted
        extract_dir = session_upload_dir 
        
        try:
            with zipfile.ZipFile(saved_filepath, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                # Find the _chat.txt file, assuming it's directly in the zip or a subfolder
                for member in zip_ref.namelist():
                    # Ensure member path is safe and within extract_dir
                    member_path = (extract_dir / Path(member)).resolve()
                    if extract_dir in member_path.parents or extract_dir == member_path.parent:
                        if member.endswith("_chat.txt") or (member.endswith(".txt") and not Path(member).name.startswith('.')):
                            chat_txt_path = member_path
                            break
            if chat_txt_path and chat_txt_path.exists():
                media_folder_path = extract_dir # The folder containing all media (which is the session_upload_dir)
            else:
                # If chat.txt not found after extraction
                shutil.rmtree(session_upload_dir)
                return templates.TemplateResponse("result.html", {
                    "request": request,
                    "filename": original_filename,
                    "analysis": {"error": "_chat.txt or .txt file not found within the ZIP."}
                })
        except zipfile.BadZipFile:
            shutil.rmtree(session_upload_dir)
            return templates.TemplateResponse("result.html", {
                "request": request,
                "filename": original_filename,
                "analysis": {"error": "Invalid or corrupted ZIP file."}
            })
        except Exception as e:
            shutil.rmtree(session_upload_dir)
            return templates.TemplateResponse("result.html", {
                "request": request,
                "filename": original_filename,
                "analysis": {"error": f"Error processing ZIP file: {e}"}
            })
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
        shutil.rmtree(session_upload_dir) # Clean up if chat file is missing after processing
        return templates.TemplateResponse("result.html", {
            "request": request,
            "filename": original_filename,
            "analysis": {"error": "Chat file (.txt) not found in the upload or ZIP."}
        })

    # MEDIA_PREVIEWS_DIR is already created at startup.
    # Pass it to analyze_chat for storing previews.
    result = analyze_chat(
        file_path=chat_txt_path, 
        media_options=media_options, 
        media_folder_path=str(media_folder_path) if media_folder_path else None,
        static_previews_dir=MEDIA_PREVIEWS_DIR
    )

    # Schedule cleanup of the session directory
    background_tasks.add_task(shutil.rmtree, session_upload_dir, ignore_errors=True)

    return templates.TemplateResponse("result.html", {
        "request": request,
        "filename": file.filename,
        "analysis": result
    })

# The /api/analyze endpoint is less relevant with the new UUID-based session folders 
# and background cleanup. If it's still needed, it would require significant rework
# to discover and process chats from potentially active (but soon to be deleted) session folders.
# For now, focusing on the primary /upload workflow.
# Consider removing or redesigning if this endpoint is critical.
@app.get("/api/analyze", response_class=JSONResponse)
async def api_analyze(media_options: str = "text_only"): 
    results = []
    # This endpoint's current logic of globbing UPLOAD_DIR is problematic with session folders.
    # It might pick up temporary files or miss context. 
    # For a robust API, it should probably accept a file ID or path directly.
    # Temporarily, let's make it return an empty list or a message indicating its deprecated status.
    # print("Warning: /api/analyze endpoint is not fully compatible with temporary session folders and may be deprecated.")
    return results
