"""
04_ir_activities.py - 机构调研 / 投资者关系活动记录
来源：东方财富网-数据中心-特色数据-机构调研
https://data.eastmoney.com/jgdy/
"""

import time
import requests
from pathlib import Path
from datetime import datetime

from config import STOCKS, DATE_START, OUTPUT_DIR

URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

# 活动类型代码映射
WAY_MAP = {
    "001": "实地调研",
    "002": "电话交流",
    "003": "视频交流",
    "004": "业绩说明会",
    "005": "网络互动",
    "006": "新闻发布会",
    "007": "现场参观",
    "008": "业绩说明会",
}

# 接待对象类型
OBJECT_TYPE_MAP = {
    "001": "机构投资者",
    "002": "个人投资者",
    "003": "其他投资者",
    "004": "分析师",
    "005": "媒体",
}


def fetch_ir_activities(code: str, start_date: str, max_records: int = 50) -> list[dict]:
    """从东方财富获取指定股票的机构调研/投资者关系活动记录"""
    results = []
    page = 1
    start_str = f"{start_date[:4]}-{start_date[5:7]}-{start_date[8:]}" if "-" in start_date else \
                f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"

    while len(results) < max_records:
        try:
            params = {
                "reportName":  "RPT_ORG_SURVEYNEW",
                "columns":     "ALL",
                "sortColumns": "NOTICE_DATE,RECEIVE_START_DATE",
                "sortTypes":   "-1,-1",
                "pageNumber":  page,
                "pageSize":    50,
                "filter":      f'(SECURITY_CODE="{code}")(NOTICE_DATE>\'{start_str}\')',
                "source":      "WEB",
                "client":      "WEB",
            }
            r = requests.get(URL, params=params, headers=HEADERS, timeout=15)
            data = r.json()

            result_data = data.get("result")
            if not result_data or not result_data.get("data"):
                break

            items = result_data["data"]
            for item in items:
                results.append({
                    "公告日期": str(item.get("NOTICE_DATE", ""))[:10],
                    "接待日期": str(item.get("RECEIVE_START_DATE", ""))[:10],
                    "时间说明": item.get("RECEIVE_TIME_EXPLAIN") or "",
                    "活动方式": item.get("RECEIVE_WAY_EXPLAIN") or WAY_MAP.get(item.get("RECEIVE_WAY", ""), ""),
                    "接待地点": item.get("RECEIVE_PLACE") or "",
                    "接待对象": item.get("RECEIVE_OBJECT") or OBJECT_TYPE_MAP.get(item.get("RECEIVE_OBJECT_TYPE", ""), ""),
                    "公司接待人": item.get("RECEPTIONIST") or "",
                    "参与机构": item.get("INVESTIGATORS") or "",
                    "备注":     item.get("REMARK") or "",
                })
                if len(results) >= max_records:
                    break

            total_pages = result_data.get("pages", 1)
            if page >= total_pages:
                break
            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"  [警告] 获取机构调研失败(p{page}): {e}")
            break

    return results


def activities_to_markdown(stock: dict, activities: list[dict]) -> str:
    code = stock["code"]
    name = stock["name"]
    now  = datetime.now().strftime("%Y-%m-%d")

    md  = f"# {name}（{code}）投资者关系活动记录\n\n"
    md += f"> 数据来源：东方财富 | 采集时间：{now} | 共 {len(activities)} 条\n\n"

    for i, item in enumerate(activities, 1):
        way  = item["活动方式"]
        date = item["接待日期"] or item["公告日期"]
        md += f"## {i}. {date}  {way}\n\n"

        if item["时间说明"]:
            md += f"**时间**：{item['时间说明']}\n\n"
        if item["接待地点"]:
            md += f"**地点**：{item['接待地点']}\n\n"
        if item["接待对象"]:
            md += f"**接待对象**：{item['接待对象']}\n\n"
        if item["公司接待人"]:
            md += f"**公司接待人**：{item['公司接待人']}\n\n"
        if item["参与机构"]:
            md += f"**参与机构**：{item['参与机构']}\n\n"
        if item["备注"]:
            md += f"**备注**：{item['备注']}\n\n"

        md += "---\n\n"

    return md


def run():
    base = Path(OUTPUT_DIR) / "ir"
    base.mkdir(parents=True, exist_ok=True)

    for stock in STOCKS:
        code = stock["code"]
        name = stock["name"]
        print(f"\n{'='*50}")
        print(f"处理: {name}({code})")

        activities = fetch_ir_activities(code, start_date=DATE_START)
        print(f"  获取到 {len(activities)} 条活动记录")

        out_file = base / f"{code}_{name}_投资者关系活动.md"
        if activities:
            md = activities_to_markdown(stock, activities)
            out_file.write_text(md, encoding="utf-8")
            print(f"  ✅ 已保存: {out_file.name}")
        else:
            print(f"  ⚠️  无活动记录")

        time.sleep(1.5)

    print("\n✅ 投资者关系活动采集完成")


if __name__ == "__main__":
    run()
