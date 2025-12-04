"""
Session Manager - In-memory session storage
Stores site data, layouts, and chat history per session
"""
import uuid
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import threading


@dataclass
class Session:
    """Session data container"""
    id: str
    created_at: datetime
    boundary: Optional[Dict] = None
    boundary_coords: Optional[List] = None
    metadata: Dict = field(default_factory=dict)
    layouts: List[Dict] = field(default_factory=list)
    chat_history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "has_boundary": self.boundary is not None,
            "num_layouts": len(self.layouts),
            "num_messages": len(self.chat_history)
        }


class SessionManager:
    """
    In-memory session storage manager
    
    Thread-safe session creation and retrieval.
    Sessions are stored in a dictionary with UUID keys.
    """
    
    def __init__(self, max_sessions: int = 1000):
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()
        self._max_sessions = max_sessions
    
    def create_session(self) -> Session:
        """Create new session with UUID"""
        session_id = str(uuid.uuid4())
        session = Session(
            id=session_id,
            created_at=datetime.now()
        )
        
        with self._lock:
            # Cleanup if too many sessions
            if len(self._sessions) >= self._max_sessions:
                self._cleanup_oldest()
            
            self._sessions[session_id] = session
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self._sessions.get(session_id)
    
    def update_session(self, session_id: str, **kwargs) -> Optional[Session]:
        """Update session data"""
        session = self._sessions.get(session_id)
        if session:
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
        return session
    
    def set_boundary(self, session_id: str, boundary: Dict, coords: List, metadata: Dict) -> bool:
        """Set boundary data for session"""
        session = self._sessions.get(session_id)
        if session:
            session.boundary = boundary
            session.boundary_coords = coords
            session.metadata = metadata
            return True
        return False
    
    def set_layouts(self, session_id: str, layouts: List[Dict]) -> bool:
        """Set generated layouts for session"""
        session = self._sessions.get(session_id)
        if session:
            session.layouts = layouts
            return True
        return False
    
    def add_chat_message(self, session_id: str, role: str, content: str, model: str = None) -> bool:
        """Add chat message to history"""
        session = self._sessions.get(session_id)
        if session:
            session.chat_history.append({
                "role": role,
                "content": content,
                "model": model,
                "timestamp": datetime.now().isoformat()
            })
            return True
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
        return False
    
    def _cleanup_oldest(self):
        """Remove oldest sessions when limit reached"""
        if not self._sessions:
            return
        
        # Sort by created_at and remove oldest 10%
        sorted_sessions = sorted(
            self._sessions.items(),
            key=lambda x: x[1].created_at
        )
        
        remove_count = max(1, len(sorted_sessions) // 10)
        for session_id, _ in sorted_sessions[:remove_count]:
            del self._sessions[session_id]
    
    @property
    def session_count(self) -> int:
        return len(self._sessions)


# Global session manager instance
session_manager = SessionManager()
