import sys
import os
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from pathlib import Path
import yaml
import json
from typing import List
from dotenv import load_dotenv

from langchain.vectorstores.pgvector import PGVector
from langchain.embeddings import CacheBackedEmbeddings
from langchain.text_splitter import TokenTextSplitter
from fastapi.encoders import jsonable_encoder
from langchain_community.document_loaders import PyPDFLoader
from unstructured.cleaners.core import clean_extra_whitespace

from app.core.config import logger
from app.schemas.ingestion_schema import LOADER_DICT
from app.utils.general_helpers import find_project_root
from app.ingestion.utils.embedding_models import get_embedding_model

load_dotenv()

POPPLER_PATH = r"C:\Users\salla\Release-26.02.0-0\poppler-26.02.0\Library\bin"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR"

if os.path.exists(POPPLER_PATH):
    os.environ["PATH"] = POPPLER_PATH + os.pathsep + os.environ["PATH"]

if os.path.exists(TESSERACT_PATH):
    os.environ["PATH"] = TESSERACT_PATH + os.pathsep + os.environ["PATH"]

current_script_path = Path(__file__).resolve()
project_root = find_project_root(current_script_path)

ingestion_config_path = project_root / "app" / "config" / "ingestion.yml"

with open(ingestion_config_path, "r") as f:
    ingestion_config = yaml.safe_load(f)

path_input_folder = project_root.parent / ingestion_config["PATH_RAW_PDF"]
path_extraction_folder = project_root.parent / ingestion_config["PATH_EXTRACTION"]

os.makedirs(path_extraction_folder, exist_ok=True)

collection_name = ingestion_config["COLLECTION_NAME"]
pdf_parser = ingestion_config["PDF_PARSER"]

db_name = os.getenv("DB_NAME")
DATABASE_HOST = os.getenv("DB_HOST")
DATABASE_PORT = os.getenv("DB_PORT")
DATABASE_USER = os.getenv("DB_USER")
DATABASE_PASSWORD = os.getenv("DB_PASS")


class PDFExtractionPipeline:

    db: PGVector | None = None
    embedding: CacheBackedEmbeddings

    def __init__(self):

        logger.info("Initializing PDFExtractionPipeline")

        self.pdf_loader = LOADER_DICT[pdf_parser]

        # Uses cached model from embedding_models.py
        self.embedding_model = get_embedding_model()

        self.connection_str = PGVector.connection_string_from_db_params(
            driver="psycopg2",
            host=DATABASE_HOST,
            port=DATABASE_PORT,
            database=db_name,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
        )

    def run(self, collection_name: str):

        logger.info(f"Running extraction pipeline for collection: {collection_name}")

        self._load_documents(
            folder_path=path_input_folder,
            collection_name=collection_name,
        )

    def _load_documents(self, folder_path, collection_name):

        text_documents = self._load_docs(folder_path)

        logger.info(f"Loaded {len(text_documents)} documents")

        if not text_documents:
            logger.warning("No documents loaded.")
            return

        splitter = TokenTextSplitter(
            chunk_size=900,
            chunk_overlap=150,
        )

        texts = splitter.split_documents(text_documents)

        for text in texts:
            text.metadata["type"] = "Text"

        PGVector.from_documents(
            embedding=self.embedding_model,
            collection_name=collection_name,
            documents=texts,
            connection_string=self.connection_str,
            pre_delete_collection=True,   # changed
        )

        logger.info("Vector DB populated successfully.")

    def _load_docs(self, dir_path):

        documents = []

        for file_name in os.listdir(dir_path):

            if not file_name.lower().endswith(".pdf"):
                continue

            file_path = os.path.join(dir_path, file_name)

            logger.info(f"Loading {file_path}")

            try:

                loader = PyPDFLoader(file_path)

                file_docs = loader.load()

                documents.extend(file_docs)

                json_path = os.path.join(
                    path_extraction_folder,
                    Path(file_name).stem + ".json",
                )

                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(
                        jsonable_encoder(file_docs),
                        f,
                        indent=4,
                        ensure_ascii=False,
                    )

                logger.info(f"{file_name} processed successfully.")

            except Exception:

                logger.exception("PDF extraction failed!")
                traceback.print_exc()

        return documents


if __name__ == "__main__":

    logger.info("Starting PDF extraction pipeline")

    pipeline = PDFExtractionPipeline()

    pipeline.run(collection_name)