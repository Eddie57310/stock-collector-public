"""
02_financials.py - 增量财务数据采集
已有的报告期数据不重复写，只追加新报告期
"""

import re
import time
import warnings
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

try:
    import akshare as ak
except ImportError:
    print("请先安装: pip install akshare")
    raise

from config import STOCKS, OUTPUT_DIR

# ── 列名映射 ──────────────────────────────────────────────

PROFIT_COLS = {
    "REPORT_DATE_NAME":        "报告期",
    "TOTAL_OPERATE_INCOME":    "营业总收入",
    "OPERATE_COST":            "营业成本",
    "OPERATE_PROFIT":          "营业利润",
    "TOTAL_PROFIT":            "利润总额",
    "NETPROFIT":               "净利润",
    "PARENT_NETPROFIT":        "归母净利润",
    "DEDUCT_PARENT_NETPROFIT": "扣非归母净利润",
    "RESEARCH_EXPENSE":        "研发费用",
    "BASIC_EPS":               "基本每股收益",
    "TOTAL_OPERATE_INCOME_YOY":"营业总收入同比(%)",
    "PARENT_NETPROFIT_YOY":    "归母净利润同比(%)",
}
BALANCE_COLS = {
    "REPORT_DATE_NAME":  "报告期",
    "TOTAL_ASSETS":      "资产总计",
    "TOTAL_LIABILITIES": "负债合计",
    "TOTAL_EQUITY":      "股东权益合计",
    "MONETARYFUNDS":     "货币资金",
    "ACCOUNTS_RECE":     "应收账款",
    "INVENTORY":         "存货",
    "SHORT_LOAN":        "短期借款",
    "LONG_LOAN":         "长期借款",
}
CASHFLOW_COLS = {
    "REPORT_DATE_NAME": "报告期",
    "NETCASH_OPERATE":  "经营活动净现金流",
    "NETCASH_INVEST":   "投资活动净现金流",
    "NETCASH_FINANCE":  "筹资活动净现金流",
    "FREE_CASHFLOW":    "自由现金流",
}

# ── 工具函数 ──────────────────────────────────────────────

def _select_rename(df, col_map):
    keep = {k: v for k, v in col_map.items() if k in df.columns}
    return df[list(keep.keys())].rename(columns=keep)

def _fmt_val(x, is_pct=False, is_eps=False):
    try:
        v = float(x)
        if is_pct:  return f"{v:.1f}%"
        if is_eps:  return f"{v:.2f}"
        return f"{v/1e8:.2f}亿"
    except Exception:
        return "-"

def _fmt_df(df):
    pct_cols = {c for c in df.columns if "同比" in c or "环比" in c or "率" in c}
    eps_cols  = {"基本每股收益"}
    for col in df.columns:
        if col == "报告期": continue
        df[col] = df[col].apply(
            lambda x: _fmt_val(x, col in pct_cols, col in eps_cols)
        )
    return df

