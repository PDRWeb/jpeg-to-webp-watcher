import os
import time
import subprocess
import shutil
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

INPUT_DIR = os.environ.get("INPUT_DIR", "/data/input")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/data/output")

# WebP tuning (env overrides)
WEBP_QUALITY = os.environ.get("WEBP_QUALITY", "82")     # 0-100 (ignored if lossless)
WEBP_METHOD  = os.environ.get("WEBP_METHOD", "6")       # 0-6 (higher = slower/better)
WEBP_LOSSLESS = os.environ.get("WEBP_LOSSLESS", "false").lower() in ("1","true","yes","y")

# Choose ImageMagick binary (prefer 'magick' if present, else 'convert')
IM_BIN = shutil.which("magick") or shutil.which("convert")
if IM_BIN is None:
    raise RuntimeError("ImageMagick not found in PATH. Ensure it's installed in the container.")

stats = {"converted": 0, "skipped": 0, "errors": 0}

def is_jpeg(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in [".jpg", ".jpeg"]

def needs_conversion(src_path: str, dest_path: str) -> bool:
    """Convert if dest missing or source is newer."""
    if not os.path.exists(dest_path):
        return True
    return os.path.getmtime(src_path) > os.path.getmtime(dest_path)

def ensure_parent_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def build_im_cmd(src: str, dest: str) -> list:
    # Support both IM v6 ("convert") and v7 ("magick convert")
    if os.path.basename(IM_BIN) == "magick":
        base = [IM_BIN, "convert"]
    else:
        base = [IM_BIN]

    # Common flags:
    # -strip removes metadata; adjust if you want to keep EXIF/color profiles
    cmd = base + [src, "-strip"]

    # WebP tuning
    cmd += ["-define", f"webp:method={WEBP_METHOD}"]
    if WEBP_LOSSLESS:
        cmd += ["-define", "webp:lossless=true"]
    else:
        cmd += ["-quality", WEBP_QUALITY, "-define", "webp:auto-filter=true", "-define", "webp:image-hint=photo"]

    cmd += [dest]
    return cmd

def convert_to_webp(src_path: str, count_stats=True):
    if not is_jpeg(src_path):
        return

    rel_path = os.path.relpath(src_path, INPUT_DIR)
    dest_path = os.path.splitext(os.path.join(OUTPUT_DIR, rel_path))[0] + ".webp"
    ensure_parent_dir(dest_path)

    if needs_conversion(src_path, dest_path):
        try:
            cmd = build_im_cmd(src_path, dest_path)
            subprocess.run(cmd, check=True)
            print(f"[Converted] {src_path} → {dest_path}")
            if count_stats: stats["converted"] += 1
        except subprocess.CalledProcessError as e:
            print(f"[Error] Failed to convert {src_path}: {e}")
            if count_stats: stats["errors"] += 1
    else:
        print(f"[Skipped] {src_path} already up-to-date")
        if count_stats: stats["skipped"] += 1

class JpegHandler(PatternMatchingEventHandler):
    def __init__(self):
        super().__init__(
            patterns=["*.jpg", "*.jpeg", "*.JPG", "*.JPEG"],
            ignore_patterns=["*~", ".*.swp", "*.tmp", ".*.crdownload", ".*.part"],
            ignore_directories=False,
            case_sensitive=False,
        )

    def on_created(self, event):
        if not event.is_directory:
            # Small delay so apps that write in chunks finish writing
            time.sleep(0.15)
            convert_to_webp(event.src_path, count_stats=False)

    def on_modified(self, event):
        if not event.is_directory:
            time.sleep(0.15)
            convert_to_webp(event.src_path, count_stats=False)

if __name__ == "__main__":
    # Initial bulk scan
    print("🔄 Running initial scan...")
    for root, _, files in os.walk(INPUT_DIR):
        for f in files:
            full = os.path.join(root, f)
            if is_jpeg(full):
                convert_to_webp(full, count_stats=True)

    # Summary
    print("\n📊 Initial Scan Summary:")
    print(f"   ✅ Converted: {stats['converted']}")
    print(f"   ⏩ Skipped:   {stats['skipped']}")
    print(f"   ❌ Errors:    {stats['errors']}\n")

    # Start watching
    handler = JpegHandler()
    observer = Observer()
    observer.schedule(handler, INPUT_DIR, recursive=True)
    observer.start()
    print(f"📂 Watching {INPUT_DIR} for changes... (press Ctrl+C to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
