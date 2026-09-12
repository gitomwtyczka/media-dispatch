"""agents/emisja-worker/__init__.py

emisja-worker package — synchronizacja arkusza Emisja oraz generowanie linków draft-collab.
"""

from .collab_linker import CollabLinker
from .worker import get_status, health_check, process

__all__ = ["CollabLinker", "health_check", "process", "get_status"]
