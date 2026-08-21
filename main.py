import json
import os
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

    print("카카오 토큰 응답 전문:", result)

    if "access_token" in result:
        return result["access_token"]
    else:
        print("Access Token 발급 실패")
        return None


def get_stock_data():
    tickers = {"나스닥": "^IXIC", "S&P 500": "^GSPC", "원/달러 환율": "KRW=X"}
    lines = []

    for name, code in tickers.items():
        ticker = yf.Ticker(code)
        df = ticker.history(period="2mo")
        if not df.empty and len(df) >= 2:
            close_today = df["Close"].iloc[-1]
            close_prev = df["Close"].iloc[-2]
            diff = close_today - close_prev
            pct = (diff / close_prev) * 100

            sign = "▲" if diff > 0 else ("▼" if diff < 0 else "-")
            lines.append(
                f"{name}: {close_today:,.2f} ({sign} {abs(diff):,.2f}, {pct:+.2f}%)"
            )

    return "\n".join(lines)


def send_kakao_message(text, access_token):
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "template_object": json.dumps(
            {
                "object_type": "text",
                "text": f"📊 오늘 증시 리포트\n\n{text}",
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