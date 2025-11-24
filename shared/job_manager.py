"""
Job manager for background task execution with progress tracking.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field, asdict
import json
import threading


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class JobStage(Enum):
    """Stages in the research workflow."""
    INITIALIZATION = "initialization"
    DOCUMENT_RETRIEVAL = "document_retrieval"
    WEB_RESEARCH = "web_research"
    CITATION_VERIFICATION = "citation_verification"
    COMPLIANCE_CHECK = "compliance_check"
    REPORT_GENERATION = "report_generation"
    FINALIZATION = "finalization"


@dataclass
class JobProgress:
    """Job progress information."""
    current_stage: JobStage = JobStage.INITIALIZATION
    stages_completed: List[str] = field(default_factory=list)
    total_stages: int = 7
    completed_stages: int = 0
    percentage: float = 0.0
    current_operation: str = ""
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def update(self, stage: JobStage, operation: str = ""):
        """Update progress."""
        self.current_stage = stage
        self.current_operation = operation
        if stage.value not in self.stages_completed:
            self.stages_completed.append(stage.value)
            self.completed_stages = len(self.stages_completed)
        self.percentage = (self.completed_stages / self.total_stages) * 100
        self.last_updated = datetime.now().isoformat()


@dataclass
class Job:
    """Represents a background research job."""
    job_id: str
    query: str
    status: JobStatus = JobStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: JobProgress = field(default_factory=JobProgress)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    cancellation_requested: bool = False
    
    # Idempotency
    idempotency_key: Optional[str] = None
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        data['progress']['current_stage'] = self.progress.current_stage.value
        return data
    
    def add_execution_record(self, stage: str, success: bool, details: str = ""):
        """Add execution record for idempotency."""
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'stage': stage,
            'success': success,
            'details': details
        })


class JobManager:
    """Manages background jobs with async execution and tracking."""
    
    def __init__(self):
        """Initialize job manager."""
        self.jobs: Dict[str, Job] = {}
        self.lock = threading.Lock()
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        
    def create_job(
        self,
        query: str,
        idempotency_key: Optional[str] = None
    ) -> Job:
        """
        Create a new job.
        
        Args:
            query: Research query
            idempotency_key: Optional key for idempotent operations
            
        Returns:
            Created job
        """
        with self.lock:
            # Check for existing job with same idempotency key
            if idempotency_key:
                for job in self.jobs.values():
                    if job.idempotency_key == idempotency_key:
                        if job.status in [JobStatus.COMPLETED, JobStatus.RUNNING]:
                            return job  # Return existing job
            
            job_id = str(uuid.uuid4())
            job = Job(
                job_id=job_id,
                query=query,
                idempotency_key=idempotency_key
            )
            self.jobs[job_id] = job
            
            return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[Job]:
        """Get all jobs."""
        return list(self.jobs.values())
    
    def update_job_status(self, job_id: str, status: JobStatus):
        """Update job status."""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = status
                
                if status == JobStatus.RUNNING and not job.started_at:
                    job.started_at = datetime.now().isoformat()
                elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    job.completed_at = datetime.now().isoformat()
    
    def update_job_progress(
        self,
        job_id: str,
        stage: JobStage,
        operation: str = ""
    ):
        """Update job progress."""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.progress.update(stage, operation)
    
    def cancel_job(self, job_id: str) -> bool:
        """Request job cancellation."""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                if job.status == JobStatus.RUNNING:
                    job.cancellation_requested = True
                    return True
        return False
    
    def is_cancellation_requested(self, job_id: str) -> bool:
        """Check if cancellation is requested."""
        job = self.get_job(job_id)
        return job.cancellation_requested if job else False
    
    def mark_job_completed(
        self,
        job_id: str,
        result: Dict[str, Any]
    ):
        """Mark job as completed."""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = JobStatus.COMPLETED
                job.result = result
                job.completed_at = datetime.now().isoformat()
                job.progress.percentage = 100.0
    
    def mark_job_failed(
        self,
        job_id: str,
        error: str,
        allow_retry: bool = True
    ):
        """Mark job as failed."""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.error = error
                
                if allow_retry and job.retry_count < job.max_retries:
                    job.status = JobStatus.RETRY
                    job.retry_count += 1
                else:
                    job.status = JobStatus.FAILED
                    job.completed_at = datetime.now().isoformat()
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old completed/failed jobs."""
        with self.lock:
            current_time = datetime.now()
            jobs_to_remove = []
            
            for job_id, job in self.jobs.items():
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    if job.completed_at:
                        completed_time = datetime.fromisoformat(job.completed_at)
                        age_hours = (current_time - completed_time).total_seconds() / 3600
                        
                        if age_hours > max_age_hours:
                            jobs_to_remove.append(job_id)
            
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
            
            return len(jobs_to_remove)


# Global job manager instance
job_manager = JobManager()
