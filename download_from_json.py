import json
import os
import requests
import time

def download_photos(json_file: str = "observations.json", output_dir: str = "photos"):
    """从 JSON 文件下载所有图片"""

    os.makedirs(output_dir, exist_ok=True)

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("results", [])
    print(f"Total observations: {len(results)}")

    downloaded = 0
    failed = 0
    skipped = 0

    for obs in results:
        obs_id = obs.get("id")
        photos = obs.get("photos", [])

        for idx, photo in enumerate(photos, 1):
            url = photo.get("url", "")
            filename = f"{obs_id}_{idx:02d}.jpg"
            filepath = os.path.join(output_dir, filename)

            if os.path.exists(filepath):
                skipped += 1
                continue

            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                downloaded += 1
                print(f"[{downloaded}] Saved: {filename}")
            except Exception as e:
                failed += 1
                print(f"Failed: {filename} - {e}")

            time.sleep(0.3)

    print(f"\n=== Done ===")
    print(f"Downloaded: {downloaded}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print(f"Total in folder: {len(os.listdir(output_dir))}")

if __name__ == "__main__":
    download_photos()
