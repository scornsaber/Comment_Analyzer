# main.py
# python3 main.py init
# python3 main.py fetch-youtube --video-id MG_npaLydKg --api-key YOUR_API_KEY
# python3 main.py load-jsonl
# python3 main.py export-csv
#

from pipeline import main as pipeline_main

if __name__ == "__main__":
    # Forward all CLI args to pipeline
    pipeline_main()
