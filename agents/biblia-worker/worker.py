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
                title = t.get('title', yt_id)
                print(f"\n[*] Processing batch item: {yt_id} ({title})")
                
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
                    
                    v_res = self.pipeline.run(
                        yt_id, 
                        title,
                        publish_date_local, 
                        publish_date_gmt, 
                        publish_date_iso, 
                        status,
                        t.get('mp4_path')
                    )
                    ok = v_res.get("ok", True)
                    results.append({
                        "yt_id": yt_id, 
                        "status": "SUCCESS" if ok else "FAILED", 
                        "verification": v_res
                    })
                except Exception as e:
                    err_msg = str(e)
                    print(f"[-] Error on {yt_id}: {err_msg}")
                    results.append({"yt_id": yt_id, "status": "FAILED", "error": err_msg})
                    if "STOP_BATCH" in err_msg:
                        stop_batch = True
        finally:
            with open("results.json", "w", encoding="utf-8") as rf:
                json.dump(results, rf, indent=2)
                
    def patch_meta(self, ids_list):
        for item in ids_list:
            wp_id, yt_id = item.split(':')
            self.pipeline.run_patch(yt_id, wp_id)

def main():
    parser = argparse.ArgumentParser(description="Biblia Worker")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--batch", type=str, help="Path to batch JSON file")
    parser.add_argument("--patch-meta", action="store_true", help="Run patch logic")
    parser.add_argument("--ids", type=str, nargs="+", help="list of wp_id:yt_id")
    
    args = parser.parse_args()
    worker = BibliaWorker(dry_run=args.dry_run)
    
    if args.patch_meta and args.ids:
        worker.patch_meta(args.ids)
    elif args.batch:
        worker.process_batch(args.batch)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
