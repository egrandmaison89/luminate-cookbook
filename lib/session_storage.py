#!/usr/bin/env python3
"""
Persistent Session Storage for Luminate Cookbook

Provides session persistence across Cloud Run instances using either:
1. Google Cloud Storage (for Cloud Run deployments)
2. Local filesystem (for local development)

This solves the problem of ephemeral /tmp storage in Cloud Run containers.
"""

import os
import json
import hashlib
import time
from typing import Optional, Dict, Any

# Check if running on Google Cloud
def is_google_cloud():
    """Check if running on Google Cloud (Cloud Run, GCE, etc.)."""
    return (
        os.environ.get("K_SERVICE") is not None or  # Cloud Run
        os.environ.get("GAE_APPLICATION") is not None or  # App Engine
        os.environ.get("GOOGLE_CLOUD_PROJECT") is not None
    )


def get_gcs_bucket_name():
    """Get the GCS bucket name for session storage."""
    # Try to get from environment variable first
    bucket = os.environ.get("SESSION_STORAGE_BUCKET")
    if bucket:
        return bucket
    
    # Try to construct from project ID
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
    if project_id:
        return f"{project_id}-luminate-sessions"
    
    return None


class SessionStorage:
    """
    Persistent session storage that works across Cloud Run instances.
    
    Uses GCS on Cloud Run, falls back to local filesystem for development.
    """
    
    def __init__(self, use_gcs: bool = None):
        """
        Initialize session storage.
        
        Args:
            use_gcs: Force GCS usage (True/False) or auto-detect (None)
        """
        self._gcs_client = None
        self._bucket = None
        
        # Auto-detect or use specified setting
        if use_gcs is None:
            self.use_gcs = is_google_cloud() and get_gcs_bucket_name() is not None
        else:
            self.use_gcs = use_gcs
        
        if self.use_gcs:
            self._init_gcs()
        else:
            self._init_local()
    
    def _init_gcs(self):
        """Initialize Google Cloud Storage client."""
        try:
            from google.cloud import storage
            self._gcs_client = storage.Client()
            bucket_name = get_gcs_bucket_name()
            
            # Try to get or create bucket
            try:
                self._bucket = self._gcs_client.get_bucket(bucket_name)
            except Exception:
                # Bucket doesn't exist, try to create it
                try:
                    self._bucket = self._gcs_client.create_bucket(bucket_name)
                except Exception as e:
                    print(f"Warning: Could not create GCS bucket: {e}")
                    self.use_gcs = False
                    self._init_local()
        except ImportError:
            print("Warning: google-cloud-storage not installed, using local storage")
            self.use_gcs = False
            self._init_local()
        except Exception as e:
            print(f"Warning: GCS initialization failed: {e}, using local storage")
            self.use_gcs = False
            self._init_local()
    
    def _init_local(self):
        """Initialize local filesystem storage."""
        temp_dir = os.environ.get('TMPDIR', '/tmp')
        self.local_dir = os.path.join(temp_dir, 'luminate_sessions')
        os.makedirs(self.local_dir, mode=0o700, exist_ok=True)
    
    def _get_session_key(self, username: str) -> str:
        """Generate a secure key for the session file."""
        username_hash = hashlib.sha256(username.encode()).hexdigest()[:16]
        return f"session_{username_hash}.json"
    
    def save_session(self, username: str, session_data: Dict[str, Any]) -> bool:
        """
        Save session data for a user.
        
        Args:
            username: Username to save session for
            session_data: Session data dictionary (cookies, storage state, etc.)
            
        Returns:
            bool: True if saved successfully
        """
        key = self._get_session_key(username)
        
        # Add metadata
        session_data['_saved_at'] = time.time()
        session_data['_username_hash'] = hashlib.sha256(username.encode()).hexdigest()[:8]
        
        try:
            if self.use_gcs and self._bucket:
                blob = self._bucket.blob(f"sessions/{key}")
                blob.upload_from_string(
                    json.dumps(session_data),
                    content_type='application/json'
                )
                return True
            else:
                # Local storage
                path = os.path.join(self.local_dir, key)
                with open(path, 'w') as f:
                    json.dump(session_data, f)
                os.chmod(path, 0o600)
                return True
        except Exception as e:
            print(f"Warning: Failed to save session: {e}")
            return False
    
    def load_session(self, username: str, max_age_hours: int = 24) -> Optional[Dict[str, Any]]:
        """
        Load session data for a user.
        
        Args:
            username: Username to load session for
            max_age_hours: Maximum age of session in hours (default 24)
            
        Returns:
            dict or None: Session data if found and valid, None otherwise
        """
        key = self._get_session_key(username)
        
        try:
            if self.use_gcs and self._bucket:
                blob = self._bucket.blob(f"sessions/{key}")
                if not blob.exists():
                    return None
                content = blob.download_as_string()
                session_data = json.loads(content)
            else:
                # Local storage
                path = os.path.join(self.local_dir, key)
                if not os.path.exists(path):
                    return None
                with open(path, 'r') as f:
                    session_data = json.load(f)
            
            # Check age
            saved_at = session_data.get('_saved_at', 0)
            age_hours = (time.time() - saved_at) / 3600
            if age_hours > max_age_hours:
                self.delete_session(username)
                return None
            
            return session_data
            
        except Exception as e:
            print(f"Warning: Failed to load session: {e}")
            return None
    
    def delete_session(self, username: str) -> bool:
        """
        Delete session for a user.
        
        Args:
            username: Username to delete session for
            
        Returns:
            bool: True if deleted successfully
        """
        key = self._get_session_key(username)
        
        try:
            if self.use_gcs and self._bucket:
                blob = self._bucket.blob(f"sessions/{key}")
                if blob.exists():
                    blob.delete()
                return True
            else:
                # Local storage
                path = os.path.join(self.local_dir, key)
                if os.path.exists(path):
                    os.remove(path)
                return True
        except Exception as e:
            print(f"Warning: Failed to delete session: {e}")
            return False
    
    def has_session(self, username: str) -> bool:
        """Check if a valid session exists for the user."""
        return self.load_session(username) is not None


# Global session storage instance
_session_storage = None

def get_session_storage() -> SessionStorage:
    """Get the global session storage instance."""
    global _session_storage
    if _session_storage is None:
        _session_storage = SessionStorage()
    return _session_storage
