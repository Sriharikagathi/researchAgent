"""
FastAPI endpoints for job management - FIXED VERSION
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
import asyncio
import traceback

from shared.job_manager import job_manager, JobStatus
from Agent.background_executor import background_executor


router = APIRouter(prefix="/jobs", tags=["jobs"])


class CreateJobRequest(BaseModel):
    """Request to create a job."""
    query: str = Field(..., description="Research query")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key")


class JobResponse(BaseModel):
    """Job response model."""
    job_id: str
    query: str
    status: str
    created_at: str
    progress: dict
    result: Optional[dict] = None
    error: Optional[str] = None


@router.post("/", response_model=JobResponse)
async def create_job(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a new research job.
    
    - **query**: The research query to execute
    - **idempotency_key**: Optional key to prevent duplicate job creation
    """
    try:
        # Create job
        job = job_manager.create_job(
            query=request.query,
            idempotency_key=request.idempotency_key
        )
        
        # If job is new or pending, start execution
        if job.status in [JobStatus.PENDING, JobStatus.RETRY]:
            # Add to background tasks
            background_tasks.add_task(
                execute_job_wrapper,
                job.job_id
            )
        
        return JobResponse(**job.to_dict())
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """
    Get job status and result.
    
    - **job_id**: The job ID
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse(**job.to_dict())


@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 100
):
    """
    List all jobs with optional filtering.
    
    - **status**: Filter by status (pending, running, completed, failed, cancelled)
    - **limit**: Maximum number of jobs to return
    """
    jobs = job_manager.get_all_jobs()
    
    if status:
        jobs = [j for j in jobs if j.status.value == status]
    
    jobs = jobs[:limit]
    
    return [JobResponse(**job.to_dict()) for job in jobs]


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a running job.
    
    - **job_id**: The job ID to cancel
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status.value}"
        )
    
    success = job_manager.cancel_job(job_id)
    
    if success:
        return {"message": "Cancellation requested", "job_id": job_id}
    else:
        raise HTTPException(status_code=400, detail="Failed to cancel job")


@router.post("/{job_id}/retry")
async def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks
):
    """
    Retry a failed job.
    
    - **job_id**: The job ID to retry
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in [JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry job with status: {job.status.value}"
        )
    
    # Reset job status
    job_manager.update_job_status(job_id, JobStatus.PENDING)
    job.error = None  # Clear previous error
    
    # Start execution
    background_tasks.add_task(execute_job_wrapper, job_id)
    
    return {"message": "Job retry initiated", "job_id": job_id}


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a completed or failed job.
    
    - **job_id**: The job ID to delete
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status == JobStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete running job. Cancel it first."
        )
    
    del job_manager.jobs[job_id]
    
    return {"message": "Job deleted", "job_id": job_id}


@router.post("/{job_id}/logs")
async def get_job_logs(job_id: str):
    """
    Get execution logs for a job.
    
    - **job_id**: The job ID
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job_id,
        "execution_history": job.execution_history
    }


def execute_job_wrapper(job_id: str):
    """
    Wrapper to execute job in background.
    Handles the async execution properly.
    """
    try:
        # Create new event loop for background task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the job
        result = loop.run_until_complete(
            background_executor.execute_job(job_id)
        )
        
        loop.close()
        
        return result
        
    except Exception as e:
        # Mark job as failed
        error_msg = f"{type(e).__name__}: {str(e)}"
        job_manager.mark_job_failed(job_id, error_msg, allow_retry=True)
        
        # Log full traceback
        print(f"\n{'='*80}")
        print(f"JOB {job_id} FAILED")
        print(f"{'='*80}")
        print(f"Error: {error_msg}")
        print(f"\nFull traceback:")
        traceback.print_exc()
        print(f"{'='*80}\n")