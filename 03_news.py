"""
03_news.py
从东方财富采集每支股票的最新资讯，保存为 Markdown
"""

import time
import warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

try:
    import akshare as ak
except ImportError:
    print("请先安装: pip install akshare")
    raise

from config import STOCKS, MAX_NEWS, OUTPUT_DIR


def fetch_stock_news(code: str, max_count: int = 50) -> list[dict]:
    """东方财富股票资讯"""
    try:
        df = ak.stock_news_em(symbol=code)
        if df.empty:
            return []
        # 统一列名
        df.columns = [c.strip() for c in df.columns]
        results = []
        for _, row in df.head(max_count).iterrows():
            results.append({
                "time":    str(row.get("发布时间", row.get("datetime", ""))),
                "title":   str(row.get("新闻标题", row.get("title", ""))),
                "content": str(row.get("新闻内容", row.get("content", ""))),
                "source":  str(row.get("文章来源", row.get("source", ""))),
            })
        return results
    except Exception as e:
        print(f"  [警告] 新闻获取失败 {code}: {e}")
        return []


def fetch_industry_news(keyword: str = "半导体 光模块 PCB AI芯片") -> list[dict]:
    """财联社快讯（行业新闻）"""
    try:
        df = ak.stock_info_global_cls(symbol="全部")
        if df.empty:
            return []
        kws = keyword.split()
        results = []
        for _, row in df.iterrows():
            content = str(row.get("内容", ""))
            title   = str(row.get("标题", ""))
            text    = content + title
            if any(kw in text for kw in kws):
                results.append({
                    "time":    f"{row.get('发布日期', '')} {row.get('发布时间', '')}",
                    "content": content or title,
                    "source":  "财联社",
                })
            if len(results) >= 30:
                break
        return results
    except Exception as e:
        print(f"  [警告] 行业快讯失败: {e}")
        return []


def news_to_markdown(stock: dict, news_list: list[dict]) -> str:
    code = stock["code"]
    name = stock["name"]
    now  = datetime.now().strftime("%Y-%m-%d")

    md  = f"# {name}（{code}）近期资讯\n\n"
    md += f"> 采集时间：{now} | 共 {len(news_list)} 条\n\n"

    for i, item in enumerate(news_list, 1):
        title   = item.get("title", "")
        content = item.get("content", "")
        t       = item.get("time", "")
        source  = item.get("source", "")

        if title:
            md += f"## {i}. {title}\n\n"
        else:
            md += f"## {i}. 快讯\n\n"

        if t or source:
            md += f"**时间**：{t}  **来源**：{source}\n\n"

        if content and content != "nan":
            # 截取前800字
            preview = content[:800]
            if len(content) > 800:
                preview += "……"
            md += preview + "\n\n"

        md += "---\n\n"

    return md


def run():
    base = Path(OUTPUT_DIR) / "news"
    base.mkdir(parents=True, exist_ok=True)

    for stock in STOCKS:
        code = stock["code"]
        name = stock["name"]
        print(f"\n{'='*50}")
        print(f"处理: {name}({code})")

        news = fetch_stock_news(code, MAX_NEWS)
        print(f"  获取到 {len(news)} 条资讯")

        out_file = base / f"{code}_{name}_资讯.md"
        if out_file.exists():
            print(f"  [跳过] 已存在: {out_file.name}")
        elif news:
            md = news_to_markdown(stock, news)
            out_file.write_text(md, encoding="utf-8")
            print(f"  ✅ 已保存: {out_file.name}")
        else:
            print(f"  ⚠️  无资讯数据")

        time.sleep(1.5)

    # ── 行业整体快讯 ──────────────────────────
    print(f"\n{'='*50}")
    print("获取行业快讯（半导体/光模块/PCB/AI芯片）...")
    industry = fetch_industry_news()
    print(f"  获取到 {len(industry)} 条")
    if industry:
        md  = "# 行业快讯（半导体/光模块/PCB/AI芯片）\n\n"
        md += f"> 来源：财联社 | 共 {len(industry)} 条\n\n"
        for i, item in enumerate(industry, 1):
            md += f"## {i}. {item.get('time', '')}\n\n"
            md += item.get("content", "") + "\n\n---\n\n"
        out_file = base / "_行业快讯.md"
        out_file.write_text(md, encoding="utf-8")
        print(f"  ✅ 已保存: _行业快讯.md")

    print("\n✅ 新闻资讯采集完成")


if __name__ == "__main__":
    run()
