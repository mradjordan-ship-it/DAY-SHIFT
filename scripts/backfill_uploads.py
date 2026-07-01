"""
Backfill script: Migrate existing local upload files to Neon database (bytea).

Run this ONCE after deploying the media_files table to persist all existing
uploads into durable Neon storage. Safe to re-run — it skips files already
in the DB.

Usage:
    uv run scripts/backfill_uploads.py
"""
import os
import sys
import mimetypes
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_conn

UPLOAD_DIR = Path("uploads")
BATCH = 50  # rows per transaction


def run() -> dict[str, int]:
    """Drain local files that aren't yet in media_files."""
    if not UPLOAD_DIR.exists():
        print(f"[Backfill] Uploads directory {UPLOAD_DIR} does not exist")
        return {"moved": 0, "skipped_missing": 0, "skipped_stub": 0}

    # Get all filenames already in DB
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT filename FROM media_files")
    db_filenames = {row["filename"] for row in cur.fetchall()}
    cur.close()
    conn.close()

    moved = skipped_missing = skipped_stub = 0
    all_files = list(UPLOAD_DIR.iterdir())
    
    print(f"[Backfill] Found {len(all_files)} files in {UPLOAD_DIR}")
    print(f"[Backfill] Already in DB: {len(db_filenames)}")

    batch_data = []
    
    for filepath in all_files:
        filename = filepath.name
        
        # Skip if already in DB
        if filename in db_filenames:
            continue
            
        if not filepath.is_file():
            continue
            
        file_size = filepath.stat().st_size
        
        # Skip corrupted stubs (< 100 bytes)
        if file_size < 100:
            skipped_stub += 1
            continue
            
        # Read and queue for DB insert
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            
            guessed, _ = mimetypes.guess_type(filename)
            mime_type = guessed or "application/octet-stream"
            
            batch_data.append((filename, data, mime_type, len(data)))
            
            # Commit in batches
            if len(batch_data) >= BATCH:
                conn2 = get_conn()
                cur2 = conn2.cursor()
                cur2.executemany(
                    "INSERT INTO media_files (filename, data, mime_type, file_size) VALUES (%s, %s, %s, %s) "
                    "ON CONFLICT (filename) DO NOTHING",
                    batch_data,
                )
                conn2.commit()
                cur2.close()
                conn2.close()
                moved += len(batch_data)
                print(f"[Backfill] Batch committed: +{len(batch_data)} (total: {moved})")
                batch_data = []
                
        except Exception as e:
            print(f"[Backfill] Error reading {filename}: {e}")
            skipped_missing += 1

    # Final partial batch
    if batch_data:
        conn3 = get_conn()
        cur3 = conn3.cursor()
        cur3.executemany(
            "INSERT INTO media_files (filename, data, mime_type, file_size) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (filename) DO NOTHING",
            batch_data,
        )
        conn3.commit()
        cur3.close()
        conn3.close()
        moved += len(batch_data)
        print(f"[Backfill] Final batch committed: +{len(batch_data)}")

    result = {
        "moved": moved,
        "skipped_missing": skipped_missing,
        "skipped_stub": skipped_stub,
    }
    print(f"\n[Backfill] Complete! Moved: {moved}, Skipped missing: {skipped_missing}, Skipped stubs: {skipped_stub}")
    return result


if __name__ == "__main__":
    run()
