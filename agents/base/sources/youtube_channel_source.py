"""agents/base/sources/youtube_channel_source.py

YouTube Channel Source Plugin.
media-dispatch | media-dev-architect-02 | 01.09.2026
"""
from agents.base.worker_base import SourcePlugin, ContentCandidate
from typing import List, Optional
import hashlib


class YouTubeChannelSource(SourcePlugin):
    """Monitoruje kanał YouTube i wykrywa nowe filmy z napisami.

    Flow:
    1. YouTube API: pobierz ostatnie N filmów z kanału
    2. Filtruj: tylko te które NIE są w VSE (transcript_jobs)
    3. Sprawdz napisy (ASR lub ręczne)
    4. Zwróć ContentCandidate dla każdego nowego
    """
    name = 'youtube_channel'

    def __init__(
        self,
        channel_id: str,
        portal: str,
        vse_api_url: str,
        vse_token: Optional[str] = None,
        yt_credentials: Optional[dict] = None,
        days_back: int = 7,
    ):
        self.channel_id = channel_id
        self.portal = portal
        self.vse_api_url = vse_api_url
        self.vse_token = vse_token
        self.yt_credentials = yt_credentials or {}
        self.days_back = days_back

    def fetch(self) -> List[ContentCandidate]:
        """TODO: YouTube API + VSE check"""
        # 1. youtube.channels().list(id=self.channel_id, part='contentDetails')
        # 2. youtube.playlistItems().list(playlistId=uploads_id, maxResults=50)
        # 3. self._already_in_vse(video_id) — GET {vse_api_url}/v1/status/{video_id}
        # 4. self._has_captions(video_id)
        # 5. Return ContentCandidate per new video
        return []  # placeholder

    def _already_in_vse(self, video_id: str) -> bool:
        """Sprawdź czy film jest już w VSE transcript_jobs"""
        try:
            import requests
            r = requests.get(
                f"{self.vse_api_url}/v1/status/{video_id}",
                headers={'Authorization': f'Bearer {self.vse_token}'},
                timeout=10,
            )
            return r.status_code == 200 and r.json().get('status') in ['done', 'processing']
        except Exception:
            return False

    def _has_captions(self, video_id: str) -> bool:
        """Sprawdz dostępność napisów przez yt-dlp (szybsze niż API)"""
        try:
            import subprocess
            r = subprocess.run(
                ['yt-dlp', '--list-subs', f'https://youtube.com/watch?v={video_id}'],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return 'pl' in r.stdout or 'en' in r.stdout
        except Exception:
            return False

    def _make_candidate(self, video: dict) -> ContentCandidate:
        video_id = video['snippet']['resourceId']['videoId']
        title = video['snippet']['title']
        return ContentCandidate(
            id=hashlib.md5(video_id.encode()).hexdigest()[:8],
            source=self.name,
            portal=self.portal,
            title=title,
            summary=f"Nowy film na kanale: {title}",
            content_url=f"https://www.youtube.com/watch?v={video_id}",
            metadata={
                'video_id': video_id,
                'published_at': video['snippet'].get('publishedAt', ''),
                'has_captions': self._has_captions(video_id),
            },
            priority=8,
        )
