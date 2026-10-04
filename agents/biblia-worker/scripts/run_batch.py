import os
import sys

# Dodajemy katalog agents/biblia-worker do sys.path aby importy dzialaly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from worker import BibliaWorker

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("batch_file", help="Path to batch JSON file")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    worker = BibliaWorker(dry_run=args.dry_run)
    worker.process_batch(args.batch_file)
