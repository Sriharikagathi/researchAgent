"""Document retrieval tool using RAG."""

from typing import Dict, Any
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from RAG.VectorStore import VectorStore
from shared.state import SharedState, LogType


class DocumentRetrievalInput(BaseModel):
    """Input schema for document retrieval tool."""
    query: str = Field(description="The search query for document retrieval")
    k: int = Field(default=5, description="Number of documents to retrieve")


def create_document_retrieval_tool(
    vector_store: VectorStore,
    shared_state: SharedState
) -> StructuredTool:
    """
    Create document retrieval tool.
    
    Args:
        vector_store: Vector store instance
        shared_state: Shared state instance
        
    Returns:
        StructuredTool for document retrieval
    """
    
    def retrieve_documents(query: str, k: int = 5) -> str:
        """
        Retrieve relevant documents from RAG system.
        
        Args:
            query: Search query
            k: Number of documents to retrieve
            
        Returns:
            JSON string with retrieved documents
        """
        shared_state.add_log(
            "[Tool: Document Retrieval] Starting document retrieval",
            LogType.TOOL,
            metadata={"query": query[:100], "k": k}
        )
        
        try:
            # Perform similarity search
            documents = vector_store.similarity_search(query, k=k)
            
            if not documents:
                shared_state.add_log(
                    "[Tool: Document Retrieval] No documents found",
                    LogType.WARNING
                )
                return str({
                    'success': False,
                    'message': 'No relevant documents found',
                    'document_count': 0
                })
            
            # Format results
            result_docs = []
            for idx, doc in enumerate(documents):
                result_docs.append({
                    'rank': idx + 1,
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'length': len(doc.page_content)
                })
            
            result = {
                'success': True,
                'document_count': len(documents),
                'documents': result_docs
            }
            
            shared_state.add_log(
                f"[Tool: Document Retrieval] Retrieved {len(documents)} documents",
                LogType.SUCCESS
            )
            
            return str(result)
            
        except Exception as e:
            shared_state.add_log(
                f"[Tool: Document Retrieval] Error: {str(e)}",
                LogType.ERROR
            )
            return str({
                'success': False,
                'error': str(e),
                'document_count': 0
            })
    
    return StructuredTool.from_function(
        func=retrieve_documents,
        name="document_retrieval",
        description="Retrieve relevant documents from the RAG vector database based on semantic similarity to the query. Use this tool to find information from ingested documents.",
        args_schema=DocumentRetrievalInput
    )