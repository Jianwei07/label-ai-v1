import shutil
import os
from fastapi import UploadFile

def save_upload_file(upload_file: UploadFile, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    file_path = os.path.join(dest_dir, upload_file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return file_path
