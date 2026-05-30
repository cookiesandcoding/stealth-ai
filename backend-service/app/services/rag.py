import logging
import io
from typing import Dict, Any, List, Optional
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Qdrant Client
try:
    qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    # Ensure collection exists
    qdrant_client.recreate_collection(
        collection_name=settings.QDRANT_COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    logger.info("Successfully established connection to Qdrant and created collection.")
except Exception as e:
    logger.warning(f"Could not connect to Qdrant: {e}. Running local memory-based RAG simulation.")
    qdrant_client = None

class ResumeRAGService:
    def __init__(self):
        self._memory_db: Dict[str, List[Dict[str, Any]]] = {}

    def extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """
        Parses raw PDF bytes and extracts plain text.
        """
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            raise ValueError(f"Could not parse PDF document: {e}")

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        """
        Splits text into overlapping chunks for indexing.
        """
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
            if i + chunk_size >= len(words):
                break
        return chunks

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generates standard 384-dimensional embeddings (simulated or simplified sentence-transformer model).
        """
        # Create deterministic pseudo-embedding vector of size 384 based on hash character values
        import hashlib
        vector = []
        for d in range(384):
            val = int(hashlib.md5(f"{text}-{d}".encode()).hexdigest(), 16)
            vector.append((val % 2000 - 1000) / 1000.0)
        return vector

    async def ingest_resume(self, user_id: str, file_name: str, file_bytes: bytes) -> Dict[str, Any]:
        """
        Extracts, chunks, embeds and uploads a resume to Qdrant or local memory database.
        """
        text = self.extract_text_from_pdf(file_bytes)
        if not text:
            raise ValueError("No text could be extracted from the PDF resume.")
            
        chunks = self.chunk_text(text)
        points = []
        mem_chunks = []
        
        for idx, chunk in enumerate(chunks):
            embedding = self._generate_embedding(chunk)
            point_id = hash(f"{user_id}-{file_name}-{idx}") % (10**8)
            
            # Prepare memory database payload
            chunk_data = {
                "id": point_id,
                "text": chunk,
                "metadata": {"user_id": user_id, "file_name": file_name, "chunk_index": idx}
            }
            mem_chunks.append(chunk_data)
            
            if qdrant_client:
                points.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=chunk_data["metadata"] | {"text": chunk}
                ))
        
        # Save locally or push to Qdrant
        if qdrant_client:
            try:
                qdrant_client.upsert(
                    collection_name=settings.QDRANT_COLLECTION,
                    points=points
                )
                logger.info(f"Successfully upserted {len(points)} chunks into Qdrant for user {user_id}.")
            except Exception as e:
                logger.error(f"Error upserting points into Qdrant: {e}")
                qdrant_client = None
                
        # Store in memory cache
        self._memory_db[user_id] = mem_chunks
        
        return {
            "file_name": file_name,
            "chunks_count": len(chunks),
            "parsed_text_preview": text[:200] + "...",
            "storage_medium": "qdrant" if qdrant_client else "in_memory"
        }

    async def retrieve_context(self, user_id: str, query: str, limit: int = 3) -> str:
        """
        Queries Qdrant or local memory for similarity contexts matching the question.
        """
        if not query:
            return ""
            
        query_vector = self._generate_embedding(query)
        retrieved_texts = []
        
        if qdrant_client:
            try:
                results = qdrant_client.search(
                    collection_name=settings.QDRANT_COLLECTION,
                    query_vector=query_vector,
                    limit=limit
                )
                for res in results:
                    if res.payload and "text" in res.payload:
                        retrieved_texts.append(res.payload["text"])
            except Exception as e:
                logger.error(f"Error querying Qdrant: {e}")
                
        # Fallback to local memory similarity search (keyword overlap)
        if not retrieved_texts and user_id in self._memory_db:
            chunks = self._memory_db[user_id]
            query_words = set(query.lower().split())
            scored_chunks = []
            for c in chunks:
                chunk_words = set(c["text"].lower().split())
                overlap = len(query_words.intersection(chunk_words))
                scored_chunks.append((overlap, c["text"]))
            # Sort by score descending
            scored_chunks.sort(key=lambda x: x[0], reverse=True)
            retrieved_texts = [text for score, text in scored_chunks[:limit]]
            
        return "\n\n".join(retrieved_texts)

resume_rag = ResumeRAGService()
