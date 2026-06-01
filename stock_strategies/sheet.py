import os
import json

import gspread
from google.oauth2.service_account import Credentials

def get_gsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_json = os.environ.get("GOOGLE_CREDS_JSON")

    if creds_json and creds_json != "test":
        creds_dict = json.loads(creds_json)
    else:
        with open(
            r"C:\Users\葉尾\Downloads\stockbot-498005-e6460537ecfe.json",
            "r",
            encoding="utf-8",
        ) as f:
            creds_dict = json.load(f)

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=scopes
    )

    gc = gspread.authorize(creds)

    return gc.open_by_key(
        os.environ["GOOGLE_SHEET_ID"]
    )

def read_watchlist() -> list[dict]:
    sh = get_gsheet()
    ws = sh.worksheet("Watchlist")
    rows = ws.get_all_records()
    enabled = [
        r for r in rows
        if str(r.get("enabled", "")).upper() in ("TRUE", "1", "YES")
    ]
    return enabled


def append_signals(signals: list[dict]):
    if not signals:
        return

    sh = get_gsheet()

    try:
        ws = sh.worksheet("Signals")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="Signals", rows=1000, cols=20)
        ws.append_row([
            "date", "stock_id", "name", "action", "signal_score",
            "entry_price", "stop_loss_price", "target_price",
            "rr_ratio", "position_pct", "winrate", "samples",
            "tech_signals", "risk_notes"
        ])

    rows = []

    for s in signals:
        c = s.get("components", {})
        rows.append([
            s.get("date", ""),
            s.get("stock_id", ""),
            s.get("name", ""),
            s.get("action", ""),
            s.get("signal_score", ""),
            s.get("entry_price", ""),
            s.get("stop_loss_price", ""),
            s.get("target_price", ""),
            s.get("risk_reward_ratio", ""),
            s.get("position_size_pct", ""),
            c.get("backtest_winrate", ""),
            c.get("backtest_samples", ""),
            ", ".join(c.get("tech_signals", [])),
            " / ".join(s.get("risk_notes", [])),
        ])

    ws.append_rows(rows)


PERFORMANCE_HEADERS = [
    "signal_date", "stock_id", "name", "entry_close", "entry_open",
    "t5_date", "t5_close", "t5_ret",
    "t10_date", "t10_close", "t10_ret",
    "t20_date", "t20_close", "t20_ret",
    "hit_target", "hit_stop", "status",
]


def read_performance() -> list[dict]:
    sh = get_gsheet()

    try:
        ws = sh.worksheet("Performance")
    except gspread.WorksheetNotFound:
        return []

    return ws.get_all_records()


def write_performance(records: list[dict]):
    sh = get_gsheet()

    try:
        ws = sh.worksheet("Performance")
        ws.clear()
    except gspread.WorksheetNotFound:
        rows_alloc = max(2000, len(records) + 100)
        ws = sh.add_worksheet(
            title="Performance",
            rows=rows_alloc,
            cols=len(PERFORMANCE_HEADERS)
        )

    ws.append_row(PERFORMANCE_HEADERS)

    if not records:
        return

    rows = [[r.get(h, "") for h in PERFORMANCE_HEADERS] for r in records]
    ws.append_rows(rows)

def replace_watchlist(stocks: list[dict]):
    """
    完全覆蓋 Watchlist
    """

    sh = get_gsheet()
    ws = sh.worksheet("Watchlist")

    ws.clear()

    ws.append_row([
        "stock_id",
        "name",
        "category",
        "enabled"
    ])

    rows = []

    for s in stocks:
        rows.append([
            s["stock_id"],
            s.get("name", ""),
            s.get("category", "AutoVolume"),
            "TRUE"
        ])

    if rows:
        ws.append_rows(rows)