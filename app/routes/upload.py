"""Image upload route."""
import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

router = APIRouter(prefix="/api", tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """Upload an image and return its public URL."""
    ext = Path(file.filename or "img.png").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        from fastapi import HTTPException
        raise HTTPException(400, f"不支持的文件格式: {ext}，支持 {', '.join(ALLOWED_EXTENSIONS)}")

    filename = f"{uuid.uuid4().hex[:12]}{ext}"
    filepath = UPLOAD_DIR / filename

    content = await file.read()
    filepath.write_bytes(content)

    return {"url": f"/uploads/{filename}", "filename": filename}
