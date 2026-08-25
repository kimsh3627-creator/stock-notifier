import json
import os
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


def get_market_summary():
    results = []

    # 1. 나스닥 및 S&P 500 (현재가 + 1년 최고가 대비 하락률)
    index_tickers = {"나스닥": "^IXIC", "S&P 500": "^GSPC"}
    for name, code in index_tickers.items():
        ticker = yf.Ticker(code)
        df = ticker.history(period="1y", interval="1d")

        if not df.empty:
            current_price = df["Close"].iloc[-1]
            max_price_1y = df["High"].max()
            drop_pct = ((current_price - max_price_1y) / max_price_1y) * 100

            text = f"📌 [{name}]\n"
            text += f"• 현재가: {current_price:,.2f}\n"
            text += f"• 1년 최고가 대비: {drop_pct:+.2f}% (최고가 {max_price_1y:,.2f})"
            results.append(text)

    # 2. 원/달러 환율 (현재가만)
    fx_ticker = yf.Ticker("KRW=X")
    fx_df = fx_ticker.history(period="5d", interval="1d")
    if not fx_df.empty:
        fx_current = fx_df["Close"].iloc[-1]
        results.append(f"📌 [원/달러 환율]\n• 현재가: {fx_current:,.2f}원")

    return "\n\n".join(results)


def get_sp500_filtered_stocks():
    """S&P 500 종목 중 PER 20 이하 & 1년 최고가 대비 30% 이상 하락한 전체 종목 추출"""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        sp500_df = tables[0]
        tickers = sp500_df["Symbol"].tolist()
    except Exception as e:
        print("S&P 500 티커 수집 실패:", e)
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

                # PER <= 20 이고 고점 대비 -30% 이하
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
        return "🔍 [S&P 500 가치주 (PER ≤ 20 & -30% 이상 하락)]\n• 조건에 해당하는 종목이 없습니다."

    # 하락률순 정렬
    filtered.sort(key=lambda x: x["drop_pct"])

    lines = [
        f"🔍 [S&P 500 가치주 (PER ≤ 20 & -30% 이상 하락)] (총 {len(filtered)}개)"
    ]
    # 요청대로 개수 제한 없이 전체 리스트 출력
    for item in filtered:
        lines.append(
            f"• {item['symbol']} (PER {item['pe']:.1f}): 현재가 ${item['current']:,.2f} / 최고가 ${item['high']:,.2f} 대비 {item['drop_pct']:.2f}%"
        )

    return "\n".join(lines)


def send_kakao_message(text, access_token):
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}

    print(f"발송 메시지 전체 길이: {len(text)}자")

    payload = {
        "template_object": json.dumps(
            {
                "object_type": "text",
                "text": text,
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

        full_message = f"📊 증시·환율 리포트\n\n{market_summary}\n\n{sp500_summary}"

        # 혹시 전체 글자가 카카오톡 1000자 한계를 넘는 경우 대비 예방 조치
        if len(full_message) > 990:
            full_message = full_message[:980] + "\n...(이하 생략)"

        send_kakao_message(full_message, token)