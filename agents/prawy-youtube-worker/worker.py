"""
prawy-youtube-worker v1.0

Autonomiczny worker kanału Studio Prawy_PL.
Monitoruje YT → VSE pipeline → editorial review.

⛔ Domyślnie: WP=draft, YT=unlisted.
Publikacja TYLKO po zatwierdzeniu przez redaktora.

Uso:
    python worker.py --run              # pełny scan kanału
    python worker.py --video-id XYZ     # pojedynczy film
    python worker.py --health           # health check

Env vars:
    VSE_JWT              JWT token dla VSE API
    CONTENT_RADAR_JWT    JWT token dla Content Radar (opcjonalny)
"""
import os, sys, argparse, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agents.base.worker_base import WorkerBase, ContentCandidate
from agents.base.sources.youtube_channel_source import YouTubeChannelSource
from agents.base.trend_signals.content_radar_signal import ContentRadarSignal

CHANNEL_ID = 'UCoH2G9By4OX3kcLsc8lHgDw'
PORTAL = 'prawy.pl'
PORTAL_ID = '2b047d7d-15a1-4d2f-8463-f89c2275bb73'
VSE_URL = 'https://vse.impresjapr.pl'
CONTENT_RADAR_URL = 'https://radar.impresjapr.pl'

CONFIG = {
    'portal': PORTAL,
    'state_file': Path(__file__).parent / 'prawy_yt_state.json',
    'content_radar_url': CONTENT_RADAR_URL,
}

class PrawyYouTubeWorker(WorkerBase):
    """
    Worker kanału Studio Prawy_PL.
    
    Źródła:
    - YouTubeChannelSource: nowe filmy z kanału UCoH2G9By4OX3kcLsc8lHgDw
    
    Sygnały trendów:
    - ContentRadarSignal: viral score z radar.impresjapr.pl
    """
    
    def __init__(self, config=None):
        super().__init__(config or CONFIG)
        
        vse_token = os.getenv('VSE_JWT')
        cr_token = os.getenv('CONTENT_RADAR_JWT')
        
        self.add_source(YouTubeChannelSource(
            channel_id=CHANNEL_ID,
            portal=PORTAL,
            vse_api_url=VSE_URL,
            vse_token=vse_token,
            days_back=7
        ))
        
        if cr_token:
            self.add_trend_signal(ContentRadarSignal(
                api_url=CONTENT_RADAR_URL,
                jwt_token=cr_token
            ))
    
    def process(self, candidate: ContentCandidate) -> dict:
        """
        Uruchom VSE pipeline dla kandydata.
        1. POST /v1/generate
        2. POST /v1/inject (draft)
        3. POST /v1/shorts/candidates
        4. Notify editor (TODO: Telegram)
        """
        import requests
        video_id = candidate.metadata.get('video_id', candidate.content_url.split('v=')[-1])
        token = os.getenv('VSE_JWT')
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        
        self.logger.info(f"Processing {video_id}: {candidate.title}")
        
        # 1. Generate
        gen_resp = requests.post(f"{VSE_URL}/v1/generate", headers=headers, json={
            'video_url': f'https://www.youtube.com/watch?v={video_id}',
            'llm_provider': 'claude', 'lang': 'pl',
            'publication_type': 'full_analysis', 'portal_id': PORTAL_ID
        }, timeout=600)
        
        if gen_resp.status_code != 200:
            return {'status': 'error', 'step': 'generate', 'error': gen_resp.text[:200]}
        
        schema_data = gen_resp.json().get('schema_data')
        
        # 2. Inject as draft
        inj_resp = requests.post(f"{VSE_URL}/v1/inject", headers=headers, json={
            'schema_data': schema_data, 'post_status': 'draft', 'post_format': 'video'
        }, timeout=60)
        
        wp_post_id = inj_resp.json().get('post_id') if inj_resp.status_code == 200 else None
        
        # 3. Shorts candidates
        shorts_resp = requests.post(f"{VSE_URL}/v1/shorts/candidates", headers=headers, json={
            'youtube_id': video_id, 'portal_id': PORTAL_ID
        }, timeout=60)
        
        result = {
            'video_id': video_id,
            'wp_post_id': wp_post_id,
            'status': 'done' if wp_post_id else 'partial',
            'shorts_count': len(shorts_resp.json()) if shorts_resp.status_code == 200 else 0
        }
        
        self.logger.info(f"Done: {result}")
        return result
    
    def run_single(self, video_id: str) -> dict:
        """Przetwórz konkretny film po video_id"""
        candidate = ContentCandidate(
            id=video_id,
            source='manual',
            portal=PORTAL,
            title=f'Video {video_id}',
            summary='Manual processing',
            content_url=f'https://www.youtube.com/watch?v={video_id}',
            metadata={'video_id': video_id}
        )
        return self.process(candidate)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prawy YouTube Worker')
    parser.add_argument('--run', action='store_true', help='Skanuj kanał i przetwórz nowe filmy')
    parser.add_argument('--video-id', help='Przetwórz konkretny film')
    parser.add_argument('--health', action='store_true')
    args = parser.parse_args()
    
    worker = PrawyYouTubeWorker()
    
    if args.health:
        print(json.dumps(worker.health_check(), indent=2, ensure_ascii=False))
    elif args.video_id:
        result = worker.run_single(args.video_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.run:
        candidates = worker.run()
        print(f"Znaleziono {len(candidates)} nowych filmów")
        for c in candidates:
            result = worker.process(c)
            print(f"  {c.title}: {result}")
