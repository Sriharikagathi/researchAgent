"""Main entry point for the research agent application."""

import asyncio
import argparse
from pathlib import Path
import uvicorn
from API.fastapi_app import app


from Agent.OrchestrationAgent import ResearchAgent
from Config.Settings import settings


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Research Agent CLI")
    
    parser.add_argument(
        '--mode',
        choices=['ingest', 'research', 'api'],
        required=True,
        help='Operation mode'
    )
    
    parser.add_argument(
        '--query',
        type=str,
        help='Research query (for research mode)'
    )
    
    parser.add_argument(
        '--documents',
        nargs='+',
        help='Document paths to ingest (for ingest mode)'
    )
    
    parser.add_argument(
        '--directory',
        type=str,
        help='Directory path to ingest all documents'
    )
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = ResearchAgent()
    
    if args.mode == 'ingest':
        print("\n" + "="*80)
        print("DOCUMENT INGESTION MODE")
        print("="*80 + "\n")
        
        if args.documents:
            # Ingest specific documents
            total = await agent.ingest_documents(args.documents)
            print(f"\n✓ Successfully ingested {total} chunks from {len(args.documents)} documents")
        
        elif args.directory:
            # Ingest directory
            total = await agent.ingest_directory(args.directory)
            print(f"\n✓ Successfully ingested {total} chunks from directory")
        
        else:
            print("Error: Please provide --documents or --directory")
            return
    
    elif args.mode == 'research':
        if not args.query:
            print("Error: Please provide --query for research mode")
            return
        
        print("\n" + "="*80)
        print("RESEARCH MODE")
        print("="*80 + "\n")
        print(f"Query: {args.query}\n")
        
        # Run research
        result = await agent.run_research(args.query)
        
        if result['success']:
            print("\n" + "="*80)
            print("RESEARCH COMPLETED")
            print("="*80)
            
            print(f"\n{result['report']}\n")
            
            print("\n" + "="*80)
            print("SUMMARY")
            print("="*80)
            print(f"Session ID: {result['session_id']}")
            print(f"Documents Retrieved: {result['summary']['retrieved_documents']}")
            print(f"Web Sources: {result['summary']['web_sources']}")
            print(f"Citations: {result['summary']['citations_verified']}")
            print(f"PII Redacted: {result['summary']['pii_redacted']}")
            print(f"Export Path: {result['export_path']}")
            print(f"Total Logs: {result['summary']['total_logs']}")
            
            print("\n" + "="*80)
            print("COMPLIANCE REPORT")
            print("="*80)
            if result['compliance']:
                print(f"PII Found: {result['compliance']['pii_count']}")
                print(f"PII Types: {', '.join(result['compliance']['pii_types'])}")
                print(f"Status: {result['compliance']['compliance_status']}")
            
            print("\n" + "="*80)
            print("RECENT LOGS")
            print("="*80)
            for log in result['logs'][-10:]:
                print(f"[{log['timestamp']}] [{log['type'].upper()}] {log['message']}")
        
        else:
            print(f"\n✗ Research failed: {result.get('error', 'Unknown error')}")
    


if __name__ == "__main__":
    asyncio.run(main())