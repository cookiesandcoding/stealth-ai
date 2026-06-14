import re
import logging
from typing import Dict, Any, Tuple, Optional
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

class QuestionDetectionEngine:
    def __init__(self):
        self.has_key = bool(settings.GEMINI_API_KEY)
        # Question indicator keywords
        self.question_indicators = [
            "how do you", "tell me about", "what is", "why would you", 
            "can you explain", "describe a time", "what are the", "how would you design",
            "could you explain", "what's the difference"
        ]

    def _quick_check_is_question(self, text: str) -> bool:
        """
        Fast heuristic check to filter non-questions before expensive semantic classification.
        """
        cleaned = text.strip().lower()
        if not cleaned:
            return False
        # Ends with a question mark
        if cleaned.endswith("?"):
            return True
        # Starts with or contains question indicators
        for ind in self.question_indicators:
            if ind in cleaned:
                return True
        return False

    async def detect_and_classify(self, text: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Checks if text is a question. If yes, classifies into categories:
        Technical, Behavioral, HR, System Design, Product with a confidence score.
        """
        if not self._quick_check_is_question(text):
            return False, None

        logger.info(f"Question detected by heuristics: '{text}'")

        if self.has_key:
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = (
                    "You are an interview question classifier. Categorize this interview question. "
                    "Allowed categories: 'Technical', 'Behavioral', 'HR', 'System Design', 'Product'. "
                    "Provide a valid JSON response with keys: 'category' (string) and 'confidence' (float between 0.0 and 1.0). "
                    f"Question: \"{text}\""
                )
                response = model.generate_content(prompt)
                
                import json
                cleaned_text = response.text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                
                data = json.loads(cleaned_text.strip())
                return True, {
                    "question_text": text,
                    "category": data.get("category", "Technical"),
                    "confidence": data.get("confidence", 0.9)
                }
            except Exception as e:
                logger.error(f"Gemini classification failed: {e}")

        # Heuristic fallback classifier
        category, confidence = self._heuristic_classifier(text)
        return True, {
            "question_text": text,
            "category": category,
            "confidence": confidence
        }

    def _heuristic_classifier(self, text: str) -> Tuple[str, float]:
        """
        Fallback keyword classifier for offline or error limits.
        """
        cleaned = text.lower()
        
        if "design" in cleaned or "architecture" in cleaned or "microservice" in cleaned or "scale" in cleaned:
            return "System Design", 0.95
        elif "tell me about a time" in cleaned or "conflict" in cleaned or "disagreement" in cleaned or "describe a" in cleaned:
            return "Behavioral", 0.90
        elif "salary" in cleaned or "relocate" in cleaned or "visa" in cleaned or "experience" in cleaned or "why do you want" in cleaned:
            return "HR", 0.85
        elif "product" in cleaned or "metric" in cleaned or "user" in cleaned or "customer" in cleaned:
            return "Product", 0.80
        else:
            return "Technical", 0.75

question_engine = QuestionDetectionEngine()
