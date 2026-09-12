"""
vse-worker package — Autonomiczny moduł Video SEO Engine w architekturze media-dispatch.
"""

from .pipeline import VSEPipeline, extract_youtube_id
from .worker import health_check, process, get_status

__all__ = ["VSEPipeline", "extract_youtube_id", "health_check", "process", "get_status"]
