from dotenv import load_dotenv
load_dotenv()

import re
import requests
import pandas as pd

from stock_strategies.sheet import replace_watchlist
from stock_strategies.data import get_price_history


TWSE_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TPEX_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"


def to_number(x):
    if x is None:
        return 0.0
    s = str(x).replace(",", "").replace("--", "").strip()
    if s == "":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def fetch_json(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_twse():
    data = fetch_json(TWSE_URL)
    rows = []

    for r in data:
        sid = str(r.get("Code", "")).strip()
        name = str(r.get("Name", "")).strip()

        if not re.match(r"^\d{4}$", sid):
            continue

        turnover = to_number(
            r.get("TradeValue")
            or r.get("TradingValue")
            or r.get("成交金額")
        )

        if turnover <= 0:
            continue

        rows.append({
            "stock_id": sid,
            "name": name,
            "category": "上市成交額前100",
            "turnover": turnover,
        })

    return rows


def fetch_tpex():
    data = fetch_json(TPEX_URL)
    rows = []

    for r in data:
        sid = str(
            r.get("SecuritiesCompanyCode")
            or r.get("Code")
            or r.get("代號")
            or ""
        ).strip()

        name = str(
            r.get("CompanyName")
            or r.get("Name")
            or r.get("名稱")
            or ""
        ).strip()

        if not re.match(r"^\d{4}$", sid):
            continue

        turnover = to_number(
            r.get("TransactionAmount")
            or r.get("TradeValue")
            or r.get("成交金額")
        )

        if turnover <= 0:
            continue

        rows.append({
            "stock_id": sid,
            "name": name,
            "category": "上櫃成交額前100",
            "turnover": turnover,
        })

    return rows


def pass_ma20_and_not_overheated(stock_id):
    try:
        px = get_price_history(stock_id, years=1)
    except TypeError:
        px = get_price_history(stock_id, 1)
    except Exception as e:
        print(f"略過 {stock_id}: 抓歷史價格失敗 {e}")
        return False

    if px is None or len(px) < 21:
        return False

    px = px.sort_values("date").copy()
    px["close"] = pd.to_numeric(px["close"], errors="coerce")
    px["ma20"] = px["close"].rolling(20).mean()

    last = px.iloc[-1]
    prev20 = px.iloc[-21]

    if pd.isna(last["ma20"]) or pd.isna(last["close"]) or pd.isna(prev20["close"]):
        return False

    above_ma20 = last["close"] > last["ma20"]
    chg20 = last["close"] / prev20["close"] - 1

    return above_ma20 and chg20 <= 0.30


def build_watchlist():
    print("抓上市成交額資料...")
    twse = fetch_twse()

    print("抓上櫃成交額資料...")
    try:
        tpex = fetch_tpex()
    except Exception as e:
        print(f"上櫃資料抓取失敗，先只用上市資料：{e}")
        tpex = []

    all_rows = twse + tpex

    if not all_rows:
        raise RuntimeError("沒有抓到任何成交額資料")

    top100 = sorted(
        all_rows,
        key=lambda x: x["turnover"],
        reverse=True
    )[:100]

    print(f"成交額前100已取得，開始過濾 MA20 與 20日漲幅...")

    result = []

    for i, s in enumerate(top100, 1):
        sid = s["stock_id"]
        name = s["name"]
        print(f"[{i}/100] 檢查 {sid} {name}")

        if pass_ma20_and_not_overheated(sid):
            result.append({
                "stock_id": sid,
                "name": name,
                "category": s["category"],
            })

    print(f"過濾後剩下 {len(result)} 檔")
    return result


if __name__ == "__main__":
    stocks = build_watchlist()
    replace_watchlist(stocks)
    print("Watchlist 已更新完成")