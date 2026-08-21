import json
import os
from datetime import datetime, timedelta
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


def get_stock_data():
    tickers = {"나스닥": "^IXIC", "S&P 500": "^GSPC", "원/달러 환율": "KRW=X"}
    results = []

    for name, code in tickers.items():
        ticker = yf.Ticker(code)
        # 1년 내 최고가 계산을 위해 period를 "1y"로 지정
        df = ticker.history(period="1y", interval="1d")

        if df.empty:
            continue

        now_dt = df.index[-1]
        current_price = df["Close"].iloc[-1]

        # 1년 내 최고가 및 최고가 대비 하락률 계산
        max_price_1y = df["High"].max()
        drop_from_high_pct = ((current_price - max_price_1y) / max_price_1y) * 100

        # 과거 비교 시점 (일 단위)
        t_1d = now_dt - timedelta(days=1)
        t_2d = now_dt - timedelta(days=2)
        t_1w = now_dt - timedelta(weeks=1)
        t_1m = now_dt - timedelta(days=30)

        p_1d = get_closest_price(df, t_1d)
        p_2d = get_closest_price(df, t_2d)
        p_1w = get_closest_price(df, t_1w)
        p_1m = get_closest_price(df, t_1m)

        text = f"📌 [{name}]\n"
        text += f"• 현재가: {current_price:,.2f}\n"
        text += f"• 1년 최고가 대비: {drop_from_high_pct:+.2f}% (최고가 {max_price_1y:,.2f})\n"
        text += f"• 1일 전: {format_value_and_change(current_price, p_1d)}\n"
        text += f"• 2일 전: {format_value_and_change(current_price, p_2d)}\n"
        text += f"• 1주일 전: {format_value_and_change(current_price, p_1w)}\n"
        text += f"• 1개월 전: {format_value_and_change(current_price, p_1m)}"

        results.append(text)

    return "\n\n".join(results)


def send_kakao_message(text, access_token):
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "template_object": json.dumps(
            {
                "object_type": "text",
                "text": f"📊 증시 및 환율 시점별 리포트\n\n{text}",
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
        msg = get_stock_data()
        send_kakao_message(msg, token)