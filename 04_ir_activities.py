"""
04_ir_activities.py - 投资者关系活动记录表 PDF 下载
来源：巨潮资讯 tabName=relation（投资者关系活动披露）
"""

import re
import time
import requests
from pathlib import Path
from datetime import datetime

from config import STOCKS, DATE_START, DATE_END, OUTPUT_DIR

CNINFO_QUERY = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_STATIC = "http://static.cninfo.com.cn/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "http://www.cninfo.com.cn/",
}
session = requests.Session()
session.headers.update(HEADERS)

_org_map: dict = {}


def _get_org_map() -> dict:
    global _org_map
    if _org_map:
        return _org_map
    try:
        r = session.get("http://www.cninfo.com.cn/new/data/szse_stock.json", timeout=10)
        _org_map = {item["code"]: item["orgId"] for item in r.json()["stockList"]}
    except Exception as e:
        print(f"  [警告] 获取orgId字典失败: {e}")
    return _org_map


def fetch_ir_announcements(code: str) -> list[dict]:
    """通过 tabName=relation 拉取投资者关系活动记录表列表"""
    org_map = _get_org_map()
    org_id = org_map.get(code, "")
    stock_item = f"{code},{org_id}" if org_id else code
    start = f"{DATE_START[:4]}-{DATE_START[5:7]}-{DATE_START[8:]}" if "-" in DATE_START \
            else f"{DATE_START[:4]}-{DATE_START[4:6]}-{DATE_START[6:]}"
    end   = f"{DATE_END[:4]}-{DATE_END[5:7]}-{DATE_END[8:]}" if "-" in DATE_END \
            else f"{DATE_END[:4]}-{DATE_END[4:6]}-{DATE_END[6:]}"

    results = []
    page = 1
    while True:
        try:
            payload = {
                "pageNum":   str(page),
                "pageSize":  "30",
                "column":    "szse",
                "tabName":   "relation",
                "plate":     "",
                "stock":     stock_item,
                "searchkey": "",
                "secid":     "",
                "category":  "",
                "trade":     "",
                "seDate":    f"{start}~{end}",
                "sortName":  "",
                "sortType":  "",
                "isHLtitle": "true",
            }
            r = session.post(CNINFO_QUERY, data=payload, timeout=15)
            data = r.json()
            anns = data.get("announcements") or []
            for a in anns:
                title = re.sub(r"<[^>]+>", "", a.get("announcementTitle", ""))
                adj   = a.get("adjunctUrl", "")
                ts_ms = a.get("announcementTime", 0)
                date  = datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d") if ts_ms else ""
                pdf_url = f"{CNINFO_STATIC}{adj}" if adj else ""
                if pdf_url:
                    results.append({"title": title, "date": date, "url": pdf_url})
            if not data.get("hasMore", False):
                break
            page += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"  [警告] 投资者关系活动查询失败(p{page}): {e}")
            break
    return results


def download_pdf(url: str, title: str, date: str, save_dir: Path) -> bool:
    safe_title = re.sub(r'[/\\:*?"<>|]', "-", title)[:60]
    filename   = f"{date}_{safe_title}.pdf"
    save_path  = save_dir / filename
    if save_path.exists():
        print(f"  [跳过] {filename}")
        return True
    try:
        r = session.get(url, timeout=30, stream=True)
        if r.status_code == 200 and "pdf" in r.headers.get("Content-Type", "").lower():
            with open(save_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            print(f"  [OK] {filename}")
            return True
        else:
            print(f"  [跳过] 非PDF或失败: {r.status_code} {filename}")
    except Exception as e:
        print(f"  [错误] {e}")
    return False


def run():
    base = Path(OUTPUT_DIR) / "pdfs"

    for stock in STOCKS:
        code = stock["code"]
        name = stock["name"]
        print(f"\n{'='*50}")
        print(f"处理: {name}({code})")

        save_dir = base / f"{code}_{name}" / "投资者关系活动"
        save_dir.mkdir(parents=True, exist_ok=True)

        anns = fetch_ir_announcements(code)
        print(f"  找到 {len(anns)} 条投资者关系活动记录")
        for ann in anns:
            download_pdf(ann["url"], ann["title"], ann["date"], save_dir)
            time.sleep(0.5)

        time.sleep(2)

    print("\n✅ 投资者关系活动PDF下载完成")


if __name__ == "__main__":
    run()
