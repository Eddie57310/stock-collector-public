"""
main.py - 一键运行所有采集模块
"""

import sys
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="A股研究资料采集工具")
    parser.add_argument(
        "--module", "-m",
        choices=["all", "ann", "fin", "news"],
        default="all",
        help="采集模块: all=全部 ann=公告PDF fin=财务数据 news=新闻"
    )
    args = parser.parse_args()

    # 创建输出目录
    Path("./output/pdfs").mkdir(parents=True, exist_ok=True)
    Path("./output/financials").mkdir(parents=True, exist_ok=True)
    Path("./output/news").mkdir(parents=True, exist_ok=True)

    if args.module in ("all", "ann"):
        print("\n" + "="*60)
        print("📄 模块1: 巨潮资讯公告PDF下载")
        print("="*60)
        import importlib, sys
        import01 = importlib.import_module("01_announcements")
        import01.run()

    if args.module in ("all", "fin"):
        print("\n" + "="*60)
        print("📊 模块2: 财务数据采集")
        print("="*60)
        import importlib
        import02 = importlib.import_module("02_financials")
        import02.run()

    if args.module in ("all", "news"):
        print("\n" + "="*60)
        print("📰 模块3: 新闻资讯采集")
        print("="*60)
        import importlib
        import03 = importlib.import_module("03_news")
        import03.run()

    print("\n" + "="*60)
    print("🎉 全部完成！输出目录结构：")
    for p in sorted(Path("./output").rglob("*")):
        depth = len(p.relative_to("./output").parts) - 1
        print("  " + "  " * depth + p.name)


if __name__ == "__main__":
    # importlib 无法直接处理以数字开头的模块名，用 runpy 替代
    import runpy, sys

    parser = argparse.ArgumentParser()
    parser.add_argument("--module", "-m",
                        choices=["all", "ann", "fin", "news"], default="all")
    args = parser.parse_args()

    Path("./output/pdfs").mkdir(parents=True, exist_ok=True)
    Path("./output/financials").mkdir(parents=True, exist_ok=True)
    Path("./output/news").mkdir(parents=True, exist_ok=True)

    if args.module in ("all", "ann"):
        print("\n📄 模块1: 巨潮资讯公告PDF下载")
        runpy.run_path("01_announcements.py", run_name="__main__")

    if args.module in ("all", "fin"):
        print("\n📊 模块2: 财务数据采集")
        runpy.run_path("02_financials.py", run_name="__main__")

    if args.module in ("all", "news"):
        print("\n📰 模块3: 新闻资讯采集")
        runpy.run_path("03_news.py", run_name="__main__")

    print("\n✅ 全部完成！")
