"""Shared state management for the research agent."""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging


class JobStatus(Enum):
    """Job execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class LogType(Enum):
    """Log entry types."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    TOOL = "tool"
    AGENT = "agent"
    MCP = "mcp"
    STATUS = "status"
    RAG = "rag"


@dataclass
class SharedState:
    """
    Shared state across all tools and components.
    Provides centralized state management with logging and compliance tracking.
    """
    
    # Session info
    query: str = ""
    status: JobStatus = JobStatus.IDLE
    session_id: str = ""
    
    # Logs
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    # RAG state
    ingested_documents: List[str] = field(default_factory=list)
    retrieved_documents: List[Dict[str, Any]] = field(default_factory=list)
    document_count: int = 0
    total_chunks: int = 0
    
    # Web research state
    web_results: List[Dict[str, Any]] = field(default_factory=list)
    web_sources: List[str] = field(default_factory=list)
    
    # Citation state
    verified_citations: List[Dict[str, Any]] = field(default_factory=list)
    citation_count: int = 0
    
    # Compliance state
    pii_found: List[Dict[str, Any]] = field(default_factory=list)
    pii_redacted_count: int = 0
    compliance_report: Optional[Dict[str, Any]] = None
    
    # Output state
    final_report: str = ""
    formatted_output: str = ""
    export_path: str = ""
    
    # Configuration
    audit_log_path: str = "./audit_logs"
    
    def __post_init__(self):
        """Initialize session ID if not provided."""
        if not self.session_id:
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def add_log(
        self,
        message: str,
        log_type: LogType = LogType.INFO,
        metadata: Optional[Dict] = None
    ):
        """
        Add a timestamped log entry.
        
        Args:
            message: Log message
            log_type: Type of log entry
            metadata: Additional metadata
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": log_type.value,
            "message": message,
            "metadata": metadata or {},
            "session_id": self.session_id
        }
        
        self.logs.append(log_entry)
        
        # Console logging
        log_level = getattr(logging, log_type.value.upper(), logging.INFO)
        logging.log(log_level, f"[{log_type.value.upper()}] {message}")
        
        # Write to audit file
        self._write_audit_log(log_entry)
    
    def _write_audit_log(self, log_entry: Dict):
        """Write log entry to persistent audit file."""
        os.makedirs(self.audit_log_path, exist_ok=True)
        log_file = os.path.join(
            self.audit_log_path,
            f"session_{self.session_id}.jsonl"
        )
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logging.error(f"Failed to write audit log: {e}")
    
    def update_status(self, new_status: JobStatus, message: str = ""):
        """
        Update job status with logging.
        
        Args:
            new_status: New job status
            message: Optional status message
        """
        self.status = new_status
        status_msg = f"Status changed to: {new_status.value}"
        if message:
            status_msg += f" - {message}"
        
        self.add_log(status_msg, LogType.STATUS)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get current state summary.
        
        Returns:
            Dictionary containing state summary
        """
        return {
            "session_id": self.session_id,
            "query": self.query,
            "status": self.status.value,
            "ingested_documents": len(self.ingested_documents),
            "total_chunks": self.total_chunks,
            "retrieved_documents": self.document_count,
            "web_sources": len(self.web_sources),
            "citations_verified": self.citation_count,
            "pii_redacted": self.pii_redacted_count,
            "total_logs": len(self.logs),
            "export_path": self.export_path
        }
    
    def get_recent_logs(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent log entries.
        
        Args:
            count: Number of recent logs to return
            
        Returns:
            List of recent log entries
        """
        return self.logs[-count:]
    
    def clear_state(self):
        """Clear all state except session_id and audit_log_path."""
        self.query = ""
        self.status = JobStatus.IDLE
        self.logs = []
        self.ingested_documents = []
        self.retrieved_documents = []
        self.document_count = 0
        self.total_chunks = 0
        self.web_results = []
        self.web_sources = []
        self.verified_citations = []
        self.citation_count = 0
        self.pii_found = []
        self.pii_redacted_count = 0
        self.compliance_report = None
        self.final_report = ""
        self.formatted_output = ""
        self.export_path = ""
        
        self.add_log("State cleared", LogType.INFO)