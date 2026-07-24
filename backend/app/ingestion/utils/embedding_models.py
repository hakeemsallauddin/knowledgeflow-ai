from typing import List

from langchain.embeddings import CacheBackedEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from app.init_db import logger


class CacheBackedEmbeddingsExtended(CacheBackedEmbeddings):
    def embed_query(self, text: str) -> List[float]:
        vectors = self.document_embedding_store.mget([text])
        text_embeddings = vectors[0]

        if text_embeddings is None:
            text_embeddings = self.underlying_embeddings.embed_query(text)
            self.document_embedding_store.mset(list(zip([text], [text_embeddings])))

        return text_embeddings


# ----------------------------------------------------------
# Load the model ONLY ONCE when FastAPI starts
# ----------------------------------------------------------

logger.info("Loading HuggingFace embedding model...")

_EMBEDDING_MODEL = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

logger.info("HuggingFace embedding model loaded successfully.")


def get_embedding_model():
    return _EMBEDDING_MODEL