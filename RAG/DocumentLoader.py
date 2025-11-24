"""Document loading and processing module."""

import asyncio
from pathlib import Path
from typing import List, Optional
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from shared.state import SharedState,LogType
from Config.Settings import settings


class DocumentLoader:
    """Handle document loading and chunking."""
    
    def __init__(self, shared_state: SharedState):
        """
        Initialize document loader.
        
        Args:
            shared_state: Shared state instance
        """
        self.shared_state = shared_state
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
    
    async def load_pdf(self, file_path: str) -> List[Document]:
        """
        Load PDF document asynchronously.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of Document objects
        """
        self.shared_state.add_log(
            f"[RAG] Loading PDF: {file_path}",
            LogType.RAG
        )
        
        loader = PyPDFLoader(
            file_path=file_path,
            extract_images=True
        )
        
        docs = await loader.aload()
        
        self.shared_state.add_log(
            f"[RAG] Loaded {len(docs)} pages from PDF",
            LogType.RAG
        )
        
        return docs
    
    def load_text(self, file_path: str) -> List[Document]:
        """
        Load text document.
        
        Args:
            file_path: Path to text file
            
        Returns:
            List of Document objects
        """
        self.shared_state.add_log(
            f"[RAG] Loading text file: {file_path}",
            LogType.RAG
        )
        
        loader = TextLoader(file_path, encoding='utf-8')
        docs = loader.load()
        
        self.shared_state.add_log(
            f"[RAG] Loaded text document",
            LogType.RAG
        )
        
        return docs
    
    def load_docx(self, file_path: str) -> List[Document]:
        """
        Load DOCX document.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            List of Document objects
        """
        self.shared_state.add_log(
            f"[RAG] Loading DOCX: {file_path}",
            LogType.RAG
        )
        
        loader = Docx2txtLoader(file_path)
        docs = loader.load()
        
        self.shared_state.add_log(
            f"[RAG] Loaded DOCX document",
            LogType.RAG
        )
        
        return docs
    
    async def load_document(self, file_path: str) -> List[Document]:
        """
        Load document based on file type.
        
        Args:
            file_path: Path to document
            
        Returns:
            List of Document objects
        """
        file_ext = Path(file_path).suffix.lower()
        
        try:
            if file_ext == '.pdf':
                return await self.load_pdf(file_path)
            elif file_ext == '.txt':
                return self.load_text(file_path)
            elif file_ext == '.docx':
                return self.load_docx(file_path)
            else:
                self.shared_state.add_log(
                    f"[RAG] Unsupported file type: {file_ext}",
                    LogType.WARNING
                )
                return []
        except Exception as e:
            self.shared_state.add_log(
                f"[RAG] Error loading {file_path}: {str(e)}",
                LogType.ERROR
            )
            return []
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks.
        
        Args:
            documents: List of documents to split
            
        Returns:
            List of chunked documents
        """
        self.shared_state.add_log(
            f"[RAG] Splitting {len(documents)} documents into chunks",
            LogType.RAG
        )
        
        chunks = self.text_splitter.split_documents(documents)
        
        self.shared_state.add_log(
            f"[RAG] Created {len(chunks)} chunks",
            LogType.RAG
        )
        
        return chunks
    
    def clean_documents(self, documents: List[Document]) -> List[Document]:
        """
        Clean documents by removing null bytes and invalid characters.
        
        Args:
            documents: Documents to clean
            
        Returns:
            Cleaned documents
        """
        self.shared_state.add_log(
            "[RAG] Cleaning documents",
            LogType.RAG
        )
        
        cleaned = [
            Document(
                page_content=doc.page_content.replace('\x00', ''),
                metadata=doc.metadata
            )
            for doc in documents
        ]
        
        return cleaned
    
    async def load_and_process(self, file_path: str) -> List[Document]:
        """
        Complete pipeline: load, split, and clean document.
        
        Args:
            file_path: Path to document
            
        Returns:
            Processed document chunks
        """
        # Load
        documents = await self.load_document(file_path)
        
        if not documents:
            return []
        
        # Split
        chunks = self.split_documents(documents)
        
        # Clean
        cleaned_chunks = self.clean_documents(chunks)
        
        # Update state
        self.shared_state.ingested_documents.append(file_path)
        self.shared_state.total_chunks += len(cleaned_chunks)
        
        self.shared_state.add_log(
            f"[RAG] Processed {file_path}: {len(cleaned_chunks)} chunks ready",
            LogType.SUCCESS
        )
        
        return cleaned_chunks
    
    async def load_directory(self, directory_path: str) -> List[Document]:
        """
        Load all supported documents from a directory.
        
        Args:
            directory_path: Path to directory
            
        Returns:
            All processed document chunks
        """
        self.shared_state.add_log(
            f"[RAG] Loading documents from directory: {directory_path}",
            LogType.RAG
        )
        
        directory = Path(directory_path)
        
        if not directory.exists():
            self.shared_state.add_log(
                f"[RAG] Directory not found: {directory_path}",
                LogType.ERROR
            )
            return []
        
        all_chunks = []
        supported_extensions = ['.pdf', '.txt', '.docx']
        
        for file_path in directory.rglob('*'):
            if file_path.suffix.lower() in supported_extensions:
                chunks = await self.load_and_process(str(file_path))
                all_chunks.extend(chunks)
        
        self.shared_state.add_log(
            f"[RAG] Loaded {len(all_chunks)} total chunks from directory",
            LogType.SUCCESS
        )
        
        return all_chunks