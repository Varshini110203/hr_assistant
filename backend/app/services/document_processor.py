import os
import PyPDF2
import faiss
import numpy as np
import hashlib
import pickle
from datetime import datetime
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.core.config import settings
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)

class ContentBasedVersionManager:
    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        self.vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
    
    def extract_document_content(self, file_path: str) -> Dict[str, Any]:
        """Extract content and metadata from PDF"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                # Create content signature
                content_hash = hashlib.md5(text.encode()).hexdigest()
                
                # Extract document title from metadata or filename
                doc_title = ""
                if pdf_reader.metadata and pdf_reader.metadata.get('/Title'):
                    doc_title = pdf_reader.metadata.get('/Title')
                else:
                    # Use filename without extension as title
                    doc_title = os.path.splitext(os.path.basename(file_path))[0]
                
                return {
                    'file_path': file_path,
                    'filename': os.path.basename(file_path),
                    'title': doc_title,
                    'content': text,
                    'content_hash': content_hash,
                    'page_count': len(pdf_reader.pages),
                    'file_size': os.path.getsize(file_path),
                    'modified_time': os.path.getmtime(file_path),
                    'created_time': os.path.getctime(file_path),
                    'metadata': pdf_reader.metadata if pdf_reader.metadata else {}
                }
        except Exception as e:
            logger.error(f"Error extracting content from {file_path}: {str(e)}")
            return None
    
    def group_similar_documents(self, documents: List[Dict]) -> Dict[str, List[Dict]]:
        """Group documents by content similarity"""
        if not documents:
            return {}
        
        # Filter out documents with no content
        valid_docs = [doc for doc in documents if doc and doc.get('content', '').strip()]
        
        if not valid_docs:
            # Fallback to filename-based grouping
            return self._group_by_fallback(documents)
        
        try:
            # Use TF-IDF for content similarity
            contents = [doc['content'] for doc in valid_docs]
            tfidf_matrix = self.vectorizer.fit_transform(contents)
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            groups = {}
            used_indices = set()
            
            for i, doc in enumerate(valid_docs):
                if i in used_indices:
                    continue
                    
                # Find similar documents
                similar_indices = [j for j in range(len(valid_docs)) 
                                 if similarity_matrix[i][j] >= self.similarity_threshold 
                                 and j not in used_indices]
                
                if similar_indices:
                    # Create group key from document title
                    group_key = self._create_group_key(valid_docs[similar_indices[0]])
                    groups[group_key] = [valid_docs[j] for j in similar_indices]
                    used_indices.update(similar_indices)
            
            # Handle any remaining documents
            for i, doc in enumerate(valid_docs):
                if i not in used_indices:
                    group_key = self._create_group_key(doc)
                    groups[group_key] = [doc]
            
            return groups
            
        except Exception as e:
            logger.error(f"Error in similarity grouping: {str(e)}")
            return self._group_by_fallback(documents)
    
    def _create_group_key(self, document: Dict) -> str:
        """Create a meaningful group key from document"""
        title = document.get('title', '').lower()
        if not title or title == 'unknown':
            # Use content-based key
            content_preview = document['content'][:100].lower().replace('\n', ' ')
            return f"document_{document['content_hash'][:8]}"
        
        # Clean title for use as key
        clean_title = ''.join(c if c.isalnum() else '_' for c in title)
        return clean_title
    
    def _group_by_fallback(self, documents: List[Dict]) -> Dict[str, List[Dict]]:
        """Fallback grouping method using content hashes"""
        groups = {}
        for doc in documents:
            if not doc:
                continue
            group_key = self._create_group_key(doc)
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(doc)
        return groups
    
    def identify_latest_versions(self, document_groups: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        """Identify latest version from each document group"""
        latest_versions = {}
        
        for group_key, documents in document_groups.items():
            if not documents:
                continue
                
            if len(documents) == 1:
                # Single document in group
                latest_versions[group_key] = {
                    'latest': documents[0],
                    'previous': None,
                    'all_versions': [documents[0]],
                    'is_multiple_versions': False,
                    'version_count': 1
                }
            else:
                # Multiple documents - find latest by modification time
                sorted_docs = sorted(documents, key=lambda x: x['modified_time'], reverse=True)
                latest_versions[group_key] = {
                    'latest': sorted_docs[0],
                    'previous': sorted_docs[1] if len(sorted_docs) > 1 else None,
                    'all_versions': sorted_docs,
                    'is_multiple_versions': True,
                    'version_count': len(sorted_docs)
                }
        
        return latest_versions
    
    def compare_versions(self, old_doc: Dict, new_doc: Dict) -> Dict[str, Any]:
        """Compare two versions of a document and identify differences"""
        if not old_doc or not new_doc:
            return {'error': 'Missing document for comparison'}
            
        old_content = old_doc.get('content', '')
        new_content = new_doc.get('content', '')
        
        if not old_content or not new_content:
            return {'error': 'Missing content for comparison'}
        
        # Simple content comparison using word sets
        old_words = set(old_content.lower().split())
        new_words = set(new_content.lower().split())
        
        added_words = new_words - old_words
        removed_words = old_words - new_words
        
        # Calculate similarity using TF-IDF
        try:
            content_vector = self.vectorizer.transform([old_content, new_content])
            similarity = cosine_similarity(content_vector[0:1], content_vector[1:2])[0][0]
        except Exception as e:
            logger.warning(f"Similarity calculation failed: {str(e)}")
            similarity = 0.0
        
        # Extract meaningful keywords (filter out common words)
        common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        meaningful_added = [word for word in added_words if word not in common_words and len(word) > 3]
        meaningful_removed = [word for word in removed_words if word not in common_words and len(word) > 3]
        
        return {
            'similarity_score': similarity,
            'content_changes': {
                'added_keywords': meaningful_added[:15],
                'removed_keywords': meaningful_removed[:15],
                'total_added': len(meaningful_added),
                'total_removed': len(meaningful_removed),
            },
            'structural_changes': {
                'page_count_change': new_doc.get('page_count', 0) - old_doc.get('page_count', 0),
                'file_size_change': new_doc.get('file_size', 0) - old_doc.get('file_size', 0),
                'page_count_old': old_doc.get('page_count', 0),
                'page_count_new': new_doc.get('page_count', 0),
            },
            'temporal_changes': {
                'days_between_versions': int((datetime.fromtimestamp(new_doc['modified_time']) - 
                                           datetime.fromtimestamp(old_doc['modified_time'])).days),
                'old_version_date': datetime.fromtimestamp(old_doc['modified_time']).strftime('%Y-%m-%d'),
                'new_version_date': datetime.fromtimestamp(new_doc['modified_time']).strftime('%Y-%m-%d'),
            }
        }


class DocumentProcessor:
    def __init__(self):
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        self.version_manager = ContentBasedVersionManager(similarity_threshold=0.7)
        self.vector_store = None
        self.documents = []
        self.document_versions = {}
        self._initialized = False

    def _get_default_content(self) -> List[str]:
        """Get default HR content when no documents are available"""
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

    def load_documents(self) -> List[str]:
        """Load and split PDF documents from the documents directory with version awareness"""
        documents_path = settings.DOCUMENTS_PATH
        all_texts = []
        
        # Create documents directory if it doesn't exist
        os.makedirs(documents_path, exist_ok=True)
        
        # Check if documents directory exists
        if not os.path.exists(documents_path):
            logger.warning(f"Documents directory {documents_path} does not exist")
            return self._get_default_content()
        
        pdf_files = [f for f in os.listdir(documents_path) if f.endswith('.pdf')]
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {documents_path}")
            return self._get_default_content()
        
        logger.info(f"Found {len(pdf_files)} PDF files: {pdf_files}")
        
        # Extract content from all documents
        all_documents = []
        for filename in pdf_files:
            file_path = os.path.join(documents_path, filename)
            doc_content = self.version_manager.extract_document_content(file_path)
            if doc_content:
                all_documents.append(doc_content)
                logger.info(f"Extracted content from {filename} ({doc_content['page_count']} pages)")
        
        if not all_documents:
            logger.warning("No valid documents could be processed")
            return self._get_default_content()
        
        # Group similar documents and identify versions
        logger.info("Grouping similar documents...")
        document_groups = self.version_manager.group_similar_documents(all_documents)
        self.document_versions = self.version_manager.identify_latest_versions(document_groups)
        
        logger.info(f"Found {len(self.document_versions)} document groups")
        for group_key, version_info in self.document_versions.items():
            if version_info['is_multiple_versions']:
                logger.info(f"Group '{group_key}': {version_info['version_count']} versions")
            else:
                logger.info(f"Group '{group_key}': single version")
        
        # Use only latest versions for processing
        latest_count = 0
        for group_key, version_info in self.document_versions.items():
            latest_doc = version_info['latest']
            if latest_doc and latest_doc.get('content'):
                chunks = self.text_splitter.split_text(latest_doc['content'])
                all_texts.extend(chunks)
                latest_count += 1
                logger.info(f"Loaded {len(chunks)} chunks from latest version: {latest_doc['filename']}")
        
        logger.info(f"Processed {latest_count} latest document versions with {len(all_texts)} total chunks")
        return all_texts

    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """Create embeddings for text chunks"""
        if not texts:
            logger.warning("No texts to create embeddings for")
            return np.array([])
            
        logger.info(f"Creating embeddings for {len(texts)} text chunks")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
        logger.info(f"Created embeddings with shape: {embeddings.shape}")
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
        
        # Save version information
        with open(os.path.join(settings.VECTOR_STORE_PATH, "versions.pkl"), 'wb') as f:
            pickle.dump(self.document_versions, f)
        
        self._initialized = True
        logger.info(f"Vector store built with {len(texts)} documents")

    def load_vector_store(self) -> bool:
        """Load pre-built vector store and version information"""
        index_path = os.path.join(settings.VECTOR_STORE_PATH, "faiss.index")
        documents_path = os.path.join(settings.VECTOR_STORE_PATH, "documents.pkl")
        versions_path = os.path.join(settings.VECTOR_STORE_PATH, "versions.pkl")
        
        if os.path.exists(index_path) and os.path.exists(documents_path):
            try:
                self.vector_store = faiss.read_index(index_path)
                with open(documents_path, 'rb') as f:
                    self.documents = pickle.load(f)
                
                # Load version information if available
                if os.path.exists(versions_path):
                    with open(versions_path, 'rb') as f:
                        self.document_versions = pickle.load(f)
                
                self._initialized = True
                logger.info(f"Loaded existing vector store with {len(self.documents)} documents")
                if self.document_versions:
                    logger.info(f"Loaded version information for {len(self.document_versions)} document groups")
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

    def get_version_comparison(self, query: str = "") -> str:
        """Generate version comparison based on user query or general overview"""
        if not self.document_versions:
            return "No document versions available for comparison."
        
        # If specific query provided, find relevant document group
        if query and query.strip():
            relevant_group = self._find_relevant_document_group(query.strip())
            if relevant_group and relevant_group['is_multiple_versions']:
                return self._get_specific_comparison(relevant_group)
        
        # Return general version overview
        return self._get_version_overview()
    
    def _find_relevant_document_group(self, query: str) -> Dict:
        """Find the most relevant document group for the query"""
        query_lower = query.lower()
        
        # Simple keyword-based matching
        for group_key, version_info in self.document_versions.items():
            if not version_info['is_multiple_versions']:
                continue
                
            latest_content = version_info['latest'].get('content', '').lower()
            doc_title = version_info['latest'].get('title', '').lower()
            
            # Check if query keywords match document content or title
            query_keywords = set(query_lower.split())
            content_keywords = set(latest_content.split())
            title_keywords = set(doc_title.split())
            
            # Simple overlap check
            content_overlap = len(query_keywords.intersection(content_keywords))
            title_overlap = len(query_keywords.intersection(title_keywords))
            
            if content_overlap > 1 or title_overlap > 0:
                return version_info
        
        # Return first group with multiple versions as fallback
        for group_key, version_info in self.document_versions.items():
            if version_info['is_multiple_versions']:
                return version_info
        
        return None
    
    def _get_specific_comparison(self, group_info: Dict) -> str:
        """Get specific comparison for a document group"""
        latest = group_info['latest']
        previous = group_info['previous']
        
        if not previous:
            return f"Only one version available for '{latest.get('title', 'Unknown')}'"
        
        comparison = self.version_manager.compare_versions(previous, latest)
        
        if 'error' in comparison:
            return f"Unable to compare versions: {comparison['error']}"
        
        response = f"""**Version Comparison: {latest.get('title', 'Unknown Document')}**