def df_to_md(df) -> str:
    lines = ["| " + " | ".join(str(h) for h in df.columns) + " |",
             "| " + " | ".join(["---"] * len(df.columns)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)

def parse_existing_periods(md_path: Path) -> set:
    """从已有md文件中提取所有报告期，避免重复写入"""
    if not md_path.exists():
        return set()
    text = md_path.read_text(encoding="utf-8")
    # 匹配表格中形如 2024年报 / 2025一季报 / 2024三季报 的值
    return set(re.findall(r'\d{4}(?:年报|中报|一季报|三季报|半年报|季报)', text))

def filter_new_rows(df: pd.DataFrame, existing: set) -> pd.DataFrame:
    """只保留报告期不在existing中的行"""
    if df is None or df.empty:
        return df
    return df[~df["报告期"].isin(existing)].reset_index(drop=True)

# ── 各数据模块 ────────────────────────────────────────────

def get_profit_table(code, market):
    sym = ("sh" if market == "sh" else "sz") + code
    try:
        df = ak.stock_profit_sheet_by_report_em(symbol=sym)
        df = _select_rename(df, PROFIT_COLS)
        return _fmt_df(df)
    except Exception as e:
        print(f"  [警告] 利润表失败: {e}"); return None

def get_balance_table(code, market):
    sym = ("sh" if market == "sh" else "sz") + code
    try:
        df = ak.stock_balance_sheet_by_report_em(symbol=sym)
        df = _select_rename(df, BALANCE_COLS)
        return _fmt_df(df)
    except Exception as e:
        print(f"  [警告] 资产负债表失败: {e}"); return None

def get_cashflow_table(code, market):
    sym = ("sh" if market == "sh" else "sz") + code
    try:
        df = ak.stock_cash_flow_sheet_by_report_em(symbol=sym)
        df = _select_rename(df, CASHFLOW_COLS)
        return _fmt_df(df)
    except Exception as e:
        print(f"  [警告] 现金流量表失败: {e}"); return None

def get_quality_metrics(code, market):
    sym = ("sh" if market == "sh" else "sz") + code
    try:
        profit  = ak.stock_profit_sheet_by_report_em(symbol=sym)
        balance = ak.stock_balance_sheet_by_report_em(symbol=sym)
        rows = []
        for i in range(min(8, len(profit))):
            try:
                p = profit.iloc[i]
                b = balance.iloc[i] if i < len(balance) else None
                rev    = float(p.get("TOTAL_OPERATE_INCOME", 0) or 0)
                cost   = float(p.get("OPERATE_COST", 0) or 0)
                net    = float(p.get("NETPROFIT", 0) or 0)
                pnet   = float(p.get("PARENT_NETPROFIT", 0) or 0)
                eq     = float(b.get("TOTAL_EQUITY", 0) or 0) if b is not None else 0
                assets = float(b.get("TOTAL_ASSETS", 0) or 0) if b is not None else 0
                rows.append({
                    "报告期": p.get("REPORT_DATE_NAME", ""),
                    "毛利率": f"{(rev-cost)/rev*100:.1f}%" if rev else "-",
                    "净利率": f"{net/rev*100:.1f}%"        if rev else "-",
                    "ROE":    f"{pnet/eq*100:.1f}%"         if eq   else "-",
                    "ROA":    f"{net/assets*100:.1f}%"      if assets else "-",
                })
            except Exception:
                continue
        return pd.DataFrame(rows) if rows else None
    except Exception as e:
        print(f"  [警告] 盈利质量失败: {e}"); return None

def get_qoq_growth(code, market):
    sym = ("sh" if market == "sh" else "sz") + code
    try:
        df = ak.stock_profit_sheet_by_report_em(symbol=sym).head(9)
        rows = []
        for i in range(min(8, len(df)-1)):
            cur, prv = df.iloc[i], df.iloc[i+1]
            def qoq(col):
                try:
                    c, p = float(cur.get(col,0) or 0), float(prv.get(col,0) or 0)
                    return f"{(c-p)/abs(p)*100:.1f}%" if p else "-"
                except: return "-"
            rows.append({
                "报告期":         cur.get("REPORT_DATE_NAME",""),
                "营收环比":       qoq("TOTAL_OPERATE_INCOME"),
                "归母净利润环比": qoq("PARENT_NETPROFIT"),
                "研发费用环比":   qoq("RESEARCH_EXPENSE"),
            })
        return pd.DataFrame(rows) if rows else None
    except Exception as e:
        print(f"  [警告] 环比增速失败: {e}"); return None

def get_monthly_price(code, market):
    prefix = "sh" if market == "sh" else "sz"
    for attempt in range(3):
        try:
            if attempt > 0:
                time.sleep(5 * attempt)
            df = ak.stock_zh_a_hist_tx(
                symbol=f"{prefix}{code}",
                start_date="20220101",
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust="qfq",
            )
            if df is None or df.empty:
                return None
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            monthly = df.resample("ME").agg(
                {"open": "first", "close": "last", "high": "max", "low": "min", "amount": "sum"}
            ).dropna()
            monthly["涨跌幅"] = monthly["close"].pct_change() * 100
            monthly = monthly.reset_index()
            monthly.columns = ["日期", "开盘", "收盘", "最高", "最低", "成交量", "涨跌幅"]
            monthly["日期"] = monthly["日期"].dt.strftime("%Y-%m-%d")
            monthly["成交量"] = monthly["成交量"].apply(
                lambda x: f"{float(x)/10000:.1f}万手" if str(x) not in ("nan", "") else "-"
            )
            monthly["涨跌幅"] = monthly["涨跌幅"].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) else "-"
            )
            return monthly
        except Exception as e:
            print(f"  [警告] 月度股价失败(第{attempt+1}次): {e}")
    return None

