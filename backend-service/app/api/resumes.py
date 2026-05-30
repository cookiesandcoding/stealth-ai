from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from app.services.rag import resume_rag
from app.core.database import db

router = APIRouter(prefix="/resumes", tags=["Resumes RAG"])

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    userId: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Ingests and embeds PDF resume layouts into the Qdrant vector database.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF resume documents are supported."
        )
        
    try:
        # Read raw PDF file bytes
        file_bytes = await file.read()
        
        # 1. Chunk and index chunks inside Qdrant/memory vector store
        ingest_result = await resume_rag.ingest_resume(
            user_id=userId,
            file_name=file.filename,
            file_bytes=file_bytes
        )
        
        # 2. Write metadata record inside PostgreSQL DB
        await db.execute(
            "INSERT INTO resumes (id, user_id, file_name, file_url, parsed_text, created_at) "
            "VALUES (gen_random_uuid(), $1, $2, $3, $4, NOW())",
            userId, file.filename, f"uploads/{file.filename}", ingest_result["parsed_text_preview"]
        )
        
        return {
            "status": "success",
            "message": "Resume successfully indexed for semantic RAG queries.",
            "data": ingest_result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume indexing pipeline failed: {e}"
        )
