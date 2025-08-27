import os
import subprocess
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Configuration ---
INPUT_DIR = os.environ.get("INPUT_DIR", "/data/input")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/data/output")
WEBP_QUALITY = int(os.environ.get("WEBP_QUALITY", 100))
WEBP_METHOD = int(os.environ.get("WEBP_METHOD", 4))
WEBP_LOSSLESS = os.environ.get("WEBP_LOSSLESS", "false").lower() == "true"

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# --- Conversion function ---
def convert_to_webp(src_path):
    basename = os.path.basename(src_path)
    
    # Ignore temp or network files
    if basename.startswith(".") or basename.startswith("~") or ".smbdelete" in basename:
        logging.debug(f"Ignored temporary file: {src_path}")
        return

    # Ensure file is a JPEG
    if not src_path.lower().endswith((".jpg", ".jpeg")):
        logging.debug(f"Skipped non-JPEG file: {src_path}")
        return

    # Determine destination path
    rel_path = os.path.relpath(src_path, INPUT_DIR)
    dest_path = os.path.join(OUTPUT_DIR, os.path.splitext(rel_path)[0] + ".webp")
    dest_dir = os.path.dirname(dest_path)
    os.makedirs(dest_dir, exist_ok=True)

    # Check modification time: convert if new or updated
    if os.path.exists(dest_path):
        src_mtime = os.path.getmtime(src_path)
        dest_mtime = os.path.getmtime(dest_path)
        if src_mtime <= dest_mtime:
            logging.info(f"Skipping (already processed): {src_path}")
            return

    # Retry if file is temporarily locked
    for attempt in range(3):
        try:
            cmd = [
                "magick", src_path, "-quality", str(WEBP_QUALITY),
                "-define", f"webp:method={WEBP_METHOD}",
                "-define", f"webp:lossless={'true' if WEBP_LOSSLESS else 'false'}",
                dest_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info(f"[Converted] {src_path} → {dest_path}")
            break
        except (PermissionError, subprocess.CalledProcessError) as e:
            logging.warning(f"[Retry {attempt+1}] Failed to convert {src_path}: {e}")
            time.sleep(2)
    else:
        logging.error(f"Failed to convert after retries: {src_path}")

# --- Watchdog event handler ---
class JpegHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            logging.info(f"Detected new file: {event.src_path}")
            convert_to_webp(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            logging.info(f"Detected modified file: {event.src_path}")
            convert_to_webp(event.src_path)

# --- Main observer ---
if __name__ == "__main__":
    logging.info(f"Starting watcher on {INPUT_DIR}, output to {OUTPUT_DIR}")
    observer = Observer()
    observer.schedule(JpegHandler(), INPUT_DIR, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping watcher...")
        observer.stop()
    observer.join()
