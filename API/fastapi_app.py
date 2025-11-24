"""FastAPI application for the research agent."""

from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import os
import shutil

from Agent.OrchestrationAgent import ResearchAgent
from Config.Settings import settings


app = FastAPI(
    title="Research Agent API",
    description="RAG-based research agent with compliance and auditing",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
research_agent: Optional[ResearchAgent] = None


class ResearchQuery(BaseModel):
    """Research query model."""
    query: str
    session_id: Optional[str] = None


class IngestDocumentsRequest(BaseModel):
    """Document ingestion request."""
    file_paths: List[str]


@app.on_event("startup")
async def startup_event():
    """Initialize research agent on startup."""
    global research_agent
    research_agent = ResearchAgent()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Research Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_initialized": research_agent is not None
    }


@app.post("/ingest/document")
async def ingest_document(file: UploadFile = File(...)):
    """
    Ingest a single document.
    
    Args:
        file: Document file to ingest
        
    Returns:
        Ingestion result
    """
    if not research_agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    # Save uploaded file
    file_path = os.path.join(settings.documents_path, file.filename)
    os.makedirs(settings.documents_path, exist_ok=True)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Ingest document
    try:
        chunks = await research_agent.ingest_document(file_path)
        
        return {
            "success": True,
            "filename": file.filename,
            "chunks_created": chunks,
            "message": f"Successfully ingested {file.filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/directory")
async def ingest_directory(directory_path: str):
    """
    Ingest all documents from a directory.
    
    Args:
        directory_path: Path to directory
        
    Returns:
        Ingestion result
    """
    if not research_agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    try:
        chunks = await research_agent.ingest_directory(directory_path)
        
        return {
            "success": True,
            "directory": directory_path,
            "chunks_created": chunks,
            "message": f"Successfully ingested documents from {directory_path}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research")
async def run_research(request: ResearchQuery):
    """
    Run research query.
    
    Args:
        request: Research query request
        
    Returns:
        Research results
    """
    if not research_agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    try:
        result = await research_agent.run_research(request.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs")
async def get_logs():
    """
    Get all logs from current session.
    
    Returns:
        List of log entries
    """
    if not research_agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    return {
        "logs": research_agent.get_logs(),
        "total": len(research_agent.get_logs())
    }


@app.get("/state")
async def get_state():
    """
    Get current state summary.
    
    Returns:
        State summary
    """
    if not research_agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    return research_agent.get_state_summary()


@app.get("/export/{filename}")
async def download_export(filename: str):
    """
    Download exported report.
    
    Args:
        filename: Name of file to download
        
    Returns:
        File download response
    """
    file_path = os.path.join(settings.export_path, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type='application/octet-stream',
        filename=filename
    )


@app.delete("/state")
async def clear_state():
    """Clear current state."""
    if not research_agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    research_agent.clear_state()
    
    return {
        "message": "State cleared successfully"
    }


# WebSocket for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time log streaming.
    
    Args:
        websocket: WebSocket connection
    """
    await websocket.accept()
    
    try:
        if not research_agent:
            await websocket.send_json({
                "error": "Agent not initialized"
            })
            await websocket.close()
            return
        
        # Send initial state
        await websocket.send_json({
            "type": "state",
            "data": research_agent.get_state_summary()
        })
        
        # Stream logs
        last_log_count = 0
        
        while True:
            current_logs = research_agent.get_logs()
            
            if len(current_logs) > last_log_count:
                # Send new logs
                new_logs = current_logs[last_log_count:]
                
                for log in new_logs:
                    await websocket.send_json({
                        "type": "log",
                        "data": log
                    })
                
                last_log_count = len(current_logs)
            
            # Send state update
            await websocket.send_json({
                "type": "state",
                "data": research_agent.get_state_summary()
            })
            
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)