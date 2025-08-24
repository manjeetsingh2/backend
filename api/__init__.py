"""
API module initialization
Centralized API routing with modular structure
"""

from .routes import create_api_router

__all__ = ["create_api_router"]