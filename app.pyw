import sys
import os
import json
import csv
import zipfile
import requests
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QTextEdit, QFileDialog,
    QGroupBox, QProgressBar
)
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QFont


def web_url_to_api_params(web_url: str) -> dict:
    """从观测页面 URL 提取 API 参数"""
    parsed = urlparse(web_url)
    params = parse_qs(parsed.query)
    return {k: v[0] if len(v) == 1 else v for k, v in params.items()}


def api_url_to_web_url(api_url: str) -> str:
    """将 API URL 转换为观测页面 URL"""
    parsed = urlparse(api_url)
    params = parse_qs(parsed.query)
    keep_params = ["nelat", "nelng", "swlat", "swlng", "taxon_id", "place_id"]
    web_params = {}
    for k in keep_params:
        if k in params:
            web_params[k] = params[k][0]
    return f"https://www.inaturalist.org/observations?{urlencode(web_params)}"


class FetchThread(QThread):
    """数据获取线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(list, int)
    error = pyqtSignal(str)

    def __init__(self, web_url):
        super().__init__()
        self.web_url = web_url

    def run(self):
        try:
            params = web_url_to_api_params(self.web_url)
            params["verifiable"] = "true"
            params["order_by"] = "id"
            params["order"] = "desc"
            params["spam"] = "false"
            params["locale"] = "zh-CN"
            params["per_page"] = 24
            params["fields"] = "(comments_count:!t,created_at:!t,created_at_details:all,created_time_zone:!t,faves_count:!t,geoprivacy:!t,id:!t,identifications:(current:!t),identifications_count:!t,location:!t,mappable:!t,obscured:!t,observed_on:!t,observed_on_details:all,observed_time_zone:!t,photos:(id:!t,url:!t),place_guess:!t,private_geojson:!t,quality_grade:!t,sounds:(id:!t),species_guess:!t,taxon:(iconic_taxon_id:!t,name:!t,preferred_common_name:!t,preferred_common_names:(name:!t),rank:!t,rank_level:!t),time_observed_at:!t,user:(icon_url:!t,id:!t,login:!t))"

            base_url = "https://api.inaturalist.org/v2/observations"
            per_page = 24
            all_results = []

            # 第一页
            params["page"] = 1
            self.progress.emit("正在获取第 1 页...")
            resp = requests.get(base_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            total_results = data.get("total_results", 0)
            total_pages = (total_results + per_page - 1) // per_page
            all_results.extend(data.get("results", []))
            self.progress.emit(f"共 {total_results} 条数据，{total_pages} 页")

            # 剩余页面
            for page in range(2, total_pages + 1):
                self.progress.emit(f"正在获取第 {page}/{total_pages} 页...")
                params["page"] = page
                resp = requests.get(base_url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                all_results.extend(data.get("results", []))
                time.sleep(1)

            self.finished.emit(all_results, total_results)

        except Exception as e:
            self.error.emit(str(e))


class DownloadThread(QThread):
    """图片下载线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(int, int)

    def __init__(self, results, output_dir):
        super().__init__()
        self.results = results
        self.output_dir = output_dir

    def run(self):
        os.makedirs(self.output_dir, exist_ok=True)
        downloaded = 0
        failed = 0

        for obs in self.results:
            obs_id = obs.get("id")
            photos = obs.get("photos", [])

            for idx, photo in enumerate(photos, 1):
                url = photo.get("url", "").replace("square", "large")
                filename = f"{obs_id}_{idx:02d}.jpg"
                filepath = os.path.join(self.output_dir, filename)

                if os.path.exists(filepath):
                    continue

                try:
                    resp = requests.get(url, timeout=30)
                    resp.raise_for_status()
                    with open(filepath, "wb") as f:
                        f.write(resp.content)
                    downloaded += 1
                    self.progress.emit(f"已下载: {filename}")
                except Exception as e:
                    failed += 1
                    self.progress.emit(f"失败: {filename}")

                time.sleep(0.3)

        self.finished.emit(downloaded, failed)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iNaturalist 观测数据下载工具")
        self.setMinimumSize(700, 500)

        self.results = []
        self.total_results = 0
        self.output_dir = ""

        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # URL 输入
        url_group = QGroupBox("观测地址")
        url_layout = QVBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("粘贴 iNaturalist 观测页面地址 (F12 之前的 URL)")
        url_layout.addWidget(self.url_input)

        btn_layout = QHBoxLayout()
        self.fetch_btn = QPushButton("获取数据")
        self.fetch_btn.clicked.connect(self.fetch_data)
        btn_layout.addWidget(self.fetch_btn)
        btn_layout.addStretch()
        url_layout.addLayout(btn_layout)
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)

        # 功能选项
        options_group = QGroupBox("功能选项")
        options_layout = QVBoxLayout()

        self.download_check = QCheckBox("下载图片 (large 高清原图)")
        options_layout.addWidget(self.download_check)

        self.pack_check = QCheckBox("打包结果 (zip)")
        options_layout.addWidget(self.pack_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # 操作按钮
        action_layout = QHBoxLayout()
        self.export_csv_btn = QPushButton("导出 CSV")
        self.export_csv_btn.setEnabled(False)
        self.export_csv_btn.clicked.connect(self.export_csv)
        action_layout.addWidget(self.export_csv_btn)

        self.run_btn = QPushButton("执行")
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self.run_tasks)
        action_layout.addWidget(self.run_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 日志
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

    def log(self, message):
        self.log_text.append(message)

    def fetch_data(self):
        url = self.url_input.text().strip()
        if not url:
            self.log("请输入观测地址")
            return

        if "inaturalist.org" not in url:
            self.log("请输入正确的 iNaturalist 地址")
            return

        self.fetch_btn.setEnabled(False)
        self.log("开始获取数据...")

        self.fetch_thread = FetchThread(url)
        self.fetch_thread.progress.connect(self.log)
        self.fetch_thread.finished.connect(self.on_fetch_finished)
        self.fetch_thread.error.connect(self.on_fetch_error)
        self.fetch_thread.start()

    def on_fetch_finished(self, results, total):
        self.results = results
        self.total_results = total
        self.fetch_btn.setEnabled(True)
        self.export_csv_btn.setEnabled(True)
        self.run_btn.setEnabled(True)
        self.log(f"数据获取完成，共 {len(results)} 条记录")

    def on_fetch_error(self, error):
        self.fetch_btn.setEnabled(True)
        self.log(f"获取失败: {error}")

    def get_output_dir(self):
        if not self.output_dir:
            self.output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(self.output_dir, exist_ok=True)
        return self.output_dir

    def export_csv(self):
        if not self.results:
            self.log("没有数据可导出")
            return

        output_dir = self.get_output_dir()
        csv_file = os.path.join(output_dir, "observations.csv")
        json_file = os.path.join(output_dir, "observations.json")

        # 保存 JSON (URL 已替换为 large)
        for obs in self.results:
            for photo in obs.get("photos", []):
                photo["url"] = photo["url"].replace("square", "large")

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({"total_results": self.total_results, "results": self.results}, f, ensure_ascii=False, indent=2)

        # 保存 CSV
        fieldnames = [
            "id", "species_guess", "scientific_name", "common_name_cn",
            "observed_on", "location", "place_guess", "user_login",
            "quality_grade", "identifications_count", "photos_count", "photo_urls"
        ]

        with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for obs in self.results:
                taxon = obs.get("taxon", {})
                photos = obs.get("photos", [])
                row = {
                    "id": obs.get("id"),
                    "species_guess": obs.get("species_guess"),
                    "scientific_name": taxon.get("name"),
                    "common_name_cn": taxon.get("preferred_common_name"),
                    "observed_on": obs.get("observed_on"),
                    "location": obs.get("location"),
                    "place_guess": obs.get("place_guess"),
                    "user_login": obs.get("user", {}).get("login"),
                    "quality_grade": obs.get("quality_grade"),
                    "identifications_count": obs.get("identifications_count"),
                    "photos_count": len(photos),
                    "photo_urls": ";".join(p.get("url", "") for p in photos)
                }
                writer.writerow(row)

        self.log(f"已导出: {csv_file}")
        self.log(f"已保存: {json_file}")

    def run_tasks(self):
        if not self.results:
            self.log("请先获取数据")
            return

        output_dir = self.get_output_dir()

        # 先导出 CSV
        self.export_csv()

        # 下载图片
        if self.download_check.isChecked():
            self.log("开始下载图片...")
            self.run_btn.setEnabled(False)
            self.export_csv_btn.setEnabled(False)

            photos_dir = os.path.join(output_dir, "photos")
            self.download_thread = DownloadThread(self.results, photos_dir)
            self.download_thread.progress.connect(self.log)
            self.download_thread.finished.connect(self.on_download_finished)
            self.download_thread.start()
        elif self.pack_check.isChecked():
            self.pack_results()

    def on_download_finished(self, downloaded, failed):
        self.run_btn.setEnabled(True)
        self.export_csv_btn.setEnabled(True)
        self.log(f"图片下载完成: 成功 {downloaded}, 失败 {failed}")

        if self.pack_check.isChecked():
            self.pack_results()

    def pack_results(self):
        output_dir = self.get_output_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"bird_observations_{timestamp}.zip"
        zip_path = os.path.join(output_dir, zip_name)

        web_url = self.url_input.text().strip()

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("source_url.txt", web_url)

            csv_file = os.path.join(output_dir, "observations.csv")
            if os.path.exists(csv_file):
                zf.write(csv_file, "observations.csv")

            json_file = os.path.join(output_dir, "observations.json")
            if os.path.exists(json_file):
                zf.write(json_file, "observations.json")

            photos_dir = os.path.join(output_dir, "photos")
            if os.path.exists(photos_dir) and self.download_check.isChecked():
                for filename in os.listdir(photos_dir):
                    filepath = os.path.join(photos_dir, filename)
                    zf.write(filepath, f"photos/{filename}")

        self.log(f"已打包: {zip_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
