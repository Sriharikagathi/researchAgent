"""Vector store operations using PGVector."""

from typing import List, Optional
from langchain_core.documents import Document
from langchain_postgres import PGVector
from RAG.Embeddings import EmbeddingGenerator
from shared.state import SharedState, LogType
from Config.Settings import settings


class VectorStore:
    """Manage PGVector operations for document storage and retrieval."""
    
    def __init__(self, shared_state: SharedState):
        """
        Initialize vector store.
        
        Args:
            shared_state: Shared state instance
        """
        self.shared_state = shared_state
        self.embedding_generator = EmbeddingGenerator(shared_state)
        self.connection_string = settings.database_url
        self.collection_name = settings.collection_name
        
        self.shared_state.add_log(
            f"[RAG] Initializing PGVector store: {self.collection_name}",
            LogType.RAG
        )
        
        self.vector_store = self._initialize_vector_store()
    
    def _initialize_vector_store(self) -> PGVector:
        """
        Initialize or connect to existing vector store.
        
        Returns:
            PGVector instance
        """
        try:
            vector_store = PGVector(
                connection=self.connection_string,
                embeddings=self.embedding_generator.get_embeddings_instance(),
                collection_name=self.collection_name,
                use_jsonb=True
            )
            
            self.shared_state.add_log(
                "[RAG] Successfully connected to PGVector store",
                LogType.SUCCESS
            )
            
            return vector_store
            
        except Exception as e:
            self.shared_state.add_log(
                f"[RAG] Error initializing vector store: {str(e)}",
                LogType.ERROR
            )
            raise
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        Add documents to vector store.
        
        Args:
            documents: List of documents to add
            
        Returns:
            List of document IDs
        """
        self.shared_state.add_log(
            f"[RAG] Adding {len(documents)} documents to vector store",
            LogType.RAG
        )
        
        try:
            ids = self.vector_store.add_documents(documents)
            
            self.shared_state.add_log(
                f"[RAG] Successfully added {len(ids)} documents",
                LogType.SUCCESS,
                metadata={"document_ids": ids[:5]}  # Log first 5 IDs
            )
            
            return ids
            
        except Exception as e:
            self.shared_state.add_log(
                f"[RAG] Error adding documents: {str(e)}",
                LogType.ERROR
            )
            raise
    
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[dict] = None
    ) -> List[Document]:
        """
        Perform similarity search.
        
        Args:
            query: Search query
            k: Number of results to return
            filter_dict: Optional metadata filter
            
        Returns:
            List of relevant documents
        """
        self.shared_state.add_log(
            f"[RAG] Performing similarity search (k={k})",
            LogType.RAG,
            metadata={"query": query[:100]}
        )
        
        try:
            results = self.vector_store.similarity_search(
                query=query,
                k=k,
                filter=filter_dict
            )
            
            self.shared_state.add_log(
                f"[RAG] Found {len(results)} relevant documents",
                LogType.SUCCESS
            )
            
            # Store in shared state
            self.shared_state.retrieved_documents = [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_rank": idx + 1
                }
                for idx, doc in enumerate(results)
            ]
            self.shared_state.document_count = len(results)
            
            return results
            
        except Exception as e:
            self.shared_state.add_log(
                f"[RAG] Error in similarity search: {str(e)}",
                LogType.ERROR
            )
            return []
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5
    ) -> List[tuple[Document, float]]:
        """
        Perform similarity search with relevance scores.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of (document, score) tuples
        """
        self.shared_state.add_log(
            f"[RAG] Performing similarity search with scores (k={k})",
            LogType.RAG
        )
        
        try:
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k
            )
            
            self.shared_state.add_log(
                f"[RAG] Found {len(results)} documents with scores",
                LogType.SUCCESS,
                metadata={"scores": [score for _, score in results]}
            )
            
            return results
            
        except Exception as e:
            self.shared_state.add_log(
                f"[RAG] Error in similarity search with score: {str(e)}",
                LogType.ERROR
            )
            return []
    
    def delete_collection(self):
        """Delete the entire collection."""
        self.shared_state.add_log(
            f"[RAG] Deleting collection: {self.collection_name}",
            LogType.WARNING
        )
        
        try:
            self.vector_store.delete_collection()
            
            self.shared_state.add_log(
                "[RAG] Collection deleted successfully",
                LogType.SUCCESS
            )
            
        except Exception as e:
            self.shared_state.add_log(
                f"[RAG] Error deleting collection: {str(e)}",
                LogType.ERROR
            )
    
    def get_retriever(self, search_kwargs: Optional[dict] = None):
        """
        Get a retriever instance for use with chains.
        
        Args:
            search_kwargs: Optional search parameters
            
        Returns:
            VectorStoreRetriever instance
        """
        if search_kwargs is None:
            search_kwargs = {"k": 5}
        
        return self.vector_store.as_retriever(search_kwargs=search_kwargs)