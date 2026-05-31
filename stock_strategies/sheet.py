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

def replace_watchlist(stocks: list[dict]):
    """
    完全覆蓋 Watchlist
    stocks:
    [
        {"stock_id":"2330","name":"台積電","category":"AI"},
        ...
    ]
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