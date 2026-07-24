from typing import List
import traceback

from langchain.embeddings import CacheBackedEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

from app.init_db import logger


class CacheBackedEmbeddingsExtended(CacheBackedEmbeddings):
    def embed_query(self, text: str) -> List[float]:
        vectors = self.document_embedding_store.mget([text])
        text_embeddings = vectors[0]

        if text_embeddings is None:
            text_embeddings = self.underlying_embeddings.embed_query(text)
            self.document_embedding_store.mset(
                list(zip([text], [text_embeddings]))
            )

        return text_embeddings


_embedding_model = None


def get_embedding_model():
    global _embedding_model

    if _embedding_model is None:
        try:
            logger.info("=" * 80)
            logger.info("Starting HuggingFace embedding model initialization...")
            logger.info("Model: sentence-transformers/all-MiniLM-L6-v2")

            _embedding_model = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )

            logger.info("HuggingFace embedding model loaded successfully.")
            logger.info("=" * 80)

        except Exception as e:
            logger.error("=" * 80)
            logger.error("FAILED TO LOAD HUGGINGFACE EMBEDDING MODEL")
            logger.error(f"Exception Type: {type(e).__name__}")
            logger.error(f"Exception Message: {str(e)}")
            logger.error("Full Traceback:")
            logger.error(traceback.format_exc())
            logger.error("=" * 80)
            raise

    return _embedding_model