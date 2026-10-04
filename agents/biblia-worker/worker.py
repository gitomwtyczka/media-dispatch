import argparse
import json
import sys
import requests
import traceback
from zoneinfo import ZoneInfo
from datetime import datetime
import config
from pipeline import BibliaPipeline

class BibliaWorker:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.pipeline = BibliaPipeline(dry_run=dry_run)

    def health_check(self):
        if self.dry_run:
            print("[DRY RUN] Health check mock.")
            return True
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

    def process_single(self, yt_id, publish_date, status, mp4_path=None):
        warsaw_tz = ZoneInfo("Europe/Warsaw")
        local_dt = datetime.strptime(publish_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=warsaw_tz)
        utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
        
        publish_date_gmt = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
        publish_date_iso = local_dt.isoformat()
        
        self.pipeline.run(yt_id, publish_date, publish_date_gmt, publish_date_iso, status, mp4_path)

    def process_batch(self, batch_file):
        with open(batch_file, "r", encoding="utf-8") as f:
            tasks = json.load(f)
            
        results = []
        stop_batch = False
        
        try:
            for t in tasks:
                if stop_batch:
                    print("[!] Batch stopped due to invalid_grant.")
                    break
                    
                yt_id = t['yt_id']
                print(f"\n[*] Processing batch item: {yt_id}")
                
                try:
                    publish_now = t.get('publish_now', False)
                    status = "publish" if publish_now else "draft"
                    
                    if 'publish_at_local' in t:
                        warsaw_tz = ZoneInfo("Europe/Warsaw")
                        local_dt = datetime.strptime(t['publish_at_local'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=warsaw_tz)
                        utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
                        publish_date_local = local_dt.strftime("%Y-%m-%d %H:%M:%S")
                        publish_date_gmt = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                        publish_date_iso = local_dt.isoformat()
                        if not publish_now:
                            status = "future"
                    elif 'publish_at_iso' in t:
                        dt = datetime.fromisoformat(t['publish_at_iso'])
                        publish_date_local = dt.strftime("%Y-%m-%d %H:%M:%S")
                        publish_date_gmt = dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")
                        publish_date_iso = t['publish_at_iso']
                        if not publish_now:
                            status = "future"
                    else:
                        publish_date_local = ""
                        publish_date_gmt = ""
                        publish_date_iso = ""
                    
                    self.pipeline.run(
                        yt_id, 
                        publish_date_local, 
                        publish_date_gmt, 
                        publish_date_iso, 
                        status,
                        t.get('mp4_path')
                    )
                    results.append({"yt_id": yt_id, "status": "SUCCESS"})
                except Exception as e:
                    err_msg = str(e)
                    print(f"[-] Error on {yt_id}: {err_msg}")
                    results.append({"yt_id": yt_id, "status": "FAILED", "error": err_msg})
                    if "STOP_BATCH" in err_msg:
                        stop_batch = True
        finally:
            with open("results.json", "w", encoding="utf-8") as rf:
                json.dump(results, rf, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Biblia Worker")
    parser.add_argument("--health", action="store_true", help="Check health")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--video-id", type=str, help="YouTube Video ID")
    parser.add_argument("--publish-date", type=str, help="Publish date YYYY-MM-DD HH:MM:SS")
    parser.add_argument("--status", type=str, default="draft", help="WP Status")
    parser.add_argument("--batch", type=str, help="Path to batch JSON file")
    
    args = parser.parse_args()
    worker = BibliaWorker(dry_run=args.dry_run)
    
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