📄 **Latest Version**: {latest['filename']} (Modified: {comparison['temporal_changes']['new_version_date']})
📄 **Previous Version**: {previous['filename']} (Modified: {comparison['temporal_changes']['old_version_date']})

**Key Changes:**
• Content Similarity: {comparison['similarity_score']:.1%}
• Page Count: {comparison['structural_changes']['page_count_old']} → {comparison['structural_changes']['page_count_new']} ({comparison['structural_changes']['page_count_change']:+d})
• File Size: {previous['file_size'] / 1024:.1f}KB → {latest['file_size'] / 1024:.1f}KB ({comparison['structural_changes']['file_size_change'] / 1024:+.1f}KB)
• Time Between Updates: {comparison['temporal_changes']['days_between_versions']} days

"""

        # Add content changes if significant
        if comparison['content_changes']['total_added'] > 0:
            response += f"• New Content Keywords: {', '.join(comparison['content_changes']['added_keywords'][:8])}\n"
        
        if comparison['content_changes']['total_removed'] > 0:
            response += f"• Removed Content Keywords: {', '.join(comparison['content_changes']['removed_keywords'][:8])}\n"
        
        return response
    
    def _get_version_overview(self) -> str:
        """Get overview of all document versions"""
        if not self.document_versions:
            return "No documents available."
        
        total_docs = sum(len(info['all_versions']) for info in self.document_versions.values())
        multi_version_count = sum(1 for info in self.document_versions.values() if info['is_multiple_versions'])
        
        response = f"""**Document Version Overview**

