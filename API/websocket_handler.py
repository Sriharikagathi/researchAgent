"""WebSocket handler for real-time updates."""

from typing import Set
from fastapi import WebSocket
import asyncio
import json


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """
        Accept new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove WebSocket connection.
        
        Args:
            websocket: WebSocket connection
        """
        self.active_connections.discard(websocket)
    
    async def broadcast(self, message: dict):
        """
        Broadcast message to all connections.
        
        Args:
            message: Message to broadcast
        """
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        # Remove disconnected clients
        self.active_connections -= disconnected
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send message to specific connection.
        
        Args:
            message: Message to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)


# Global connection manager
manager = ConnectionManager()