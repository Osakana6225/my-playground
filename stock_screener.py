"""
日本株スクリーニングBot
"""
import os
"""
日本株スクリーニングBot - Gemini AI評価 + Discord通知
条件: ゴールデンクロス・RSI回復・出来高急増・25日線上抜け のうち2つ以上でヒット
ヒット銘柄をGemini AIが総合評価してDiscordに通知
"""

import yfinance as yf
import pandas as pd
import requests
import time
import os
from datetime import datetime

# ============================================================
# 設定
# ============================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "YOUR_DISCORD_WEBHOOK_URL")

# ============================================================
# 東証銘柄リスト
# ============================================================
def get_tse_tickers():
    return [
        "7203.T",  # トヨタ
        "6758.T",  # ソニー
        "9984.T",  # ソフトバンクG
        "8306.T",  # 三菱UFJ
        "6861.T",  # キーエンス
        "9432.T",  # NTT
        "4063.T",  # 信越化学
        "8316.T",  # 三井住友FG
        "6367.T",  # ダイキン
        "7741.T",  # HOYA
        "4519.T",  # 中外製薬
        "6098.T",  # リクルート
        "9433.T",  # KDDI
        "8035.T",  # 東京エレクトロン
        "7267.T",  # ホンダ
        "4502.T",  # 武田薬品
        "6501.T",  # 日立
        "6702.T",  # 富士通
        "7751.T",  # キヤノン
        "9022.T",  # JR東海
        "6594.T",  # 日本電産（ニデック）
        "4661.T",  # オリエンタルランド
        "9983.T",  # ファーストリテイリング
        "8411.T",  # みずほFG
        "7974.T",  # 任天堂
        "4543.T",  # テルモ
        "6954.T",  # ファナック
        "4901.T",  # 富士フイルム
        "8801.T",  # 三井不動産
        "9020.T",  # JR東日本
    ]

