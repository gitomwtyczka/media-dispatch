import pytest
import os
import sys
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
        assert mock_run.call_count >= 1

@patch('pipeline.subprocess.run')
def test_idempotency_skip_inject(mock_run):
    mock_run_res = MagicMock()
    mock_run_res.stdout = b'{"found": true, "id": 1234, "status": "publish"}'
    mock_run.return_value = mock_run_res
    
    worker = BibliaWorker(dry_run=False)
    existing_id, status = worker.pipeline.check_existing_wp_post("test_id", "Title")
    assert existing_id == 1234
    
    res = worker.pipeline.step_inject("test_id", "Title", {}, "2026-10-10", "draft")
    assert res == 1234

@patch('pipeline.subprocess.run')
def test_get_yt_tokens_channel_id(mock_run):
    worker = BibliaWorker(dry_run=False)
    mock_run_res = MagicMock()
    import config
    # Output mock credentials matching config.YT_CHANNEL
    mock_run_res.stdout = b'[{"channel_id": "' + config.YT_CHANNEL.encode() + b'", "token": "abc"}]'
    mock_run.return_value = mock_run_res
    
    with patch('pipeline.build'):
        worker.pipeline.get_yt_tokens()
        assert worker.pipeline.channel_token == "abc"

@patch('pipeline.subprocess.run')
def test_step_verify(mock_run):
    worker = BibliaWorker(dry_run=False)
    worker.pipeline.yt_client = MagicMock()
    worker.pipeline.yt_client.videos().list().execute.return_value = {"items": [{"status": {"privacyStatus": "public"}}]}
    
    mock_run_res = MagicMock()
    mock_run_res.stdout = b'{"status": "publish", "date": "2026-10-10"}'
    mock_run.return_value = mock_run_res
    
    v_res = worker.pipeline.step_verify(1234, "test_id")
    assert v_res["ok"] is True
    assert v_res["yt_verified"] == "public"
    assert "publish" in v_res["wp_verified"]