📊 **Summary:**
• Total Documents: {total_docs}
• Document Groups: {len(self.document_versions)}
• Groups with Multiple Versions: {multi_version_count}

**Latest Versions in Use:**
"""
        
        for group_key, version_info in self.document_versions.items():
            latest = version_info['latest']
            status = "🔄 Multiple versions" if version_info['is_multiple_versions'] else "✅ Single version"
            response += f"• **{latest.get('title', 'Unknown')}**: {latest['filename']} ({status})\n"
        
        if multi_version_count > 0:
            response += "\n💡 *Ask about specific documents to see version differences*"
        
        return response

    def get_version_context(self) -> str:
        """Get context about document versions being used"""
        if not self.document_versions:
            return "Using default HR content (no documents found)"
        
        latest_files = [info['latest']['filename'] for info in self.document_versions.values()]
        version_count = sum(1 for info in self.document_versions.values() if info['is_multiple_versions'])
        
        return f"Using {len(latest_files)} latest document versions ({version_count} with multiple versions available)"

    def is_initialized(self) -> bool:
        """Check if vector store is initialized and ready"""
        return self._initialized

    def get_status(self) -> dict:
        """Get current status of document processor"""
        version_info = {
            "document_groups": len(self.document_versions) if self.document_versions else 0,
            "multiple_versions": sum(1 for info in self.document_versions.values() if info['is_multiple_versions']) if self.document_versions else 0,
            "total_versions": sum(len(info['all_versions']) for info in self.document_versions.values()) if self.document_versions else 0,
        }
        
        return {
            "initialized": self._initialized,
            "documents_loaded": len(self.documents) if self._initialized else 0,
            "vector_store_ready": self.vector_store is not None,
            "version_management": version_info
        }