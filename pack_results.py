import json
import os
import re
import zipfile
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode

def api_url_to_web_url(api_url: str) -> str:
    """将 API URL 转换为观测页面 URL"""
    parsed = urlparse(api_url)
    params = parse_qs(parsed.query)

    # 只保留地理和分类相关的参数
    keep_params = ["nelat", "nelng", "swlat", "swlng", "taxon_id", "place_id"]
    web_params = {}
    for k in keep_params:
        if k in params:
            web_params[k] = params[k][0]

    return f"https://www.inaturalist.org/observations?{urlencode(web_params)}"

def pack_results(
    photos_dir: str = "photos",
    json_file: str = "observations.json",
    csv_file: str = "observations.csv",
    url_file: str = "url.txt",
    output_dir: str = "."
):
    """打包所有结果文件"""

    # 读取 API URL 并转换为网页 URL
    with open(url_file, "r", encoding="utf-8") as f:
        api_url = f.read().strip()
    web_url = api_url_to_web_url(api_url)

    # 生成压缩文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"bird_observations_{timestamp}.zip"
    zip_path = os.path.join(output_dir, zip_name)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 写入观测页面 URL
        zf.writestr("source_url.txt", web_url)

        # 打包 JSON
        if os.path.exists(json_file):
            zf.write(json_file, json_file)
            print(f"Added: {json_file}")

        # 打包 CSV
        if os.path.exists(csv_file):
            zf.write(csv_file, csv_file)
            print(f"Added: {csv_file}")

        # 打包图片
        if os.path.exists(photos_dir):
            photo_count = 0
            for filename in sorted(os.listdir(photos_dir)):
                filepath = os.path.join(photos_dir, filename)
                zf.write(filepath, os.path.join(photos_dir, filename))
                photo_count += 1
            print(f"Added: {photos_dir}/ ({photo_count} photos)")

    print(f"\nCreated: {zip_path}")
    print(f"Web URL: {web_url}")

if __name__ == "__main__":
    pack_results()
