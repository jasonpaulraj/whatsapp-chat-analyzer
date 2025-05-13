from fastapi import FastAPI, UploadFile, File, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import zipfile
import os
import shutil
import uuid  # Added uuid for unique folder names
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
    # Clean up uploads and media previews directories
    for item in UPLOAD_DIR.iterdir():
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            item.unlink(missing_ok=True)

    for item in MEDIA_PREVIEWS_DIR.iterdir():
        if item.is_dir():  # Only remove session-specific subdirectories
            shutil.rmtree(item, ignore_errors=True)
        # Optionally, handle individual files directly in MEDIA_PREVIEWS_DIR if any are expected
        # else:
        #     item.unlink(missing_ok=True)

    # Ensure the base directories exist after cleanup (though they should not be deleted by rmtree on their contents)
    UPLOAD_DIR.mkdir(exist_ok=True)
    MEDIA_PREVIEWS_DIR.mkdir(exist_ok=True)
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
                # The folder containing all media (which is the session_upload_dir)
                media_folder_path = extract_dir
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
            # else:
            #     # Fallback or error: if no chat.txt found in zip
            #     # For now, let's assume if a .txt is not found, we might try to find one in UPLOAD_DIR as a fallback
            #     # or handle as an error. For simplicity, we'll assume _chat.txt is present.
            #     # If not, analyze_chat will likely raise an error or return an error message.
            #     pass
    elif original_filename.endswith(".txt"):
        chat_txt_path = saved_filepath
        # No separate media folder if it's just a .txt file, media would be ignored by parser or handled if paths are absolute

    if not chat_txt_path or not chat_txt_path.exists():
        # Clean up if chat file is missing after processing
        shutil.rmtree(session_upload_dir)
        return templates.TemplateResponse("result.html", {
            "request": request,
            "filename": original_filename,
            "analysis": {"error": "Chat file (.txt) not found in the upload or ZIP."}
        })

    # MEDIA_PREVIEWS_DIR is already created at startup.
    # Pass it to analyze_chat for storing previews.
    session_media_previews_dir = MEDIA_PREVIEWS_DIR / session_id
    session_media_previews_dir.mkdir(exist_ok=True)
    result = analyze_chat(
        file_path=chat_txt_path,
        media_options=media_options,
        media_folder_path=str(
            media_folder_path) if media_folder_path else None,
        static_previews_dir=session_media_previews_dir,
        session_id=session_id  # Pass session_id
    )

    # Schedule cleanup of the session directory
    background_tasks.add_task(
        shutil.rmtree, session_upload_dir, ignore_errors=True)

    return templates.TemplateResponse("result.html", {
        "request": request,
        "filename": file.filename,
        "analysis": result
    })
