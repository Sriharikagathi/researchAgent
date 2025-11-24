"""
Real-time job monitoring tool with live updates.
Run this to watch a job's progress in real-time.
"""

import requests
import time
import sys
from datetime import datetime
import os


BASE_URL = "http://localhost:8000"


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def get_progress_bar(percentage: float, width: int = 50) -> str:
    """Create a visual progress bar."""
    filled = int(width * percentage / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {percentage:.1f}%"


def get_stage_indicator(stages_completed: list, current_stage: str) -> str:
    """Create visual stage indicator."""
    all_stages = [
        'initialization',
        'document_retrieval',
        'web_research',
        'citation_verification',
        'compliance_check',
        'report_generation',
        'finalization'
    ]
    
    stage_symbols = []
    for stage in all_stages:
        if stage in stages_completed:
            stage_symbols.append('✓')
        elif stage == current_stage:
            stage_symbols.append('▶')
        else:
            stage_symbols.append('○')
    
    return ' '.join(stage_symbols)


def get_stage_name(stage: str) -> str:
    """Get human-readable stage name."""
    names = {
        'initialization': 'Initialization',
        'document_retrieval': 'Document Retrieval',
        'web_research': 'Web Research',
        'citation_verification': 'Citation Verification',
        'compliance_check': 'Compliance Check',
        'report_generation': 'Report Generation',
        'finalization': 'Finalization'
    }
    return names.get(stage, stage)


def format_time(seconds: float) -> str:
    """Format elapsed time."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    else:
        mins = int(seconds / 60)
        secs = seconds % 60
        return f"{mins}m {secs:.1f}s"


def monitor_job(job_id: str, refresh_rate: float = 0.5):
    """
    Monitor a job with live updates.
    
    Args:
        job_id: Job ID to monitor
        refresh_rate: Update interval in seconds
    """
    start_time = time.time()
    iteration = 0
    
    print(f"Starting real-time monitoring for job: {job_id}")
    print(f"Press Ctrl+C to stop monitoring\n")
    time.sleep(1)
    
    try:
        while True:
            iteration += 1
            elapsed = time.time() - start_time
            
            # Fetch job status
            try:
                response = requests.get(f"{BASE_URL}/jobs/{job_id}", timeout=5)
                
                if response.status_code != 200:
                    print(f"\n✗ Error fetching job: {response.status_code}")
                    break
                
                job = response.json()
                
            except requests.exceptions.RequestException as e:
                print(f"\n✗ Connection error: {e}")
                time.sleep(2)
                continue
            
            # Clear and redraw
            clear_screen()
            
            # Header
            print("=" * 80)
            print(f"  JOB MONITOR - Real-time Status Updates")
            print("=" * 80)
            print()
            
            # Job Info
            print(f"Job ID:     {job['job_id']}")
            print(f"Query:      {job['query']}")
            print(f"Status:     {job['status'].upper()}")
            print(f"Elapsed:    {format_time(elapsed)}")
            print(f"Updates:    {iteration}")
            print()
            
            # Progress
            progress = job['progress']
            percentage = progress['percentage']
            current_stage = progress['current_stage']
            stages_completed = progress['stages_completed']
            current_operation = progress['current_operation']
            
            print("─" * 80)
            print("PROGRESS")
            print("─" * 80)
            print()
            print(get_progress_bar(percentage, 60))
            print()
            print(f"Stage: {progress['completed_stages']}/{progress['total_stages']}")
            print()
            
            # Stage visualization
            print("STAGES:")
            print()
            print(get_stage_indicator(stages_completed, current_stage))
            print()
            stage_names = [
                'Init', 'Docs', 'Web', 'Cite', 'Comp', 'Report', 'Final'
            ]
            print(' '.join(f"{name:^5s}" for name in stage_names))
            print()
            
            # Current stage details
            print("─" * 80)
            print(f"CURRENT: {get_stage_name(current_stage)}")
            print("─" * 80)
            print()
            if current_operation:
                print(f"  {current_operation}")
            print()
            
            # Status-specific info
            if job['status'] == 'completed':
                print("─" * 80)
                print("✓ JOB COMPLETED SUCCESSFULLY")
                print("─" * 80)
                print()
                
                if job.get('result'):
                    result = job['result']
                    if result.get('summary'):
                        summary = result['summary']
                        print("Summary:")
                        print(f"  Documents Retrieved: {summary.get('retrieved_documents', 0)}")
                        print(f"  Web Sources: {summary.get('web_sources', 0)}")
                        print(f"  Citations: {summary.get('citations_verified', 0)}")
                        print(f"  PII Redacted: {summary.get('pii_redacted', 0)}")
                
                print()
                print("Press Ctrl+C to exit")
                
                # Don't exit automatically, let user see results
                time.sleep(refresh_rate)
                continue
            
            elif job['status'] == 'failed':
                print("─" * 80)
                print("✗ JOB FAILED")
                print("─" * 80)
                print()
                print(f"Error: {job.get('error', 'Unknown error')}")
                print()
                print("Press Ctrl+C to exit")
                time.sleep(refresh_rate)
                continue
            
            elif job['status'] == 'cancelled':
                print("─" * 80)
                print("✗ JOB CANCELLED")
                print("─" * 80)
                print()
                print("Press Ctrl+C to exit")
                time.sleep(refresh_rate)
                continue
            
            # Footer
            print("─" * 80)
            print(f"Monitoring... (refresh every {refresh_rate}s)")
            print("Press Ctrl+C to stop monitoring")
            
            # Wait before next update
            time.sleep(refresh_rate)
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("  Monitoring stopped by user")
        print("=" * 80)
        print()
        
        # Final status
        try:
            response = requests.get(f"{BASE_URL}/jobs/{job_id}")
            if response.status_code == 200:
                job = response.json()
                print(f"Final Status: {job['status'].upper()}")
                print(f"Progress: {job['progress']['percentage']:.1f}%")
        except:
            pass
        
        print()


def create_and_monitor(query: str, idempotency_key: str = None):
    """Create a job and start monitoring it."""
    print("=" * 80)
    print("  CREATE AND MONITOR JOB")
    print("=" * 80)
    print()
    print(f"Query: {query}")
    print()
    
    # Create job
    try:
        response = requests.post(
            f"{BASE_URL}/jobs/",
            json={
                "query": query,
                "idempotency_key": idempotency_key
            }
        )
        
        if response.status_code != 200:
            print(f"✗ Failed to create job: {response.status_code}")
            print(response.text)
            return
        
        job = response.json()
        job_id = job['job_id']
        
        print(f"✓ Job created: {job_id}")
        print()
        print("Starting monitor in 2 seconds...")
        time.sleep(2)
        
        # Start monitoring
        monitor_job(job_id)
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Connection error: {e}")
        print("\nMake sure the API server is running:")
        print("  python run_api.py")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor research jobs in real-time")
    
    parser.add_argument(
        '--job-id',
        type=str,
        help='Monitor existing job by ID'
    )
    
    parser.add_argument(
        '--create',
        type=str,
        help='Create new job with this query and monitor it'
    )
    
    parser.add_argument(
        '--refresh',
        type=float,
        default=0.5,
        help='Refresh rate in seconds (default: 0.5)'
    )
    
    parser.add_argument(
        '--key',
        type=str,
        help='Idempotency key for new job'
    )
    
    args = parser.parse_args()
    
    if args.job_id:
        # Monitor existing job
        monitor_job(args.job_id, args.refresh)
    
    elif args.create:
        # Create and monitor new job
        create_and_monitor(args.create, args.key)
    
    else:
        # Interactive mode
        print("=" * 80)
        print("  JOB MONITOR - Interactive Mode")
        print("=" * 80)
        print()
        print("Options:")
        print("  1. Monitor existing job")
        print("  2. Create new job and monitor")
        print("  3. Exit")
        print()
        
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == '1':
            job_id = input("Enter job ID: ").strip()
            monitor_job(job_id, args.refresh)
        
        elif choice == '2':
            query = input("Enter research query: ").strip()
            key = input("Idempotency key (optional): ").strip() or None
            create_and_monitor(query, key)
        
        else:
            print("Exiting...")


if __name__ == "__main__":
    main()