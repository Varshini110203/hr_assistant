import os
import PyPDF2
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings
import logging
from typing import List, Tuple
import pickle

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
        self._initialized = False

    def load_documents(self) -> List[str]:
        """Load and split PDF documents from the documents directory"""
        documents_path = settings.DOCUMENTS_PATH
        all_texts = []
        
        # Create documents directory if it doesn't exist
        os.makedirs(documents_path, exist_ok=True)
        
        # Check if documents directory exists and has PDF files
        if not os.path.exists(documents_path):
            logger.warning(f"Documents directory {documents_path} does not exist")
            return all_texts
        
        pdf_files = [f for f in os.listdir(documents_path) if f.endswith('.pdf')]
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {documents_path}")
            # Create default HR content
            default_content = [
                "HR Policy: Employees are entitled to 15 days of paid leave per year.",
                "Leave Policy: Sick leave requires a doctor's note for absences longer than 3 days.",
                "Administrative Guidelines: All expense reports must be submitted by the end of the month.",
                "Employee Handbook: The company dress code is business casual unless otherwise specified.",
                "Remote Work Policy: Remote work is allowed for up to 2 days per week with manager approval.",
                "Benefits: Health insurance coverage begins on the first day of the month following employment start date.",
                "Performance Reviews: Annual performance reviews are conducted in December each year.",
                "Code of Conduct: All employees must adhere to the company's code of conduct and ethical guidelines.",
                "Training: New employees must complete mandatory training within the first 30 days of employment.",
                "Travel Policy: Business travel requires pre-approval from department head and HR."
            ]
            return default_content
        
        for filename in pdf_files:
            file_path = os.path.join(documents_path, filename)
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    
                    # Split text into chunks
                    chunks = self.text_splitter.split_text(text)
                    all_texts.extend(chunks)
                    logger.info(f"Loaded {len(chunks)} chunks from {filename}")
                    
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
        
        return all_texts

    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """Create embeddings for text chunks"""
        if not texts:
            logger.warning("No texts to create embeddings for")
            return np.array([])
            
        logger.info(f"Creating embeddings for {len(texts)} text chunks")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
        return embeddings

    def build_vector_store(self, texts: List[str], embeddings: np.ndarray):
        """Build FAISS vector store"""
        if len(texts) == 0 or embeddings.shape[0] == 0:
            logger.warning("No texts or embeddings to build vector store")
            return
            
        dimension = embeddings.shape[1]
        self.vector_store = faiss.IndexFlatL2(dimension)
        self.vector_store.add(embeddings.astype(np.float32))
        self.documents = texts
        
        # Save vector store and documents
        os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)
        faiss.write_index(self.vector_store, os.path.join(settings.VECTOR_STORE_PATH, "faiss.index"))
        
        with open(os.path.join(settings.VECTOR_STORE_PATH, "documents.pkl"), 'wb') as f:
            pickle.dump(texts, f)
        
        self._initialized = True
        logger.info(f"Vector store built with {len(texts)} documents")

    def load_vector_store(self) -> bool:
        """Load pre-built vector store"""
        index_path = os.path.join(settings.VECTOR_STORE_PATH, "faiss.index")
        documents_path = os.path.join(settings.VECTOR_STORE_PATH, "documents.pkl")
        
        if os.path.exists(index_path) and os.path.exists(documents_path):
            try:
                self.vector_store = faiss.read_index(index_path)
                with open(documents_path, 'rb') as f:
                    self.documents = pickle.load(f)
                self._initialized = True
                logger.info(f"Loaded existing vector store with {len(self.documents)} documents")
                return True
            except Exception as e:
                logger.error(f"Error loading vector store: {str(e)}")
                return False
        return False

    def initialize_vector_store(self):
        """Initialize vector store - load existing or create new"""
        logger.info("Initializing vector store...")
        
        # Try to load existing vector store first
        if self.load_vector_store():
            logger.info("Vector store initialization completed successfully")
            return
        
        logger.info("Creating new vector store...")
        texts = self.load_documents()
        
        if texts:
            logger.info(f"Processing {len(texts)} text chunks")
            embeddings = self.create_embeddings(texts)
            if embeddings.size > 0:
                self.build_vector_store(texts, embeddings)
                logger.info("Vector store created successfully")
            else:
                logger.error("Failed to create embeddings")
                self._initialized = False
        else:
            logger.warning("No documents available for vector store")
            self._initialized = False

    def search_similar(self, query: str, k: int = 3) -> List[Tuple[str, float]]:
        """Search for similar documents"""
        if not self._initialized or self.vector_store is None or not self.documents:
            logger.error("Vector store not ready for search")
            return []
        
        try:
            query_embedding = self.embedding_model.encode([query])
            distances, indices = self.vector_store.search(query_embedding.astype(np.float32), k)
            
            results = []
            for i, idx in enumerate(indices[0]):
                if 0 <= idx < len(self.documents):
                    # Convert distance to similarity score
                    similarity_score = 1.0 / (1.0 + distances[0][i])
                    results.append((self.documents[idx], similarity_score))
            
            logger.info(f"Found {len(results)} similar documents for query")
            return results
            
        except Exception as e:
            logger.error(f"Error during similarity search: {str(e)}")
            return []

    def is_initialized(self) -> bool:
        """Check if vector store is initialized and ready"""
        return self._initialized

    def get_status(self) -> dict:
        """Get current status of document processor"""
        return {
            "initialized": self._initialized,
            "documents_loaded": len(self.documents) if self._initialized else 0,
            "vector_store_ready": self.vector_store is not None
        }