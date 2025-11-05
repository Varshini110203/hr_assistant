import os
import faiss
import numpy as np
import pickle
import hashlib
import logging
from datetime import datetime
from typing import List, Tuple, Dict, Any
import PyPDF2
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self):
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        self.vector_store = None
        self.documents = []
        self.document_versions = {}
        self._initialized = False

    # 🧠 --- Basic PDF Extraction ---
    def extract_document_content(self, file_path: str) -> Dict[str, Any]:
        """Extract content and metadata from a PDF file."""
        try:
            with open(file_path, "rb") as f:
                pdf = PyPDF2.PdfReader(f)
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

                content_hash = hashlib.md5(text.encode()).hexdigest()
                doc_title = os.path.splitext(os.path.basename(file_path))[0]

                return {
                    "file_path": file_path,
                    "filename": os.path.basename(file_path),
                    "title": doc_title,
                    "content": text,
                    "content_hash": content_hash,
                    "page_count": len(pdf.pages),
                    "file_size": os.path.getsize(file_path),
                    "modified_time": os.path.getmtime(file_path),
                    "created_time": os.path.getctime(file_path),
                }
        except Exception as e:
            logger.error(f"Error reading PDF {file_path}: {str(e)}")
            return None

    # 🔍 --- Automatic rebuild detection ---
    def _vector_store_is_up_to_date(self) -> bool:
        """Check if existing vector store matches current document folder state."""
        index_path = os.path.join(settings.VECTOR_STORE_PATH, "faiss.index")
        versions_path = os.path.join(settings.VECTOR_STORE_PATH, "versions.pkl")
        documents_path = settings.DOCUMENTS_PATH

        if not os.path.exists(index_path) or not os.path.exists(versions_path):
            return False

        try:
            with open(versions_path, "rb") as f:
                stored_versions = pickle.load(f)

            # Current folder PDFs
            current_files = {
                f: os.path.getmtime(os.path.join(documents_path, f))
                for f in os.listdir(documents_path)
                if f.endswith(".pdf")
            }

            if not current_files:
                return False

            stored_files = {
                info["filename"]: info["modified_time"] for info in stored_versions.values()
            }

            # Added or removed PDFs
            if set(current_files.keys()) != set(stored_files.keys()):
                return False

            # Modified PDFs
            for fname, mtime in current_files.items():
                if abs(mtime - stored_files.get(fname, 0)) > 1:
                    return False

            return True

        except Exception as e:
            logger.warning(f"Vector store freshness check failed: {str(e)}")
            return False

    # 📄 --- Load and Split Documents ---
    def load_documents(self) -> List[str]:
        """Load and split PDF documents from the documents directory."""
        documents_path = settings.DOCUMENTS_PATH
        all_texts = []

        os.makedirs(documents_path, exist_ok=True)
        pdf_files = [f for f in os.listdir(documents_path) if f.endswith(".pdf")]

        if not pdf_files:
            logger.warning(f"No PDF files found in {documents_path}")
            return []

        logger.info(f"Found {len(pdf_files)} PDF files: {pdf_files}")

        all_documents = []
        for filename in pdf_files:
            file_path = os.path.join(documents_path, filename)
            doc_data = self.extract_document_content(file_path)
            if doc_data:
                all_documents.append(doc_data)
                logger.info(f"Extracted {filename} ({doc_data['page_count']} pages)")

        if not all_documents:
            return []

        # Save version info directly (simplified — no grouping)
        self.document_versions = {
            doc["filename"]: doc for doc in all_documents
        }

        for doc in all_documents:
            chunks = self.text_splitter.split_text(doc["content"])
            all_texts.extend(chunks)
            logger.info(f"Split {doc['filename']} into {len(chunks)} chunks")

        logger.info(f"Total {len(all_texts)} text chunks from {len(all_documents)} documents")
        return all_texts

    # 🔢 --- Embeddings ---
    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        if not texts:
            logger.warning("No texts to create embeddings for")
            return np.array([])

        logger.info(f"Creating embeddings for {len(texts)} chunks")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
        logger.info(f"Embeddings created: {embeddings.shape}")
        return embeddings

    # 🧱 --- FAISS Store Build ---
    def build_vector_store(self, texts: List[str], embeddings: np.ndarray):
        if len(texts) == 0 or embeddings.shape[0] == 0:
            logger.warning("No texts or embeddings to build vector store")
            return

        dim = embeddings.shape[1]
        self.vector_store = faiss.IndexFlatL2(dim)
        self.vector_store.add(embeddings.astype(np.float32))
        self.documents = texts

        os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)
        faiss.write_index(self.vector_store, os.path.join(settings.VECTOR_STORE_PATH, "faiss.index"))

        with open(os.path.join(settings.VECTOR_STORE_PATH, "documents.pkl"), "wb") as f:
            pickle.dump(texts, f)

        with open(os.path.join(settings.VECTOR_STORE_PATH, "versions.pkl"), "wb") as f:
            pickle.dump(self.document_versions, f)

        self._initialized = True
        logger.info(f"✅ Vector store built with {len(texts)} chunks")

    # 📦 --- Load FAISS Store ---
    def load_vector_store(self) -> bool:
        index_path = os.path.join(settings.VECTOR_STORE_PATH, "faiss.index")
        docs_path = os.path.join(settings.VECTOR_STORE_PATH, "documents.pkl")
        versions_path = os.path.join(settings.VECTOR_STORE_PATH, "versions.pkl")

        if not (os.path.exists(index_path) and os.path.exists(docs_path)):
            return False

        try:
            self.vector_store = faiss.read_index(index_path)
            with open(docs_path, "rb") as f:
                self.documents = pickle.load(f)
            if os.path.exists(versions_path):
                with open(versions_path, "rb") as f:
                    self.document_versions = pickle.load(f)
            self._initialized = True
            logger.info("✅ Loaded existing FAISS vector store")
            return True
        except Exception as e:
            logger.error(f"Failed to load vector store: {str(e)}")
            return False

    # 🚀 --- Initialize or Rebuild Automatically ---
    def initialize_vector_store(self):
        logger.info("Initializing vector store...")

        if self._vector_store_is_up_to_date():
            if self.load_vector_store():
                logger.info("✅ Vector store is up-to-date — using existing files.")
                return

        logger.info("⚙️ Rebuilding vector store due to new or modified documents...")
        texts = self.load_documents()
        if texts:
            embeddings = self.create_embeddings(texts)
            if embeddings.size > 0:
                self.build_vector_store(texts, embeddings)
                logger.info("✅ Vector store rebuilt successfully")
            else:
                logger.error("Embedding generation failed.")
        else:
            logger.warning("No documents found for vector store rebuild.")
            self._initialized = False

    # 🔎 --- Search Function ---
    def search_similar(self, query: str, k: int = 3) -> List[Tuple[str, float]]:
        if not self._initialized or self.vector_store is None or not self.documents:
            logger.error("Vector store not ready for search.")
            return []

        try:
            query_vec = self.embedding_model.encode([query])
            distances, indices = self.vector_store.search(query_vec.astype(np.float32), k)
            results = []
            for i, idx in enumerate(indices[0]):
                if 0 <= idx < len(self.documents):
                    similarity = 1.0 / (1.0 + distances[0][i])
                    results.append((self.documents[idx], similarity))
            return results
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []

    # ⚙️ --- Status ---
    def get_status(self) -> dict:
        return {
            "initialized": self._initialized,
            "documents_loaded": len(self.documents),
            "vector_store_ready": self.vector_store is not None,
            "document_count": len(self.document_versions),
        }

    def is_initialized(self) -> bool:
        return self._initialized

    def get_version_context(self) -> str:
        """Get a short description of currently loaded document versions."""
        if not self.document_versions:
            return "No documents found in the system."

        latest_files = [info["filename"] for info in self.document_versions.values()]
        modified_dates = [
            datetime.fromtimestamp(info["modified_time"]).strftime("%Y-%m-%d")
            for info in self.document_versions.values()
        ]

        summary = "\n".join(
            [f"• {f} (last modified: {d})" for f, d in zip(latest_files, modified_dates)]
        )

        return (
            f"Using {len(latest_files)} document(s) from '{settings.DOCUMENTS_PATH}'.\n"
            f"All documents are up to date.\n\n{summary}"
        )