def get_dividend_history(code):
    try:
        df = ak.stock_history_dividend_detail(symbol=code, indicator="分红")
        return df.head(10) if df is not None and not df.empty else None
    except Exception:
        try:
            df = ak.stock_dividend_cninfo(symbol=code)
            return df.head(10) if df is not None and not df.empty else None
        except Exception as e:
            print(f"  [警告] 分红历史失败: {e}"); return None

def get_spot_info(code, market):
    prefix = "sh" if market == "sh" else "sz"
    result = {}
    # Latest price via Tencent hist API
    for attempt in range(3):
        try:
            if attempt > 0:
                time.sleep(5 * attempt)
            since = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
            df = ak.stock_zh_a_hist_tx(
                symbol=f"{prefix}{code}",
                start_date=since,
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust="qfq",
            )
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                prev   = df.iloc[-2] if len(df) >= 2 else latest
                chg    = (latest["close"] - prev["close"]) / prev["close"] * 100
                result["最新价(元)"]  = latest["close"]
                result["涨跌幅(%)"]   = f"{chg:.2f}"
            break
        except Exception as e:
            print(f"  [警告] 行情快照失败(第{attempt+1}次): {e}")
    # Valuation metrics via Baidu
    for indicator, key in [("总市值", "总市值(亿)"), ("市盈率(TTM)", "市盈率PE-TTM"), ("市净率", "市净率PB")]:
        try:
            vdf = ak.stock_zh_valuation_baidu(symbol=code, indicator=indicator, period="近一年")
            if vdf is not None and not vdf.empty:
                val = float(vdf.iloc[-1]["value"])
                result[key] = f"{val:.1f}亿" if key == "总市值(亿)" else f"{val:.2f}"
            time.sleep(0.3)
        except Exception:
            pass
    return result

# ── 增量更新核心逻辑 ──────────────────────────────────────

def update_section(existing_text: str, section_title: str, new_df: pd.DataFrame) -> str:
    """
    在已有md文本中，找到对应section，把新行插到表格顶部。
    如果section不存在则追加到文件末尾（---之前）。
    """
    if new_df is None or new_df.empty:
        return existing_text

    new_rows_md = "\n".join(
        "| " + " | ".join(str(v) for v in row) + " |"
        for _, row in new_df.iterrows()
    )

    # 找到 section 标题后的表格，在表头分隔行之后插入新行
    pattern = rf'(## {re.escape(section_title)}.*?\n\|[^\n]+\|\n\|[-| ]+\|\n)'
    match = re.search(pattern, existing_text, re.DOTALL)
    if match:
        insert_pos = match.end()
        return existing_text[:insert_pos] + new_rows_md + "\n" + existing_text[insert_pos:]
    else:
        # section不存在，追加到 --- 之前
        footer = "\n---\n*以上数据仅供研究参考，不构成投资建议*\n"
        header = df_to_md(new_df)
        new_section = f"\n## {section_title}\n\n{header}\n\n"
        return existing_text.replace(footer, new_section + footer)

# ── 主函数 ────────────────────────────────────────────────

