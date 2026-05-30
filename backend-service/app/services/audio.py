import logging
import asyncio
from typing import Dict, Any, Callable, Optional
from app.services.question import question_engine
from app.services.ai import ai_orchestration
from app.services.rag import resume_rag

logger = logging.getLogger(__name__)

class AudioStreamProcessor:
    def __init__(self, session_id: str, user_id: str, send_callback: Callable[[Dict[str, Any]], asyncio.Future]):
        self.session_id = session_id
        self.user_id = user_id
        self.send_callback = send_callback
        self.audio_buffer = bytearray()
        self.transcript_accumulator = ""
        self.is_active = True
        
        # Simple simulated timer to emulate speech increments during local workspace tests
        self._loop_task: Optional[asyncio.Task] = None

    async def start(self):
        logger.info(f"Starting real-time audio pipeline for session {self.session_id}")
        self._loop_task = asyncio.create_task(self._simulation_loop())

    async def stop(self):
        self.is_active = False
        if self._loop_task:
            self._loop_task.cancel()
        logger.info(f"Terminated audio pipeline for session {self.session_id}")

    async def receive_audio_chunk(self, chunk: bytes):
        """
        Receives binary 16-bit PCM audio frames from the desktop app client.
        In a production deploy, we pipe this stream directly to Deepgram/Whisper streaming sockets.
        """
        self.audio_buffer.extend(chunk)
        # Flush or process buffer when it hits a threshold (e.g. 32000 bytes = 1 sec of 16kHz audio)
        if len(self.audio_buffer) >= 64000:
            # logger.info(f"Processing 2-second audio frame buffer of size {len(self.audio_buffer)}")
            # Real STT API streaming goes here:
            # response = await deepgram_client.send(self.audio_buffer)
            self.audio_buffer.clear()

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
                    "model_used": suggestions.get("model_used", "gemini-2.5-flash")
                })
            
            phase_idx += 1
            await asyncio.sleep(25) # spacing between consecutive questions
