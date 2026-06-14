from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import json
import logging
from app.core.database import db
from app.services.audio import AudioStreamProcessor
from app.services.screen import screen_service
from app.services.analytics import analytics_service
from app.services.ai import ai_orchestration
from app.services.rag import resume_rag

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions Pipeline"])

class SessionCreate(BaseModel):
    userId: str
    title: Optional[str] = "Interview Session"

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate):
    """
    Creates a new interview session record in PostgreSQL.
    """
    try:
        session_id = await db.fetch_row(
            "INSERT INTO sessions (id, user_id, title, created_at, updated_at) "
            "VALUES (gen_random_uuid(), $1, $2, NOW(), NOW()) RETURNING id",
            payload.userId, payload.title
        )
        return {"status": "created", "session_id": session_id["id"]}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create interview session: {e}"
        )

@router.get("", status_code=status.HTTP_200_OK)
async def list_sessions(userId: str):
    """
    Lists all sessions associated with a specific user.
    """
    try:
        rows = await db.fetch_rows(
            "SELECT id, title, transcript, created_at FROM sessions WHERE user_id = $1 ORDER BY created_at DESC",
            userId
        )
        return {"sessions": rows}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sessions: {e}"
        )

@router.delete("/{session_id}", status_code=status.HTTP_200_OK)
async def delete_session(session_id: str):
    """
    Deletes an interview session and automatically cascades delete down to nested questions/analytics.
    """
    try:
        await db.execute("DELETE FROM sessions WHERE id = $1", session_id)
        return {"status": "deleted", "session_id": session_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {e}"
        )

@router.post("/{session_id}/screen-capture", status_code=status.HTTP_200_OK)
async def process_screen_capture(session_id: str, file: UploadFile = File(...)):
    """
    Receives screen image uploads, processes with OCR/Gemini Vision, and yields dynamic contextual solutions.
    """
    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supported image formats are PNG and JPEG."
        )
        
    try:
        img_bytes = await file.read()
        
        # 1. OCR Visual parser
        ocr_result = await screen_service.analyze_screenshot(img_bytes)
        
        # 2. Persist screen question log if a problem is identified
        if ocr_result.get("detected_problem"):
            # Insert question
            question_id = await db.fetch_row(
                "INSERT INTO questions (id, session_id, category, confidence, question_text, timestamp) "
                "VALUES (gen_random_uuid(), $1, $2, $3, $4, NOW()) RETURNING id",
                session_id, "Technical", 1.0, ocr_result["detected_problem"]
            )
            
            # Insert suggestion response
            await db.execute(
                "INSERT INTO responses (id, question_id, ai_response, created_at) "
                "VALUES (gen_random_uuid(), $1, $2, NOW())",
                question_id["id"], ocr_result["suggested_solution"]
            )
            
        return {"status": "success", "analysis": ocr_result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Screen OCR analysis failed: {e}"
        )

@router.get("/{session_id}/analytics", status_code=status.HTTP_200_OK)
async def get_session_analytics(session_id: str):
    """
    Retrieves full speech analytics report, creating a new entry if not already processed.
    """
    try:
        # Check if analytics already exists
        analytics_row = await db.fetch_row(
            "SELECT * FROM analytics WHERE session_id = $1",
            session_id
        )
        
        if analytics_row:
            fw = analytics_row.get("filler_words_count")
            if isinstance(fw, str):
                try:
                    fw_parsed = json.loads(fw)
                except Exception:
                    fw_parsed = {}
            else:
                fw_parsed = fw or {}
            analytics_row["filler_words_count"] = fw_parsed
            analytics_row["fillerWordsCount"] = fw_parsed
            return {"analytics": analytics_row}
            
        # If not, generate fresh metrics from accumulated transcripts
        session_row = await db.fetch_row(
            "SELECT transcript FROM sessions WHERE id = $1",
            session_id
        )
        
        if not session_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview session not found."
            )
            
        report = analytics_service.analyze_transcript(session_row.get("transcript", ""))
        
        # Save metrics to database
        await db.execute(
            "INSERT INTO analytics (id, session_id, filler_words_count, speaking_pace, clarity_score, knowledge_gaps, suggestions, updated_at) "
            "VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, NOW())",
            session_id, json.dumps(report["filler_words_count"]), report["speaking_pace"], 
            report["clarity_score"], report["knowledge_gaps"], report["suggestions"]
        )
        
        return {"analytics": report}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analytics compilation pipeline encountered a database error: {e}"
        )

@router.websocket("/{session_id}/stream")
async def live_audio_stream(websocket: WebSocket, session_id: str, userId: str):
    """
    WebSocket endpoint establishing low-latency, real-time auditory PCM streaming pipes.
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for session: {session_id}")

    # Aggregated transcript to save on close
    session_transcript = []

    async def push_to_client(data: Dict[str, Any]):
        try:
            await websocket.send_json(data)
            # Accumulate final speech transcripts
            if data.get("type") == "TRANSCRIPT_CHUNK" and data.get("is_final"):
                session_transcript.append(data.get("text", ""))
        except Exception as e:
            logger.error(f"Error sending payload to client: {e}")

    # Initialize audio stream controller
    processor = AudioStreamProcessor(
        session_id=session_id,
        user_id=userId,
        send_callback=push_to_client
    )
    
    await processor.start()

    try:
        while True:
            # Client sends binary float/int PCM audio buffers
            data = await websocket.receive_bytes()
            await processor.receive_audio_chunk(data)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected gracefully for session {session_id}.")
    except Exception as e:
        logger.error(f"WebSocket error on audio stream: {e}")
    finally:
        await processor.stop()
        
        # Save accumulated transcripts to db on completion
        full_transcript_str = " ".join(session_transcript).strip()
        if full_transcript_str:
            try:
                await db.execute(
                    "UPDATE sessions SET transcript = $1, updated_at = NOW() WHERE id = $2",
                    full_transcript_str, session_id
                )
                logger.info(f"Successfully saved transcript log for completed session {session_id}.")
            except Exception as e:
                logger.error(f"Failed to save final transcript: {e}")
                
        try:
            await websocket.close()
        except Exception:
            pass
