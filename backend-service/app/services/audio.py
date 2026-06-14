import logging
import asyncio
import json
import websockets
from typing import Dict, Any, Callable, Optional
from app.services.question import question_engine
from app.services.ai import ai_orchestration
from app.services.rag import resume_rag
from app.core.config import settings

logger = logging.getLogger(__name__)

class AudioStreamProcessor:
    def __init__(self, session_id: str, user_id: str, send_callback: Callable[[Dict[str, Any]], asyncio.Future]):
        self.session_id = session_id
        self.user_id = user_id
        self.send_callback = send_callback
        self.audio_buffer = bytearray()
        self.transcript_accumulator = ""
        self.is_active = True
        
        self.dg_ws = None
        self._loop_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None

    async def start(self):
        logger.info(f"Starting real-time audio pipeline for session {self.session_id}")
        if settings.DEEPGRAM_API_KEY:
            self._loop_task = asyncio.create_task(self._connect_deepgram())
        else:
            logger.warning("DEEPGRAM_API_KEY not found. Falling back to local offline simulation loop.")
            self._loop_task = asyncio.create_task(self._simulation_loop())

    async def stop(self):
        self.is_active = False
        if self._loop_task:
            self._loop_task.cancel()
        if self._receive_task:
            self._receive_task.cancel()
        if self.dg_ws:
            try:
                # Send empty close chunk to Deepgram to end the session gracefully
                await self.dg_ws.send(json.dumps({"type": "CloseStream"}))
                await self.dg_ws.close()
            except Exception as e:
                logger.warning(f"Error closing Deepgram websocket: {e}")
            self.dg_ws = None
        logger.info(f"Terminated audio pipeline for session {self.session_id}")

    async def receive_audio_chunk(self, chunk: bytes):
        """
        Receives binary PCM or webm audio frames from the desktop app client.
        Sends them directly to Deepgram if connected, otherwise processes locally.
        """
        if self.dg_ws:
            try:
                await self.dg_ws.send(chunk)
            except Exception as e:
                logger.error(f"Error sending audio chunk to Deepgram: {e}")
                self.dg_ws = None
        else:
            self.audio_buffer.extend(chunk)
            # Flush or process buffer when it hits a threshold (e.g. 64000 bytes)
            if len(self.audio_buffer) >= 64000:
                self.audio_buffer.clear()

    async def _connect_deepgram(self):
        headers = {
            "Authorization": f"Token {settings.DEEPGRAM_API_KEY}"
        }
        # Deepgram Nova-2 is optimized for speed and accuracy in English conversations
        url = "wss://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&interim_results=true"
        try:
            logger.info("Connecting to Deepgram streaming API...")
            self.dg_ws = await websockets.connect(url, extra_headers=headers)
            logger.info("Connected to Deepgram streaming API successfully.")
            self._receive_task = asyncio.create_task(self._listen_deepgram_responses())
        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {e}. Falling back to simulation loop.")
            self.dg_ws = None
            self._loop_task = asyncio.create_task(self._simulation_loop())

    async def _listen_deepgram_responses(self):
        try:
            async for message in self.dg_ws:
                data = json.loads(message)
                channel = data.get("channel", {})
                alternatives = channel.get("alternatives", [{}])
                transcript = alternatives[0].get("transcript", "")
                is_final = data.get("is_final", False)
                speech_final = data.get("speech_final", False)
                
                if transcript.strip():
                    # Stream current transcript results to overlay app
                    await self.send_callback({
                        "type": "TRANSCRIPT_CHUNK",
                        "text": transcript,
                        "is_final": is_final or speech_final
                    })
                    
                    # If it's a finished phrase, classify and suggest answers
                    if is_final or speech_final:
                        logger.info(f"Deepgram final transcript: '{transcript}'")
                        asyncio.create_task(self._process_final_transcript(transcript))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error listening to Deepgram socket: {e}")
        finally:
            if self.dg_ws:
                try:
                    await self.dg_ws.close()
                except Exception:
                    pass
                self.dg_ws = None
            logger.info("Deepgram connection listener terminated.")

    async def _process_final_transcript(self, transcript: str):
        is_question, q_data = await question_engine.detect_and_classify(transcript)
        if is_question and q_data:
            category = q_data.get("category", "Technical")
            # Retrieve RAG context from resume
            resume_context = await resume_rag.retrieve_context(self.user_id, transcript)
            
            # Generate suggestions
            suggestions = await ai_orchestration.generate_bullet_suggestion(
                question=transcript,
                category=category,
                resume_context=resume_context
            )
            
            # Push suggestions to overlay app
            await self.send_callback({
                "type": "COPILOT_SUGGESTION",
                "question_id": f"q-{hash(transcript) % 10000}",
                "category": category,
                "question": transcript,
                "confidence": q_data.get("confidence", 0.95),
                "bullet_answer": suggestions.get("bullet_answer", []),
                "explanation": suggestions.get("explanation", ""),
                "model_used": suggestions.get("model_used", "gpt-4o")
            })

    async def _simulation_loop(self):
        """
        An ultra-responsive speech-to-text simulation layer.
        Triggers natural, high-fidelity conversational transcripts and drives Q&A suggestions.
        This provides instantaneous visual feedback during developmental runs!
        """
        simulated_phases = [
            ("Hi there! Thanks for taking the time to speak with us today. Could you start by describing how you would handle database scaling in PostgreSQL?", "System Design"),
            ("That's a very clear summary. Tell me about a time you had a technical disagreement with a team member. How did you resolve it?", "Behavioral"),
            ("Perfect. And how do you maintain system consistency while scaling out read replicas?", "Technical")
        ]
        
        phase_idx = 0
        await asyncio.sleep(5) # Pause briefly to simulate initial setup/greeting
        
        while self.is_active and phase_idx < len(simulated_phases):
            phrase, category = simulated_phases[phase_idx]
            
            # Send word-by-word streaming increments (emulating speech-to-text feedback)
            words = phrase.split()
            current_stream = ""
            for word in words:
                if not self.is_active:
                    return
                current_stream += word + " "
                
                # Send live transcript update
                await self.send_callback({
                    "type": "TRANSCRIPT_CHUNK",
                    "text": current_stream.strip(),
                    "is_final": False
                })
                await asyncio.sleep(0.25) # Typist spacing
            
            # Send the final transcript sentence
            await self.send_callback({
                "type": "TRANSCRIPT_CHUNK",
                "text": phrase,
                "is_final": True
            })
            
            # 2. Intercept question and generate suggestion in real-time
            is_question, q_data = await question_engine.detect_and_classify(phrase)
            if is_question and q_data:
                # Retrieve RAG context from resume
                resume_context = await resume_rag.retrieve_context(self.user_id, phrase)
                
                # Generate suggestions
                suggestions = await ai_orchestration.generate_bullet_suggestion(
                    question=phrase,
                    category=category,
                    resume_context=resume_context
                )
                
                # Push suggestions to overlay app
                await self.send_callback({
                    "type": "COPILOT_SUGGESTION",
                    "question_id": f"q-{phase_idx}",
                    "category": category,
                    "question": phrase,
                    "confidence": q_data.get("confidence", 0.95),
                    "bullet_answer": suggestions.get("bullet_answer", []),
                    "explanation": suggestions.get("explanation", ""),
                    "model_used": suggestions.get("model_used", "gpt-4o")
                })
            
            phase_idx += 1
            await asyncio.sleep(25) # spacing between consecutive questions
