import json
import os
from datetime import datetime, timedelta
import pandas as pd
import requests
import yfinance as yf

REST_KEY = os.getenv("KAKAO_REST_KEY")
REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN")


def get_access_token():
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": REST_KEY,
        "refresh_token": REFRESH_TOKEN,
    }
    response = requests.post(url, data=data)
    result = response.json()

    if "access_token" in result:
        return result["access_token"]
    else:
        print("Access Token 발급 실패:", result)
        return None


def get_closest_price(df, target_dt):
    """주어진 시간(target_dt) 이전의 가장 가까운 종가 수치를 가져옵니다."""
    filtered = df[df.index <= target_dt]
    if not filtered.empty:
        return filtered["Close"].iloc[-1]
    return df["Close"].iloc[0]


def format_value_and_change(current, past):
    if past is None or past == 0:
        return "-"
    diff = current - past
    sign = "▲" if diff > 0 else ("▼" if diff < 0 else "-")
    return f"{past:,.2f} ({sign} {abs(diff):,.2f})"


def get_market_summary():
    tickers = {"나스닥": "^IXIC", "S&P 500": "^GSPC", "원/달러 환율": "KRW=X"}
    results = []

    for name, code in tickers.items():
        ticker = yf.Ticker(code)
        df = ticker.history(period="1y", interval="1d")

        if df.empty:
            continue

        now_dt = df.index[-1]
        current_price = df["Close"].iloc[-1]

        max_price_1y = df["High"].max()
        drop_from_high_pct = ((current_price - max_price_1y) / max_price_1y) * 100

        t_1d = now_dt - timedelta(days=1)
        t_1w = now_dt - timedelta(weeks=1)
        t_1m = now_dt - timedelta(days=30)

        p_1d = get_closest_price(df, t_1d)
        p_1w = get_closest_price(df, t_1w)
        p_1m = get_closest_price(df, t_1m)

        text = f"📌 [{name}]\n"
        text += f"• 현재가: {current_price:,.2f}\n"
        text += f"• 1년 최고가 대비: {drop_from_high_pct:+.2f}% (최고가 {max_price_1y:,.2f})\n"
        text += f"• 1일 전: {format_value_and_change(current_price, p_1d)}\n"
        text += f"• 1주일 전: {format_value_and_change(current_price, p_1w)}\n"
        text += f"• 1개월 전: {format_value_and_change(current_price, p_1m)}"

        results.append(text)

    return "\n\n".join(results)


def get_sp500_filtered_stocks():
    """S&P 500 종목 중 PER 20 이하 & 1년 최고가 대비 30% 이상 하락한 종목 추출"""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        sp500_df = tables[0]
        tickers = sp500_df["Symbol"].tolist()
    except Exception as e:
        print("S&P 500 리스트 가져오기 실패:", e)
        return ""

    filtered = []

    for ticker in tickers:
        symbol = ticker.replace(".", "-")
        try:
            t = yf.Ticker(symbol)
            info = t.info

            pe = info.get("trailingPE")
            high_52w = info.get("fiftyTwoWeekHigh")
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")

            if pe and high_52w and current_price:
                drop_pct = ((current_price - high_52w) / high_52w) * 100

                # 조건: PER <= 20 이고 1년 최고가 대비 -30% 이하
                if 0 < pe <= 20 and drop_pct <= -30:
                    filtered.append(
                        {
                            "symbol": symbol,
                            "pe": pe,
                            "current": current_price,
                            "high": high_52w,
                            "drop_pct": drop_pct,
                        }
                    )
        except Exception:
            continue

    if not filtered:
        return "🔍 [S&P 500 특이 종목 (PER ≤ 20 & -30% 이상 하락)]\n• 조건에 해당하는 종목이 없습니다."

    # 하락률이 높은 순으로 정렬
    filtered.sort(key=lambda x: x["drop_pct"])

    lines = [
        f"🔍 [S&P 500 특이 종목 (PER ≤ 20 & -30% 이상 하락)] (총 {len(filtered)}개)"
    ]
    # 카카오톡 글자 수 제한을 고려해 하락률 상위 최대 10개 표시
    for item in filtered[:10]:
        lines.append(
            f"• {item['symbol']} (PER {item['pe']:.1f}): 현재가 ${item['current']:,.2f} / 최고가 ${item['high']:,.2f} 대비 {item['drop_pct']:.2f}%"
        )

    return "\n".join(lines)


def send_kakao_message(text, access_token):
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "template_object": json.dumps(
            {
                "object_type": "text",
                "text": f"📊 증시·환율 리포트 & S&P500 가치주 탐색\n\n{text}",
                "link": {
                    "web_url": "https://finance.yahoo.com",
                    "mobile_web_url": "https://finance.yahoo.com",
                },
            }
        )
    }

    res = requests.post(url, headers=headers, data=payload)
    print("전송 결과:", res.json())


if __name__ == "__main__":
    token = get_access_token()
    if token:
        market_summary = get_market_summary()
        sp500_summary = get_sp500_filtered_stocks()

        full_message = f"{market_summary}\n\n{sp500_summary}"
        send_kakao_message(full_message, token)