# ============================================================
# テクニカル指標
# ============================================================
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def check_signals(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
        if df is None or len(df) < 80:
            return None
        close = df["Close"].squeeze()
        volume = df["Volume"].squeeze()
        ma25 = close.rolling(25).mean()
        ma75 = close.rolling(75).mean()
        rsi = calculate_rsi(close)
        signals = []
        signal_details = []
        if (ma25.iloc[-2] <= ma75.iloc[-2]) and (ma25.iloc[-1] > ma75.iloc[-1]):
            signals.append("ゴールデンクロス")
            signal_details.append(f"25日線({ma25.iloc[-1]:.0f}) が75日線({ma75.iloc[-1]:.0f})を上抜け")
        if rsi.iloc[-2] <= 40 and rsi.iloc[-1] > rsi.iloc[-2]:
            signals.append("RSI回復")
            signal_details.append(f"RSI: {rsi.iloc[-2]:.1f} → {rsi.iloc[-1]:.1f}（売られすぎから回復）")
        avg_vol = volume.iloc[-6:-1].mean()
        if volume.iloc[-1] > avg_vol * 1.5:
            ratio = volume.iloc[-1] / avg_vol
            signals.append("出来高急増")
            signal_details.append(f"出来高: 5日平均の{ratio:.1f}倍")
        if (close.iloc[-2] < ma25.iloc[-2]) and (close.iloc[-1] > ma25.iloc[-1]):
            signals.append("25日線上抜け")
            signal_details.append(f"株価({close.iloc[-1]:.0f}) が25日線({ma25.iloc[-1]:.0f})を上抜け")
        if len(signals) >= 2:
            price_change_1d = ((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]) * 100
            price_change_1m = ((close.iloc[-1] - close.iloc[-22]) / close.iloc[-22]) * 100
            return {
                "ticker": ticker,
                "price": float(close.iloc[-1]),
                "price_change_1d": float(price_change_1d),
                "price_change_1m": float(price_change_1m),
                "rsi": float(rsi.iloc[-1]),
                "ma25": float(ma25.iloc[-1]),
                "ma75": float(ma75.iloc[-1]),
                "signals": signals,
                "details": signal_details,
                "signal_count": len(signals),
            }
        return None
    except Exception as e:
        print(f"  エラー ({ticker}): {e}")
        return None

# ============================================================
# Gemini AI評価
# ============================================================
def evaluate_with_gemini(stocks):
    if not stocks:
        return {}
    stocks_info = ""
    for s in stocks:
        ticker_short = s["ticker"].replace(".T", "")
        stocks_info += f"""
銘柄コード: {ticker_short}
株価: {s['price']:,.0f}円（前日比: {s['price_change_1d']:+.1f}%、1ヶ月比: {s['price_change_1m']:+.1f}%）
RSI: {s['rsi']:.1f}
25日移動平均: {s['ma25']:,.0f}円
75日移動平均: {s['ma75']:,.0f}円
シグナル: {', '.join(s['signals'])}
"""
    prompt = f"""
あなたは日本株のテクニカル分析の専門家です。
以下の銘柄はスクリーニング条件（ゴールデンクロス、RSI回復、出来高急増、25日線上抜け）に複数ヒットした銘柄です。

{stocks_info}

各銘柄について以下の形式で簡潔に評価してください（各銘柄3行以内）：
- 星評価：★1〜5（5が最も注目度高い）
- 一言コメント：テクニカル面から見た特徴と注意点

最後に全体のまとめを1〜2文で書いてください。
※ あくまでテクニカル分析に基づく参考情報であり、投資判断は自己責任でお願いします。
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.3}
    }
    try:
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"Gemini APIエラー: {e}")
        return "（AI評価の取得に失敗しました）"

# ============================================================
# Discord通知
# ============================================================
def send_discord(content):
    chunks = [content[i:i+1900] for i in range(0, len(content), 1900)]
    for chunk in chunks:
        payload = {"content": chunk}
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code not in (200, 204):
            print(f"Discord送信エラー: {resp.status_code}")
        time.sleep(0.5)

# ============================================================
# メイン処理
# ============================================================
def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"=== 日本株スクリーニング開始 {today} ===")
    tickers = get_tse_tickers()
    hit_stocks = []
    for i, ticker in enumerate(tickers):
        print(f"チェック中... {ticker} ({i+1}/{len(tickers)})")
        result = check_signals(ticker)
        if result:
            hit_stocks.append(result)
            print(f"  ✅ ヒット！ シグナル: {', '.join(result['signals'])}")
        time.sleep(0.5)
    print(f"対象: {len(tickers)}銘柄 / ヒット: {len(hit_stocks)}銘柄")
    hit_stocks.sort(key=lambda x: x["signal_count"], reverse=True)
    if not hit_stocks:
        send_discord(f"📊 **日本株スクリーニング結果 {today}**\n該当銘柄はありませんでした。")
        return
    msg = f"📊 **日本株スクリーニング結果 {today}**\n{len(hit_stocks)}銘柄がシグナルに該当しました\n" + "━" * 30 + "\n"
    for s in hit_stocks:
        ticker_short = s["ticker"].replace(".T", "")
        msg += f"\n🔔 **{ticker_short}**（{s['signal_count']}シグナル）\n"
        msg += f"株価: {s['price']:,.0f}円（前日比 {s['price_change_1d']:+.1f}%）\n"
        for sig, detail in zip(s["signals"], s["details"]):
            msg += f"  ✅ {sig}: {detail}\n"
    send_discord(msg)
    print("Gemini AIで評価中...")
    ai_comment = evaluate_with_gemini(hit_stocks)
    ai_msg = "\n🤖 **Gemini AI 総合評価**\n" + "━" * 30 + "\n" + ai_comment + "\n\n⚠️ *投資判断は自己責任でお願いします*"
    send_discord(ai_msg)
    print("Discord通知完了！")

if __name__ == "__main__":
    main()print("test")
