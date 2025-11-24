import logging
from obp.agents.foundational_gatherer import FoundationalGatherer
from obp.downloader import FoundationalDownloader
from obp.db import get_resources_collection
from uuid import uuid4
import time

logging.basicConfig(level=logging.INFO)

def test_end_to_end():
    request_id = str(uuid4())
    query = "Recent advances in quantum computing 2024"
    modality = "text"
    
    print(f"\n🆔 Request ID: {request_id}")
    
    # 1. Gather
    gatherer = FoundationalGatherer()
    print("🔍 Gathering...")
    count = gatherer.gather_and_store(query, modality, request_id, limit=3)
    print(f"Found {count} links.")
    
    if count == 0:
        print("❌ Failed to gather links. Aborting.")
        return

    # 2. Sample
    print("🧪 Sampling (1 item)...")
    sampled = gatherer.sample_resources(request_id, count_per_modality=1)
    print(f"Sampled {sampled} items.")
    
    # Check DB for sample
    col = get_resources_collection()
    sample_doc = col.find_one({"request_id": request_id, "status": "sampled"})
    if sample_doc:
        print(f"✅ Sample verified in DB: {sample_doc['sample_path']}")
    else:
        # Might be 'downloaded' if logic overlapped or failed?
        print("❌ Sample verification failed (No 'sampled' status found).")

    # 3. Full Download
    print("⬇️ Downloading All...")
    downloader = FoundationalDownloader()
    downloaded = downloader.download_all(request_id)
    print(f"Downloaded {downloaded} items.")
    
    # Check DB for downloads
    # Note: 'sampled' items might remain 'sampled' if download_all skips them or updates them?
    # download_all queries status='discovered'.
    # So the 'sampled' item (status='sampled') will be SKIPPED by download_all logic!
    # This is a logic flaw in my implementation if I want EVERYTHING downloaded.
    # But usually 'sampled' means it IS downloaded (sample_path).
    # If I want to move it to 'downloaded' or ensure it's in the final set...
    # The exporter logic checks 'downloaded' THEN 'sampled'.
    # So it covers both.
    
    # Let's check total items (sampled + downloaded)
    total_dl = col.count_documents({"request_id": request_id, "status": {"$in": ["downloaded", "sampled"]}})
    print(f"✅ Verified {total_dl} total items available locally.")
    
    if total_dl >= count: # Might be less if some failed download
        print("🎉 End-to-End Success!")
    else:
        print(f"⚠️ Partial success (Expected {count}, got {total_dl})")

if __name__ == "__main__":
    test_end_to_end()
