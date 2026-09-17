import argparse
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from biblia_worker.worker import BibliaWorker

def main():
    parser = argparse.ArgumentParser(description="Biblia Batch Runner")
    parser.add_argument("batch_file", help="Path to batch JSON file")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.batch_file):
        print(f"Error: file {args.batch_file} not found.")
        sys.exit(1)
        
    worker = BibliaWorker()
    worker.process_batch(args.batch_file)

if __name__ == "__main__":
    main()
