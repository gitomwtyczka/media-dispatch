import argparse
import json
import sys
import requests
from .pipeline import BibliaPipeline
from . import config

class BibliaWorker:
    def __init__(self):
        self.pipeline = BibliaPipeline()

    def health_check(self):
        try:
            print("[*] Checking VSE Health...")
            resp = requests.get(f"{config.VSE_BASE}/health")
            if not resp.ok:
                print("[-] VSE API Health Check failed.")
                return False
            
            print("[*] Checking JWT generation...")
            self.pipeline.get_jwt_token()
            print("[+] Health check passed!")
            return True
        except Exception as e:
            print(f"[-] Health check exception: {e}")
            return False

    def process_single(self, yt_id, publish_date, status):
        from datetime import datetime, timedelta
        local_dt = datetime.strptime(publish_date, "%Y-%m-%d %H:%M:%S")
        gmt_dt = local_dt - timedelta(hours=2)
        publish_date_gmt = gmt_dt.strftime("%Y-%m-%d %H:%M:%S")
        publish_date_iso = local_dt.strftime("%Y-%m-%dT%H:%M:%S+02:00")
        
        self.pipeline.run(yt_id, publish_date, publish_date_gmt, publish_date_iso, status)

    def process_batch(self, batch_file):
        with open(batch_file, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        for t in tasks:
            print(f"\n[*] Processing batch item: {t['yt_id']}")
            self.pipeline.run(
                t['yt_id'], 
                t['publish_date_local'], 
                t['publish_date_gmt'], 
                t.get('publish_date_iso', t['publish_date_local'].replace(" ", "T") + "+02:00"), 
                t.get('status', 'future')
            )

def main():
    parser = argparse.ArgumentParser(description="Biblia Worker")
    parser.add_argument("--health", action="store_true", help="Check health")
    parser.add_argument("--video-id", type=str, help="YouTube Video ID")
    parser.add_argument("--publish-date", type=str, help="Publish date YYYY-MM-DD HH:MM:SS")
    parser.add_argument("--status", type=str, default="future", help="WP Status")
    parser.add_argument("--batch", type=str, help="Path to batch JSON file")
    
    args = parser.parse_args()
    worker = BibliaWorker()
    
    if args.health:
        worker.health_check()
    elif args.batch:
        worker.process_batch(args.batch)
    elif args.video_id and args.publish_date:
        worker.process_single(args.video_id, args.publish_date, args.status)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
