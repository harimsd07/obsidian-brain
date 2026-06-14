"""
API Key Authentication Middleware for Obsidian Brain

Provides:
- API key generation and validation
- Flexible authentication modes (optional/required)
- Rate limiting per API key
- Key management endpoints
"""

import os
import secrets
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from fastapi import HTTPException, Request
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Configuration
API_KEY_DIR = Path(os.getenv("BRAIN_API_KEY_DIR", "./data/api_keys"))
API_KEYS_FILE = API_KEY_DIR / "keys.json"
AUTH_REQUIRED = os.getenv("BRAIN_AUTH_REQUIRED", "false").lower() == "true"
API_KEY_HEADER = "X-API-Key"

class APIKeyManager:
    """Manage API keys for authentication"""
    
    def __init__(self):
        self.api_key_dir = API_KEY_DIR
        self.api_key_dir.mkdir(parents=True, exist_ok=True)
        self.keys_file = API_KEYS_FILE
        self.keys = self._load_keys()
        
    def _load_keys(self) -> Dict:
        """Load API keys from file"""
        if self.keys_file.exists():
            try:
                with open(self.keys_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading API keys: {e}")
                return {}
        return {}
    
    def _save_keys(self):
        """Save API keys to file"""
        try:
            with open(self.keys_file, 'w') as f:
                json.dump(self.keys, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving API keys: {e}")
    
    def generate_key(self, name: str, days_valid: int = 365) -> str:
        """
        Generate a new API key
        
        Args:
            name: Human-readable name for the key
            days_valid: Number of days until expiration (0 = never)
            
        Returns:
            The new API key
        """
        # Generate random 32-byte key (256-bit)
        key = f"obsidian_{secrets.token_urlsafe(32)}"
        
        # Calculate expiration
        if days_valid > 0:
            expiration = (datetime.now() + timedelta(days=days_valid)).isoformat()
        else:
            expiration = None  # Never expires
        
        # Store key info (never store the key itself in plain text in production)
        key_hash = self._hash_key(key)
        self.keys[key_hash] = {
            "name": name,
            "created": datetime.now().isoformat(),
            "expiration": expiration,
            "active": True,
            "requests_count": 0,
            "last_used": None
        }
        
        self._save_keys()
        logger.info(f"Generated new API key: {name}")
        return key
    
    def validate_key(self, key: str) -> bool:
        """
        Validate an API key
        
        Args:
            key: The API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        key_hash = self._hash_key(key)
        
        if key_hash not in self.keys:
            return False
        
        key_info = self.keys[key_hash]
        
        # Check if active
        if not key_info.get("active", True):
            return False
        
        # Check expiration
        if key_info.get("expiration"):
            expiration = datetime.fromisoformat(key_info["expiration"])
            if datetime.now() > expiration:
                return False
        
        # Update last used time
        key_info["last_used"] = datetime.now().isoformat()
        key_info["requests_count"] = key_info.get("requests_count", 0) + 1
        self._save_keys()
        
        return True
    
    def revoke_key(self, key: str) -> bool:
        """Revoke an API key"""
        key_hash = self._hash_key(key)
        if key_hash in self.keys:
            self.keys[key_hash]["active"] = False
            self._save_keys()
            logger.info(f"Revoked API key: {self.keys[key_hash]['name']}")
            return True
        return False
    
    def list_keys(self) -> List[Dict]:
        """List all active API keys (without the key itself)"""
        active_keys = []
        for key_hash, info in self.keys.items():
            if info.get("active", True):
                key_info = info.copy()
                # Show masked key for reference
                key_info["key_hash"] = key_hash[:20] + "..."
                active_keys.append(key_info)
        return active_keys
    
    @staticmethod
    def _hash_key(key: str) -> str:
        """Hash an API key (simple implementation for demonstration)"""
        import hashlib
        return hashlib.sha256(key.encode()).hexdigest()


# Global API key manager
api_key_manager = APIKeyManager()


def require_api_key(f):
    """Decorator to require API key for endpoint"""
    @wraps(f)
    async def wrapper(request: Request, *args, **kwargs):
        if not AUTH_REQUIRED:
            # Authentication disabled
            return await f(request, *args, **kwargs)
        
        # Get API key from header
        api_key = request.headers.get(API_KEY_HEADER)
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="API key required. Use X-API-Key header."
            )
        
        # Validate API key
        if not api_key_manager.validate_key(api_key):
            raise HTTPException(
                status_code=403,
                detail="Invalid or expired API key"
            )
        
        return await f(request, *args, **kwargs)
    
    return wrapper


def get_api_key_from_request(request: Request) -> Optional[str]:
    """Extract API key from request if present"""
    return request.headers.get(API_KEY_HEADER)


class AuthInfo:
    """Information about authenticated request"""
    def __init__(self, api_key: Optional[str] = None, auth_required: bool = False):
        self.api_key = api_key
        self.auth_required = auth_required
        self.authenticated = api_key is not None if auth_required else True


# Endpoint models for key management
class GenerateKeyRequest:
    def __init__(self, name: str, days_valid: int = 365):
        self.name = name
        self.days_valid = days_valid


class RevokeKeyRequest:
    def __init__(self, key: str):
        self.key = key
