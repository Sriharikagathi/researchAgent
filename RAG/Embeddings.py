from typing import List
from langchain_openai import OpenAIEmbeddings
from Config.Settings import settings
from shared.state import SharedState, LogType
import os


class EmbeddingGenerator:
    '''Handle embedding generation for documents.'''
    
    def __init__(self, shared_state: SharedState):
        '''
        Initialize embedding generator.
        
        Args:
            shared_state: Shared state instance
        '''
        self.shared_state = shared_state
        os.environ['OPENAI_API_KEY'] = settings.openai_api_key
        
        # Ensure API key is in environment
        # if not os.environ.get('OPENAI_API_KEY'):
        #     os.environ['OPENAI_API_KEY'] = settings.openai_api_key
        
        try:
            # Initialize without passing api_key directly
            self.embeddings = OpenAIEmbeddings(
                model=settings.embedding_model
            )
            
            self.shared_state.add_log(
                f"[RAG] Initialized embeddings model: {settings.embedding_model}",
                LogType.RAG
            )
        except Exception as e:
            self.shared_state.add_log(
                f"[RAG] Error initializing embeddings: {str(e)}",
                LogType.ERROR
            )
            raise
    
    def embed_query(self, query: str) -> List[float]:
        '''
        Generate embedding for a query.
        
        Args:
            query: Query text
            
        Returns:
            Embedding vector
        '''
        self.shared_state.add_log(
            "[RAG] Generating embedding for query",
            LogType.RAG
        )
        
        try:
            return self.embeddings.embed_query(query)
        except Exception as e:
            self.shared_state.add_log(
                f"[RAG] Error generating query embedding: {str(e)}",
                LogType.ERROR
            )
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        '''
        Generate embeddings for multiple documents.
        
        Args:
            texts: List of document texts
            
        Returns:
            List of embedding vectors
        '''
        self.shared_state.add_log(
            f"[RAG] Generating embeddings for {len(texts)} documents",
            LogType.RAG
        )
        
        try:
            return self.embeddings.embed_documents(texts)
        except Exception as e:
            self.shared_state.add_log(
                f"[RAG] Error generating document embeddings: {str(e)}",
                LogType.ERROR
            )
            raise
    
    def get_embeddings_instance(self):
        '''Get the embeddings instance for use in vector stores.'''
        return self.embeddings