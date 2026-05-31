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