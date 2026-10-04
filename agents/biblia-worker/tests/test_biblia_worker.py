import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Dodajemy katalog do sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from worker import BibliaWorker

@patch('pipeline.requests.post')
def test_idempotency_skip_inject(mock_post):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {'found': True}
    mock_post.return_value = mock_resp
    
    worker = BibliaWorker(dry_run=False)
    # mock token
    worker.pipeline.headers = {"Authorization": "Bearer mock"}
    
    # run step_inject
    res = worker.pipeline.step_inject("test_id", {}, "2026-10-10T10:00:00Z", "draft")
    assert res == "existing_id"

@patch('pipeline.requests.post')
def test_fail_fast_4xx(mock_post):
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 400
    mock_resp.text = "bad request"
    mock_post.return_value = mock_resp
    
    worker = BibliaWorker(dry_run=False)
    worker.pipeline.headers = {"Authorization": "Bearer mock"}
    
    with pytest.raises(Exception, match="4xx: 400"):
        worker.pipeline.step_generate("test_id")

@patch('pipeline.requests.post')
def test_invalid_grant_stop(mock_post):
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 401
    mock_resp.text = '{"error": "invalid_grant"}'
    mock_post.return_value = mock_resp
    
    worker = BibliaWorker(dry_run=False)
    worker.pipeline.headers = {"Authorization": "Bearer mock"}
    
    with pytest.raises(Exception, match="STOP_BATCH: invalid_grant"):
        worker.pipeline.step_generate("test_id")

def test_timezone_parsing():
    worker = BibliaWorker(dry_run=True)
    with patch('worker.BibliaPipeline.run') as mock_run:
        worker.process_single("test", "2026-10-10 12:00:00", "draft")
        # In October CEST (UTC+2) -> GMT is 10:00:00
        mock_run.assert_called_once()
        args = mock_run.call_args[0]
        # args[2] is publish_date_gmt
        assert args[2] == "2026-10-10 10:00:00"

@patch('pipeline.requests.post')
def test_transcript_guard(mock_post):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {"transkrypcja": "To wideo zawiera brak transkryptu."}
    mock_post.return_value = mock_resp
    
    worker = BibliaWorker(dry_run=False)
    worker.pipeline.headers = {"Authorization": "Bearer mock"}
    
    with pytest.raises(Exception, match="fallback require manual implementation"):
        worker.pipeline.step_generate("test_id", mp4_path="dummy.mp4")
