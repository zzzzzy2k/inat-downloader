import json
import requests
import time
from urllib.parse import urlparse, parse_qs

def fetch_all_observations(url_file: str = "url.txt", output_file: str = "observations.json"):
    """从 url.txt 分页获取所有观测数据并保存"""

    with open(url_file, "r", encoding="utf-8") as f:
        base_url = f.read().strip()

    parsed = urlparse(base_url)
    params = parse_qs(parsed.query)
    params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

    per_page = int(params.get("per_page", 24))
    all_results = []

    # 第一页
    params["page"] = 1
    print("Fetching page 1...")
    resp = requests.get(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    total_results = data.get("total_results", 0)
    total_pages = (total_results + per_page - 1) // per_page
    all_results.extend(data.get("results", []))

    print(f"Total results: {total_results}, Total pages: {total_pages}")

    # 剩余页面
    for page in range(2, total_pages + 1):
        print(f"Fetching page {page}/{total_pages}...")
        params["page"] = page
        resp = requests.get(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        all_results.extend(data.get("results", []))
        time.sleep(1)

    # 将 photo URL 替换为 large
    for obs in all_results:
        for photo in obs.get("photos", []):
            photo["url"] = photo["url"].replace("square", "large")

    # 保存
    output = {"total_results": total_results, "results": all_results}
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(all_results)} observations to {output_file}")
    print(f"Photo URLs updated: square -> large")

if __name__ == "__main__":
    fetch_all_observations()
