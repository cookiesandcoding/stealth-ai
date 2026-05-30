import os
import json
import logging
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Google Generative AI
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not found in configuration. Operating in simulated offline mode.")

class AIOrchestrationService:
    def __init__(self):
        self.has_key = bool(settings.GEMINI_API_KEY)
        self.flash_model = "gemini-2.5-flash" if self.has_key else None
        self.pro_model = "gemini-2.5-pro" if self.has_key else None

    async def generate_bullet_suggestion(self, question: str, category: str, resume_context: Optional[str] = None, screen_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates low-latency answer suggestions using Gemini Flash.
        """
        system_instruction = (
            "You are an expert Interview Copilot. Your goal is to help the candidate with bulleted key talking points in real-time. "
            "Generate concise, high-impact bullet points and a light explanation. Keep bullet points to 1 sentence each, designed to be spoken naturally. "
            "Tailor the answer using the candidate's resume context and screen OCR context if provided. "
            "Return the output as a valid JSON object with keys: 'bullet_answer' (list of strings) and 'explanation' (string)."
        )
        
        prompt = f"Question Category: {category}\nQuestion: {question}\n"
        if resume_context:
            prompt += f"\nCandidate Resume Context:\n{resume_context}\n"
        if screen_context:
            prompt += f"\nScreen OCR/Visual Context:\n{screen_context}\n"
            
        if not self.has_key:
            return self._mock_bullet_suggestion(question, category)
            
        try:
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config={"response_mime_type": "application/json"},
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            data = json.loads(response.text)
            return {
                "bullet_answer": data.get("bullet_answer", []),
                "explanation": data.get("explanation", ""),
                "model_used": "gemini-2.5-flash"
            }
        except Exception as e:
            logger.error(f"Error calling Gemini API for low-latency suggestion: {e}")
            return self._mock_bullet_suggestion(question, category)

    async def generate_deep_explanation(self, question: str, category: str, resume_context: Optional[str] = None, screen_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates deep, reasoning-focused structural answers (STAR or design layout) using Gemini Pro.
        """
        system_instruction = (
            "You are an elite System Design and Behavioral Coach. Analyze the question and provide a comprehensive, fully detailed response. "
            "If category is 'Behavioral', construct the answer using a pristine STAR format (Situation, Task, Action, Result). "
            "If category is 'System Design', outline a world-class microservices/distributed architecture covering ingestion, compute, storage, caching, and scalability. "
            "If category is 'Technical', output clean, optimized code snippets with a time/space complexity analysis. "
            "Return a JSON object with keys: 'detailed_response' (markdown string) and 'follow_up_questions' (list of strings)."
        )
        
        prompt = f"Question Category: {category}\nQuestion: {question}\n"
        if resume_context:
            prompt += f"\nResume Details:\n{resume_context}\n"
        if screen_context:
            prompt += f"\nVisual Screen Context:\n{screen_context}\n"
            
        if not self.has_key:
            return self._mock_deep_response(question, category)
            
        try:
            model = genai.GenerativeModel(
                model_name="gemini-2.5-pro",
                generation_config={"response_mime_type": "application/json"},
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            data = json.loads(response.text)
            return {
                "detailed_response": data.get("detailed_response", ""),
                "follow_up_questions": data.get("follow_up_questions", []),
                "model_used": "gemini-2.5-pro"
            }
        except Exception as e:
            logger.error(f"Error calling Gemini API for deep explanation: {e}")
            return self._mock_deep_response(question, category)

    def _mock_bullet_suggestion(self, question: str, category: str) -> Dict[str, Any]:
        """
        Fallback simulation logic for rapid visual testing.
        """
        logger.info(f"Simulating fast Gemini Suggestion response for '{question}' ({category})")
        if "scaling" in question.lower() or "design" in question.lower() or "database" in question.lower():
            return {
                "bullet_answer": [
                    "Horizontal Scaling: Direct read-heavy traffic to PostgreSQL read replicas to relieve primary pressure.",
                    "Database Partitioning: Split massive transactional tables using range partitioning on created_at timestamp.",
                    "Distributed Caching: Layer Redis cluster above Postgres to store frequent, low-write metadata records.",
                    "Connection Optimization: Place PgBouncer connection pooler to prevent idle transaction overheads."
                ],
                "explanation": "Scaling high-throughput relational databases requires decoupling read traffic via replicas, partitioning tables to manage indices, and pooling idle threads.",
                "model_used": "gemini-2.5-flash (simulated)"
            }
        elif "conflict" in question.lower() or "disagreement" in question.lower() or "behavioral" in question.lower():
            return {
                "bullet_answer": [
                    "Active Listening: Focus on understanding their perspective rather than preparing counterarguments.",
                    "Data-Driven Alignment: Pivot disagreements onto empirical benchmarks, metrics, and user feedback.",
                    "Empathy & Calm: Acknowledge valid engineering tradeoffs without taking friction personally.",
                    "Collaborative Compromise: Leverage minor proof-of-concept tests to objectively settle architectural loops."
                ],
                "explanation": "Behavioral conflicts are best diffused by focusing on product success metrics and establishing rapid, objective sandbox spikes.",
                "model_used": "gemini-2.5-flash (simulated)"
            }
        else:
            return {
                "bullet_answer": [
                    "Identify Core Bottlenecks: Systematically isolate network latencies, memory profiling, and database queries.",
                    "Pragmatic Implementation: Implement standard optimizations and modularize the critical operational path.",
                    "Thorough Verification: Run high-load test coverage, sanity-checking standard edge cases.",
                    "Clear Articulation: Explain engineering tradeoffs clearly, showing structural command of the architecture."
                ],
                "explanation": "Ensure you structure your answers with strong problem discovery and articulate incremental refactoring designs.",
                "model_used": "gemini-2.5-flash (simulated)"
            }

    def _mock_deep_response(self, question: str, category: str) -> Dict[str, Any]:
        """
        Fallback simulation logic for detailed Gemini Pro responses.
        """
        logger.info(f"Simulating deep Gemini Pro response for '{question}' ({category})")
        if category == "Behavioral":
            detailed = (
                "### Situation:\n"
                "At my previous company, we noticed our real-time notification engine was lagging during peak hours, "
                "leading to user complaints about message delays of up to 45 seconds.\n\n"
                "### Task:\n"
                "I was tasked with diagnosing the throughput issue and restructuring the event brokers to support "
                "up to 5,000 requests per second under highly variable load.\n\n"
                "### Action:\n"
                "1. **Isolated Latency:** Verified that synchronous PostgreSQL write operations were blocking the primary thread.\n"
                "2. **Asynchronous Architecture:** Refactored the notification pipeline to push events to a **RabbitMQ** queue.\n"
                "3. **Worker Pooling:** Developed an asynchronous Python worker pool utilizing Celery to process jobs in parallel.\n"
                "4. **Backpressure Controls:** Configured rate-limiting policies at the broker level to gracefully queue spikes.\n\n"
                "### Result:\n"
                "Decreased message dispatch latency from **45 seconds to under 250 milliseconds**. Improved application "
                "throughput by **4.5x** and reduced direct database connection load by **60%**."
            )
            follow_up = ["How do you handle message delivery guarantees (at-least-once vs. exactly-once)?", "What caching layer did you use?"]
        elif category == "System Design":
            detailed = (
                "### Modern Real-time Data Platform Architecture\n\n"
                "#### 1. Ingestion Layer\n"
                "- **API Gateway:** Acts as the reverse proxy for SSL termination and rate-limiting using Token Bucket algorithms.\n"
                "- **Apache Kafka:** Multi-partition cluster capturing continuous JSON streams. Scaled horizontally across 3 availability zones.\n\n"
                "#### 2. Process & Compute Layer\n"
                "- **Apache Flink:** Performs streaming map-reduce calculations to deduplicate and aggregate metrics in a 5-second sliding window.\n"
                "- **Dockerized Microservices:** Highly-focused Node.js/Go backend pods autoscaled by Kubernetes HPA based on CPU/Memory usage.\n\n"
                "#### 3. Storage Layer\n"
                "- **TimescaleDB / PostgreSQL:** Stores high-fidelity logs with automatic hyper-table partitions.\n"
                "- **Qdrant / PGVector:** Manages high-dimensional semantic embeddings for contextual workspace searches.\n\n"
                "#### 4. Scalability & Resilience\n"
                "- **Decoupled Architecture:** Asynchronous queues absorb traffic spikes.\n"
                "- **Caching:** Multi-tier caching with local memory and distributed Redis pools reduces read latencies by 80%."
            )
            follow_up = ["How do you coordinate distributed transactions?", "What is your data retention and archiving policy?"]
        else:
            detailed = (
                "### Solution Architecture & Code Snippet\n\n"
                "Here is an optimized implementation of a Sliding Window Maximum algorithm in Python, using a `deque` to achieve $O(n)$ time complexity:\n\n"
                "```python\n"
                "from collections import deque\n\n"
                "def max_sliding_window(nums: list[int], k: int) -> list[int]:\n"
                "    \"\"\"\n"
                "    Time Complexity: O(n) as each element is pushed/popped at most twice.\n"
                "    Space Complexity: O(k) for the tracking deque queue.\n"
                "    \"\"\"\n"
                "    q = deque() # holds indices\n"
                "    result = []\n"
                "    \n"
                "    for i, num in enumerate(nums):\n"
                "        # Remove elements out of current window\n"
                "        if q and q[0] < i - k + 1:\n"
                "            q.popleft()\n"
                "        \n"
                "        # Remove smaller elements in current window\n"
                "        while q and nums[q[-1]] < num:\n"
                "            q.pop()\n"
                "            \n"
                "        q.append(i)\n"
                "        \n"
                "        # Window is fully formed\n"
                "        if i >= k - 1:\n"
                "            result.append(nums[q[0]])\n"
                "            \n"
                "    return result\n"
                "```\n\n"
                "#### Optimization Details:\n"
                "- By maintaining a monotonically decreasing structure within the sliding boundaries, we avoid $O(n \\times k)$ brute force lookup runs."
            )
            follow_up = ["Can you adapt this for streaming stream buffers?", "What happens if k exceeds array length?"]

        return {
            "detailed_response": detailed,
            "follow_up_questions": follow_up,
            "model_used": "gemini-2.5-pro (simulated)"
        }

ai_orchestration = AIOrchestrationService()
