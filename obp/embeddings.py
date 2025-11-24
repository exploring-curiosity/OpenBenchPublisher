"""Embeddings generation using VoyageAI."""

from typing import List, Union
import numpy as np
import voyageai
import logging
import time
from obp.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Unified embedding service using VoyageAI."""
    
    def __init__(self):
        logger.info("Initializing VoyageAI client...")
        self.client = voyageai.Client(api_key=settings.voyage_api_key)
        self.last_call_time = 0
        self.min_interval = 20  # 20 seconds between calls (3 RPM = 1 call per 20 sec)
        logger.info("VoyageAI client ready")
    
    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        self.last_call_time = time.time()
    
    def embed_text(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for text(s) using VoyageAI with rate limiting."""
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]
        
        # Rate limit
        self._rate_limit()
        
        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = self.client.embed(texts, model="voyage-2", input_type="document")
                embeddings = result.embeddings
                logger.debug(f"Generated {len(embeddings)} embeddings via VoyageAI")
                return embeddings[0] if is_single else embeddings
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 30  # 30, 60, 90 seconds
                    logger.warning(f"VoyageAI error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"VoyageAI failed after {max_retries} attempts: {e}")
                    raise
    
    def embed_image_caption(self, caption: str) -> List[float]:
        """Generate embedding for image caption/description."""
        return self.embed_text(caption)
    
    def compute_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Compute cosine similarity between two embeddings."""
        vec1 = np.array(emb1)
        vec2 = np.array(emb2)
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        return float(similarity)


# Global embedding service instance (lazy-loaded)
_embedding_service = None

def get_embedding_service():
    """Get or create the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

# Lazy accessor
class _EmbeddingServiceAccessor:
    def __getattr__(self, name):
        return getattr(get_embedding_service(), name)

embedding_service = _EmbeddingServiceAccessor()
