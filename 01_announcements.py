"""
01_announcements.py - 用akshare抓取公告，绕开cninfo反爬
"""

import time
import requests
from pathlib import Path
from urllib.parse import urlparse, parse_qs

try:
    import akshare as ak
except ImportError:
    print("请先安装: pip install akshare")
    raise

from config import STOCKS, DATE_START, DATE_END, IMPORTANT_KEYWORDS, OUTPUT_DIR

CNINFO_BASE = "http://static.cninfo.com.cn/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}
session = requests.Session()
session.headers.update(HEADERS)


def cninfo_detail_to_pdf(url: str) -> str:
    """将巨潮详情页URL转换为静态PDF下载URL
    detail: http://www.cninfo.com.cn/new/disclosure/detail?...&announcementId=XXX&announcementTime=YYYY-MM-DD
    pdf:    http://static.cninfo.com.cn/finalpage/YYYY-MM-DD/XXX.PDF
    """
    try:
        params = parse_qs(urlparse(url).query)
        ann_id = params.get("announcementId", [None])[0]
        ann_time = params.get("announcementTime", [None])[0]
        if ann_id and ann_time:
            return f"http://static.cninfo.com.cn/finalpage/{ann_time}/{ann_id}.PDF"
    except Exception:
        pass
    return url


def _cninfo_rows(df) -> list:
    """从stock_zh_a_disclosure_report_cninfo的DataFrame提取统一格式"""
    results = []
    if df is None or df.empty:
        return results
    for _, row in df.iterrows():
        detail_url = str(row.get("公告链接", ""))
        results.append({
            "title": str(row.get("公告标题", "")),
            "date":  str(row.get("公告时间", ""))[:10],
            "url":   cninfo_detail_to_pdf(detail_url),
        })
    return results


def fetch_periodic_reports(code: str) -> list:
    """定期报告：年报/半年报/季报"""
    results = []
    categories = ["年报", "半年报", "一季报", "三季报"]
    start = DATE_START.replace("-", "")
    end   = DATE_END.replace("-", "")
    for cat in categories:
        try:
            df = ak.stock_zh_a_disclosure_report_cninfo(
                symbol=code,
                market="沪深京",
                category=cat,
                start_date=start,
                end_date=end,
            )
            results.extend(_cninfo_rows(df))
        except Exception as e:
            print(f"  [警告] 定期报告({cat})接口失败: {e}")
        time.sleep(0.3)
    return results


def fetch_all_announcements(code: str, market: str) -> list:
    """全部公告（akshare封装cninfo）"""
    try:
        df = ak.stock_zh_a_disclosure_report_cninfo(
            symbol=code,
            market="沪深京",
            category="",
            start_date=DATE_START.replace("-", ""),
            end_date=DATE_END.replace("-", ""),
        )
        return _cninfo_rows(df)
    except Exception as e:
        print(f"  [警告] 公告接口失败: {e}")
        return []


def download_pdf_by_url(url: str, title: str, date: str, save_dir: Path) -> bool:
    if not url or url == "nan":
        return False

    # 补全url
    if url.startswith("/"):
        url = CNINFO_BASE + url.lstrip("/")

    safe_title = title.replace("/", "-").replace("\\", "-")[:60]
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
    base = Path(OUTPUT_DIR)

    for stock in STOCKS:
        code   = stock["code"]
        name   = stock["name"]
        market = stock["market"]
        print(f"\n{'='*50}")
        print(f"处理: {name}({code})")

        # ── 定期报告 ──────────────────────────────────────
        save_dir = base / "pdfs" / f"{code}_{name}" / "定期报告"
        save_dir.mkdir(parents=True, exist_ok=True)
        print(f"  查询定期报告...")
        periodic = fetch_periodic_reports(code)
        print(f"  找到 {len(periodic)} 条")
        for ann in periodic:
            download_pdf_by_url(ann["url"], ann["title"], ann["date"], save_dir)
            time.sleep(0.5)

        # ── 临时公告（关键词过滤）────────────────────────
        save_dir = base / "pdfs" / f"{code}_{name}" / "重要临时公告"
        save_dir.mkdir(parents=True, exist_ok=True)
        print(f"  查询临时公告...")
        all_anns = fetch_all_announcements(code, market)
        important = [
            a for a in all_anns
            if any(kw in a["title"] for kw in IMPORTANT_KEYWORDS)
        ]
        print(f"  找到重要公告 {len(important)} 条（共{len(all_anns)}条）")
        for ann in important:
            download_pdf_by_url(ann["url"], ann["title"], ann["date"], save_dir)
            time.sleep(0.5)

        time.sleep(2)

    print("\n✅ 公告下载完成")


if __name__ == "__main__":
    run()
