STOCKS = [
    {"code": "600536", "name": "中国软件",  "market": "sh"},
    {"code": "300308", "name": "中际旭创",  "market": "sz"},
    {"code": "600183", "name": "生益科技",  "market": "sh"},
    {"code": "002938", "name": "鹏鼎控股",  "market": "sz"},
    {"code": "300757", "name": "罗博特科",  "market": "sz"},
    {"code": "002384", "name": "东山精密",  "market": "sz"},
    {"code": "002281", "name": "光迅科技",  "market": "sz"},
    {"code": "688808", "name": "联讯仪器",  "market": "sh"},
    {"code": "301191", "name": "菱科思",    "market": "sz"},
    {"code": "688048", "name": "长光华芯",  "market": "sh"},
    {"code": "002428", "name": "云南锗业",  "market": "sz"},
]

# 采集设置
DATE_START = "2022-01-01"
DATE_END   = "2026-05-09"

# 公告类别（巨潮）
ANN_CATEGORIES = {
    "年度报告":   "category_ndbg_szsh",
    "半年度报告": "category_bndbg_szsh",
    "季度报告":   "category_jdbg_szsh",
    "临时公告":   "",          # 空 = 全部，下面按关键词过滤
}

# 临时公告关键词过滤（标题包含其一则下载）
IMPORTANT_KEYWORDS = [
    "重大合同", "收购", "并购", "战略", "定增", "募资",
    "处罚", "立案", "诉讼", "仲裁",
    "业绩预告", "业绩快报", "盈利预警",
    "股权激励", "回购", "分红",
    "重大资产", "关联交易",
]

# 每类公告最多下载数量
MAX_ANN_PER_CATEGORY = 20
MAX_TEMP_ANN = 30
MAX_NEWS = 50

OUTPUT_DIR = "./output"
