import pytest
import os
import sys
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from worker import BibliaWorker

@patch('pipeline.subprocess.run')
@patch('pipeline.requests.post')
def test_transcript_guard_real_fallback(mock_post, mock_run):
    mock_resp1 = MagicMock()
    mock_resp1.ok = True
    mock_resp1.json.return_value = {"transkrypcja": "brak transkryptu"}
    
    mock_resp2 = MagicMock()
    mock_resp2.status_code = 200
    mock_resp2.json.return_value = {"schema_data": {"vtt": "MOCK VTT"}}
    
    mock_resp3 = MagicMock()
    mock_resp3.ok = True
    mock_resp3.json.return_value = {"transkrypcja": "Poprawny transkrypt po retry"}
    
    mock_post.side_effect = [mock_resp1, mock_resp2, mock_resp3]
    
    mock_run_res = MagicMock()
    mock_run_res.returncode = 0
    mock_run_res.stdout = b""
    mock_run.return_value = mock_run_res
    
    worker = BibliaWorker(dry_run=False)
    worker.pipeline.headers = {"Authorization": "Bearer mock"}
    worker.pipeline.yt_client = MagicMock()
    worker.pipeline.yt_client.captions().insert().execute.return_value = {}
    
    with patch('pipeline.Path.exists', return_value=True), patch('pipeline.open'), patch('pipeline.time.sleep'):
        res = worker.pipeline.step_generate("test_id", "Title", mp4_path="dummy.mp4")
        assert "Poprawny transkrypt" in res.get("transkrypcja")

@patch('pipeline.subprocess.run')
def test_step_verify_ok(mock_run):
    worker = BibliaWorker(dry_run=False)
    worker.pipeline.yt_client = MagicMock()
    worker.pipeline.yt_client.videos().list().execute.return_value = {
        "items": [{
            "status": {"privacyStatus": "private", "publishAt": "2026-10-10T10:00:00Z", "embeddable": True},
            "snippet": {"defaultLanguage": "pl", "defaultAudioLanguage": "pl"}
        }]
    }
    worker.pipeline.yt_client.playlistItems().list().execute.return_value = {
        "items": [{"snippet": {"resourceId": {"videoId": "test_id"}}}]
    }
    import config
    config.PLAYLIST = "mock_playlist"
    
    mock_run_res = MagicMock()
    mock_run_res.stdout = json.dumps({
        "status": "future", "date": "2026-10-10", "podcast_show": ["prawy-biblijny"],
        "categories": ["biblia"], "meta": {"podcast_youtube_url": "https://www.youtube.com/watch?v=test_id"}
    }).encode()
    mock_run.return_value = mock_run_res
    
    v_res = worker.pipeline.step_verify(1234, "test_id", "future", "2026-10-10T10:00:00Z")
    assert v_res["ok"] is True
    assert len(v_res["errors"]) == 0

@patch('pipeline.subprocess.run')
def test_step_verify_failed_wp_meta(mock_run):
    worker = BibliaWorker(dry_run=False)
    worker.pipeline.yt_client = MagicMock()
    worker.pipeline.yt_client.videos().list().execute.return_value = {
        "items": [{
            "status": {"privacyStatus": "private", "publishAt": "2026-10-10T10:00:00Z", "embeddable": True},
            "snippet": {"defaultLanguage": "pl", "defaultAudioLanguage": "pl"}
        }]
    }
    worker.pipeline.yt_client.playlistItems().list().execute.return_value = {
        "items": [{"snippet": {"resourceId": {"videoId": "test_id"}}}]
    }
    
    mock_run_res = MagicMock()
    mock_run_res.stdout = json.dumps({
        "status": "future", "date": "2026-10-10", "podcast_show": ["prawy-biblijny"],
        "categories": ["inna"], "meta": {"podcast_youtube_url": "invalid"}
    }).encode()
    mock_run.return_value = mock_run_res
    
    v_res = worker.pipeline.step_verify(1234, "test_id", "future", "2026-10-10T10:00:00Z")
    assert v_res["ok"] is False
    assert any("meta podcast_youtube_url" in err for err in v_res["errors"])
    assert any("missing category: biblia" in err for err in v_res["errors"])

@patch('pipeline.subprocess.run')
def test_step_verify_failed_yt_embeddable(mock_run):
    worker = BibliaWorker(dry_run=False)
    worker.pipeline.yt_client = MagicMock()
    worker.pipeline.yt_client.videos().list().execute.return_value = {
        "items": [{
            "status": {"privacyStatus": "private", "publishAt": "2026-10-10T10:00:00Z", "embeddable": False},
            "snippet": {"defaultLanguage": "pl", "defaultAudioLanguage": "pl"}
        }]
    }
    worker.pipeline.yt_client.playlistItems().list().execute.return_value = {
        "items": [{"snippet": {"resourceId": {"videoId": "test_id"}}}]
    }
    
    mock_run_res = MagicMock()
    mock_run_res.stdout = json.dumps({
        "status": "future", "date": "2026-10-10", "podcast_show": ["prawy-biblijny"],
        "categories": ["biblia"], "meta": {"podcast_youtube_url": "https://www.youtube.com/watch?v=test_id"}
    }).encode()
    mock_run.return_value = mock_run_res
    
    v_res = worker.pipeline.step_verify(1234, "test_id", "future", "2026-10-10T10:00:00Z")
    assert v_res["ok"] is False
    assert any("embeddable" in err for err in v_res["errors"])
