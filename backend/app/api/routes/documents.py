from pathlib import Path
import shutil

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.deps import CurrentUser
from app.ingestion.run import PDFExtractionPipeline, collection_name

router = APIRouter()

UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

BACKEND_DIR = Path(__file__).resolve().parents[3]
PROJECT_ROOT = BACKEND_DIR.parent

RAW_DATA_FOLDER = PROJECT_ROOT / "data" / "raw"
RAW_DATA_FOLDER.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_document(
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    """
    Upload a PDF and automatically ingest it into the vector database.
    """

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    try:
        # Save uploaded file
        upload_path = UPLOAD_FOLDER / file.filename

        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Remove previously uploaded PDFs
        for pdf in RAW_DATA_FOLDER.glob("*.pdf"):
            try:
                pdf.unlink()
            except Exception:
                pass

        # Copy only the current PDF
        raw_path = RAW_DATA_FOLDER / file.filename
        shutil.copy2(upload_path, raw_path)

        # Run ingestion
        pipeline = PDFExtractionPipeline()
        pipeline.run(collection_name)

        return {
            "status": "success",
            "message": "Document uploaded and indexed successfully.",
            "filename": file.filename,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )