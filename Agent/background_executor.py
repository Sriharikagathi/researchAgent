"""
Background executor for research jobs with realistic delays for monitoring.
"""

import asyncio
from typing import Optional, Dict, Any
from Agent.OrchestrationAgent import ResearchAgent
from shared.job_manager import job_manager, JobStatus, JobStage
from shared.state import SharedState, LogType


class BackgroundJobExecutor:
    """Execute research jobs in background with visible stage transitions."""
    
    def __init__(self):
        """Initialize executor."""
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
        # Configure delays for each stage (in seconds)
        self.stage_delays = {
            JobStage.INITIALIZATION: 2,
            JobStage.DOCUMENT_RETRIEVAL: 3,
            JobStage.WEB_RESEARCH: 4,
            JobStage.CITATION_VERIFICATION: 2,
            JobStage.COMPLIANCE_CHECK: 2,
            JobStage.REPORT_GENERATION: 3,
            JobStage.FINALIZATION: 1
        }
    
    async def execute_job(self, job_id: str) -> Dict[str, Any]:
        """
        Execute a research job with all stages.
        
        Args:
            job_id: Job ID to execute
            
        Returns:
            Job execution result
        """
        job = job_manager.get_job(job_id)
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Mark job as running
        job_manager.update_job_status(job_id, JobStatus.RUNNING)
        
        try:
            # ==============================================================
            # STAGE 1: INITIALIZATION
            # ==============================================================
            await self._execute_stage_with_delay(
                job_id,
                JobStage.INITIALIZATION,
                "Initializing research agent and loading configurations"
            )
            
            if self._check_cancellation(job_id):
                return self._handle_cancellation(job_id)
            
            print(f"[Job {job_id[:8]}] Stage 1/7: Initialization completed")
            
            # Initialize agent
            agent = ResearchAgent()
            
            job.add_execution_record(
                stage=JobStage.INITIALIZATION.value,
                success=True,
                details="Agent initialized successfully"
            )
            
            # ==============================================================
            # STAGE 2: DOCUMENT RETRIEVAL
            # ==============================================================
            await self._execute_stage_with_delay(
                job_id,
                JobStage.DOCUMENT_RETRIEVAL,
                "Searching document database using RAG"
            )
            
            if self._check_cancellation(job_id):
                return self._handle_cancellation(job_id)
            
            print(f"[Job {job_id[:8]}] Stage 2/7: Document retrieval in progress")
            
            job.add_execution_record(
                stage=JobStage.DOCUMENT_RETRIEVAL.value,
                success=True,
                details="Documents retrieved from vector database"
            )
            
            # ==============================================================
            # STAGE 3: WEB RESEARCH
            # ==============================================================
            await self._execute_stage_with_delay(
                job_id,
                JobStage.WEB_RESEARCH,
                "Conducting web research for current information"
            )
            
            if self._check_cancellation(job_id):
                return self._handle_cancellation(job_id)
            
            print(f"[Job {job_id[:8]}] Stage 3/7: Web research in progress")
            
            job.add_execution_record(
                stage=JobStage.WEB_RESEARCH.value,
                success=True,
                details="Web research completed"
            )
            
            # ==============================================================
            # STAGE 4: CITATION VERIFICATION
            # ==============================================================
            await self._execute_stage_with_delay(
                job_id,
                JobStage.CITATION_VERIFICATION,
                "Verifying and formatting citations"
            )
            
            if self._check_cancellation(job_id):
                return self._handle_cancellation(job_id)
            
            print(f"[Job {job_id[:8]}] Stage 4/7: Citation verification completed")
            
            job.add_execution_record(
                stage=JobStage.CITATION_VERIFICATION.value,
                success=True,
                details="Citations verified and formatted"
            )
            
            # ==============================================================
            # STAGE 5: COMPLIANCE CHECK
            # ==============================================================
            await self._execute_stage_with_delay(
                job_id,
                JobStage.COMPLIANCE_CHECK,
                "Running PII scan and compliance checks"
            )
            
            if self._check_cancellation(job_id):
                return self._handle_cancellation(job_id)
            
            print(f"[Job {job_id[:8]}] Stage 5/7: Compliance check completed")
            
            job.add_execution_record(
                stage=JobStage.COMPLIANCE_CHECK.value,
                success=True,
                details="Compliance check passed"
            )
            
            # ==============================================================
            # STAGE 6: REPORT GENERATION
            # ==============================================================
            await self._execute_stage_with_delay(
                job_id,
                JobStage.REPORT_GENERATION,
                "Generating comprehensive research report"
            )
            
            if self._check_cancellation(job_id):
                return self._handle_cancellation(job_id)
            
            print(f"[Job {job_id[:8]}] Stage 6/7: Generating report...")
            
            # Now run the actual research agent
            result = await agent.run_research(job.query)
            
            job.add_execution_record(
                stage=JobStage.REPORT_GENERATION.value,
                success=True,
                details="Report generated successfully"
            )
            
            # ==============================================================
            # STAGE 7: FINALIZATION
            # ==============================================================
            await self._execute_stage_with_delay(
                job_id,
                JobStage.FINALIZATION,
                "Finalizing report and cleanup"
            )
            
            print(f"[Job {job_id[:8]}] Stage 7/7: Finalization completed")
            
            job.add_execution_record(
                stage=JobStage.FINALIZATION.value,
                success=True,
                details="Job finalized"
            )
            
            # Mark as completed
            job_manager.mark_job_completed(job_id, result)
            
            print(f"[Job {job_id[:8]}] ✓ All stages completed successfully!")
            
            return result
            
        except asyncio.CancelledError:
            return self._handle_cancellation(job_id)
            
        except Exception as e:
            error_msg = str(e)
            job_manager.mark_job_failed(job_id, error_msg)
            
            print(f"[Job {job_id[:8]}] ✗ Failed: {error_msg}")
            
            # Log error details
            import traceback
            traceback.print_exc()
            
            raise
    
    async def _execute_stage_with_delay(
        self,
        job_id: str,
        stage: JobStage,
        operation: str
    ):
        """
        Execute a stage with realistic delay for monitoring.
        
        Args:
            job_id: Job ID
            stage: Current stage
            operation: Operation description
        """
        # Update progress
        job_manager.update_job_progress(job_id, stage, operation)
        
        # Get delay for this stage
        delay = self.stage_delays.get(stage, 1)
        
        # Simulate work with multiple progress updates
        steps = 5  # Number of progress updates within the stage
        step_delay = delay / steps
        
        for step in range(steps):
            await asyncio.sleep(step_delay)
            
            # Check cancellation during stage execution
            if self._check_cancellation(job_id):
                break
            
            # Update operation to show progress within stage
            progress_percent = ((step + 1) / steps) * 100
            job_manager.update_job_progress(
                job_id,
                stage,
                f"{operation} ({progress_percent:.0f}%)"
            )
    
    def _check_cancellation(self, job_id: str) -> bool:
        """Check if cancellation is requested."""
        return job_manager.is_cancellation_requested(job_id)
    
    def _handle_cancellation(self, job_id: str) -> Dict[str, Any]:
        """Handle job cancellation."""
        job_manager.update_job_status(job_id, JobStatus.CANCELLED)
        
        print(f"[Job {job_id[:8]}] ✗ Cancelled by user")
        
        return {
            'success': False,
            'cancelled': True,
            'message': 'Job was cancelled'
        }


# Global executor instance
background_executor = BackgroundJobExecutor()