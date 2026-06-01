"""量價型態偵測 (V3.1 量價字典)"""

import pandas as pd


def detect_patterns(df: pd.DataFrame, idx: int = -1) -> dict:
    """
    偵測 5 種量能型態
    回傳: {"patterns": [...], "bonus": int, "details": {...}}
    """
    if len(df) < 21:
        return {"patterns": [], "bonus": 0, "details": {}}

    if idx < 0:
        idx = len(df) + idx

    patterns = []
    bonus = 0
    details = {}

    vol = df["volume"]
    close = df["close"]
    open_ = df["open"] if "open" in df.columns else close
    high = df["high"]

    vol_today = float(vol.iloc[idx])
    vol_yesterday = float(vol.iloc[idx - 1])

    # 倍量柱：今日量 ≥ 昨日 2x
    if vol_yesterday > 0 and vol_today >= 2 * vol_yesterday:
        patterns.append("倍量柱")
        bonus += 10
        details["倍量柱"] = f"今日量為昨日 {vol_today/vol_yesterday:.1f}x"

    # 梯量柱：連續 3 日量能遞增 + 價格上漲
    if idx >= 2:
        v3 = float(vol.iloc[idx])
        v2 = float(vol.iloc[idx - 1])
        v1 = float(vol.iloc[idx - 2])
        if v3 > v2 > v1 and close.iloc[idx] > close.iloc[idx - 2]:
            patterns.append("梯量柱")
            bonus += 8
            details["梯量柱"] = "連續 3 日量能遞增，價格同步上攻"

    # 縮量柱：連續 3 日量能遞減 + 價格回調（洗盤）
    if idx >= 2:
        v3 = float(vol.iloc[idx])
        v2 = float(vol.iloc[idx - 1])
        v1 = float(vol.iloc[idx - 2])
        if v3 < v2 < v1 and close.iloc[idx] < close.iloc[idx - 2]:
            patterns.append("縮量柱")
            bonus += 5
            details["縮量柱"] = "連續 3 日量能遞減，回調但賣壓輕"

    # 低量柱：今日量 < 60% 20 日均量
    vol_20ma = float(vol.iloc[max(0, idx - 20):idx].mean())
    if vol_20ma > 0 and vol_today < 0.6 * vol_20ma:
        patterns.append("低量柱")
        bonus += 8
        details["低量柱"] = f"今日量僅 20 日均量 {vol_today/vol_20ma*100:.0f}%，拋壓耗盡"

    # 平量柱：連續 3 日量能高度一致（變化率 < 15%）— 多空平衡，蓄力中
    if idx >= 2:
        v3 = float(vol.iloc[idx])
        v2 = float(vol.iloc[idx - 1])
        v1 = float(vol.iloc[idx - 2])
        if v1 > 0 and v2 > 0 and v3 > 0:
            rng_max = max(v1, v2, v3)
            rng_min = min(v1, v2, v3)
            if (rng_max - rng_min) / rng_max < 0.15:
                patterns.append("平量柱")
                # 中性訊號 — 不加不扣分
                details["平量柱"] = (
                    f"連續 3 日量能 {int(v1)}/{int(v2)}/{int(v3)} 高度一致，多空平衡蓄力中"
                )

    # 創高放量：收盤突破近 60 日高點，且量大於 20 日均量 1.5 倍
    if idx >= 60:
        high_60 = float(high.iloc[idx - 60:idx].max())
        if vol_20ma > 0 and close.iloc[idx] > high_60 and vol_today >= 1.5 * vol_20ma:
            patterns.append("創高放量")
            bonus += 20
            details["創高放量"] = f"收盤突破60日高點，量為20日均量 {vol_today/vol_20ma:.1f}x"

    # 動能轉強：5 日漲幅 > 8%，且量大於 20 日均量 1.2 倍
    if idx >= 5:
        close_5d_ago = float(close.iloc[idx - 5])
        if close_5d_ago > 0:
            chg_5d = close.iloc[idx] / close_5d_ago - 1
            if vol_20ma > 0 and chg_5d > 0.08 and vol_today >= 1.2 * vol_20ma:
                patterns.append("動能轉強")
                bonus += 15
                details["動能轉強"] = f"5日漲幅 {chg_5d*100:.1f}%，量為20日均量 {vol_today/vol_20ma:.1f}x"

    # 強勢回檔：距60日高點回檔5%~15%，可能是主升段洗盤
    if idx >= 60:
        high_60 = float(high.iloc[idx - 60:idx].max())
        if high_60 > 0:
            pullback = (high_60 - float(close.iloc[idx])) / high_60
            if 0.05 <= pullback <= 0.15:
                patterns.append("強勢回檔")
                bonus += 15
                details["強勢回檔"] = f"距60日高點回檔 {pullback*100:.1f}%"

    # 放量滯漲：放量但 K 線差（收黑 / 長上影 / 漲幅微弱）
    vol_5ma = float(vol.iloc[max(0, idx - 5):idx].mean())
    if vol_5ma > 0 and vol_today >= 1.5 * vol_5ma:
        c = float(close.iloc[idx])
        o = float(open_.iloc[idx]) if "open" in df.columns else c
        h = float(high.iloc[idx])
        prev_c = float(close.iloc[idx - 1])
        body = abs(c - o)
        upper_shadow = h - max(c, o)
        chg = (c - prev_c) / prev_c if prev_c > 0 else 0

        is_red = c < o
        has_long_upper = body > 0 and upper_shadow > body * 2
        tiny_gain = 0 < chg < 0.01

        if is_red or has_long_upper or tiny_gain:
            patterns.append("放量滯漲")
            bonus -= 20
            details["放量滯漲"] = f"量放大 {vol_today/vol_5ma:.1f}x 但 K 線收黑或留上影"

    return {"patterns": patterns, "bonus": bonus, "details": details}


def verdict(patterns: list[str]) -> str:
    """根據偵測到的量能型態給出結論"""
    if "放量滯漲" in patterns:
        return "⚠️ 高檔爆量疑似出貨，持有者應考慮砍半鎖利"
    if "強勢回檔" in patterns:
        return "🟡 主升段回檔5~15%，若量能未退可觀察第二波"
    if "創高放量" in patterns:
        return "🚀 創高放量，短線動能明顯轉強"
    if "動能轉強" in patterns:
        return "🔥 近5日價量同步轉強，留意短線續攻"
    if "倍量柱" in patterns and "梯量柱" in patterns:
        return "🟢 A軌動能突破成立，主力積極進場"
    if "倍量柱" in patterns:
        return "🟢 今日出現倍量攻勢，關注後續跟進"
    if "梯量柱" in patterns:
        return "📈 量能階梯推升，走勢健康"
    if "低量柱" in patterns and "縮量柱" in patterns:
        return "🟡 底部極限縮量 + 洗盤完成，逢訊號可伏擊"
    if "低量柱" in patterns:
        return "🟡 底部極限縮量，拋壓耗盡，等待訊號"
    if "平量柱" in patterns:
        return "⚖️ 多空平衡蓄力中，等下一根倍量或破線"
    if "縮量柱" in patterns:
        return "🟡 量縮洗盤，主力未退場"
    return "量能平淡，無特殊訊號"