def run():
    base = Path(OUTPUT_DIR) / "financials"
    base.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d")

    for stock in STOCKS:
        code   = stock["code"]
        name   = stock["name"]
        market = stock["market"]
        out    = base / f"{code}_{name}_财务摘要.md"

        print(f"\n{'='*50}")
        print(f"处理: {name}({code})")

        # 读取已有报告期
        existing_periods = parse_existing_periods(out)
        is_new_file = not out.exists()

        if existing_periods:
            print(f"  已有报告期: {sorted(existing_periods, reverse=True)}")

        # ── 全量拉取（API每次都返回最新N期）──
        print(f"  [1/7] 行情快照...")
        spot = get_spot_info(code, market); time.sleep(0.5)

        print(f"  [2/7] 利润表...")
        profit_all = get_profit_table(code, market); time.sleep(0.5)

        print(f"  [3/7] 盈利质量...")
        quality_all = get_quality_metrics(code, market); time.sleep(0.5)

        print(f"  [4/7] 环比增速...")
        qoq_all = get_qoq_growth(code, market); time.sleep(0.5)

        print(f"  [5/7] 资产负债表...")
        balance_all = get_balance_table(code, market); time.sleep(0.5)

        print(f"  [6/7] 现金流量表...")
        cashflow_all = get_cashflow_table(code, market); time.sleep(0.5)

        print(f"  [7/7] 月度股价+分红...")
        price_all = get_monthly_price(code, market); time.sleep(0.3)
        div_all   = get_dividend_history(code); time.sleep(0.5)

        # ── 过滤出新报告期 ──────────────────────
        profit_new   = filter_new_rows(profit_all,  existing_periods)
        quality_new  = filter_new_rows(quality_all, existing_periods)
        qoq_new      = filter_new_rows(qoq_all,     existing_periods)
        balance_new  = filter_new_rows(balance_all, existing_periods)
        cashflow_new = filter_new_rows(cashflow_all,existing_periods)

        # 股价按日期判断（月度，取已有最新日期之后的）
        price_new = None
        if price_all is not None and not price_all.empty and not is_new_file:
            existing_text = out.read_text(encoding="utf-8")
            existing_dates = set(re.findall(r'\d{4}-\d{2}-\d{2}', existing_text))
            price_new = price_all[~price_all["日期"].astype(str).isin(existing_dates)]
            if price_new.empty:
                price_new = None
        elif is_new_file:
            price_new = price_all

        # 判断是否有任何新数据
        has_new = any(
            df is not None and not df.empty
            for df in [profit_new, quality_new, qoq_new, balance_new, cashflow_new, price_new]
        )

        if not has_new and not is_new_file:
            print(f"  ✅ 无新数据，跳过")
            # 只更新行情快照（每次都刷新）
            if spot:
                text = out.read_text(encoding="utf-8")
                spot_md = "\n".join(f"- **{k}**：{v}" for k, v in spot.items())
                text = re.sub(
                    r'(## 当前行情快照\n\n).*?(\n\n##)',
                    rf'\g<1>{spot_md}\n\g<2>',
                    text, flags=re.DOTALL
                )
                out.write_text(text, encoding="utf-8")
                print(f"  ✅ 行情快照已刷新")
            continue

        if is_new_file:
            # 全新文件，直接生成
            md  = f"# {name}（{code}）完整财务研究数据\n\n"
            md += f"> 数据来源：东方财富 via akshare | 首次采集：{now}\n\n"
            if spot:
                md += "## 当前行情快照\n\n"
                md += "\n".join(f"- **{k}**：{v}" for k, v in spot.items()) + "\n\n"
            sections = [
                ("利润表（含同比增速）",        profit_all),
                ("盈利质量（毛利率/净利率/ROE/ROA）", quality_all),
                ("环比增速",                    qoq_all),
                ("资产负债表",                  balance_all),
                ("现金流量表",                  cashflow_all),
                ("月度股价走势（前复权）",       price_all),
                ("分红送配历史",                div_all),
            ]
            for title, df in sections:
                if df is not None and not df.empty:
                    md += f"## {title}\n\n{df_to_md(df)}\n\n"
            md += "---\n*以上数据仅供研究参考，不构成投资建议*\n"
            out.write_text(md, encoding="utf-8")
        else:
            # 增量更新：把新行插入各 section
            text = out.read_text(encoding="utf-8")
            # 更新行情快照
            if spot:
                spot_md = "\n".join(f"- **{k}**：{v}" for k, v in spot.items())
                text = re.sub(
                    r'(## 当前行情快照\n\n).*?(\n\n##)',
                    rf'\g<1>{spot_md}\n\g<2>',
                    text, flags=re.DOTALL
                )
            # 更新最后采集时间
            text = re.sub(
                r'最后更新：\d{4}-\d{2}-\d{2}',
                f'最后更新：{now}', text
            )
            if "最后更新" not in text:
                text = text.replace(
                    "首次采集：", f"最后更新：{now} | 首次采集："
                )
            pairs = [
                ("利润表（含同比增速）",             profit_new),
                ("盈利质量（毛利率/净利率/ROE/ROA）", quality_new),
                ("环比增速",                         qoq_new),
                ("资产负债表",                       balance_new),
                ("现金流量表",                       cashflow_new),
                ("月度股价走势（前复权）",            price_new),
            ]
            for title, df in pairs:
                text = update_section(text, title, df)
            out.write_text(text, encoding="utf-8")

        new_count = sum(
            len(df) for df in [profit_new, quality_new, qoq_new, balance_new, cashflow_new]
            if df is not None and not df.empty
        )
        print(f"  ✅ 已{'创建' if is_new_file else '增量更新'}，新增 {new_count} 条报告期数据")
        time.sleep(1.5)

    print("\n✅ 财务数据采集完成")

if __name__ == "__main__":
    run()
