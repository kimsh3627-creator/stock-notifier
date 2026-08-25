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

    # 1. 나스닥 및 S&P 500 (현재가 + 1년 최고가 대비)
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
    """
    S&P 500 상위 300개 종목 필터링:
    - 5 <= PER <= 15
    - 0 <= PBR <= 10
    - 1년 최고가 대비 -30% 이상 하락
    """
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        sp500_df = tables[0]
        # 상위 300개 종목 추출
        raw_tickers = sp500_df["Symbol"].head(300).tolist()
    except Exception as e:
        print("S&P 500 티커 수집 실패:", e)
        return "🔍 [S&P 500 특이 종목]\n• 데이터 수집 중 오류 발생"

    filtered = []

    # 50개씩 분할 처리하여 API 차단 방지 및 속도 최적화
    chunk_size = 50
    for i in range(0, len(raw_tickers), chunk_size):
        chunk = raw_tickers[i : i + chunk_size]
        chunk_symbols = [t.replace(".", "-") for t in chunk]

        ticker_objects = yf.Tickers(" ".join(chunk_symbols))

        for symbol in chunk_symbols:
            try:
                t = ticker_objects.tickers[symbol]
                info = t.info

                pe = info.get("trailingPE")
                pbr = info.get("priceToBook")
                high_52w = info.get("fiftyTwoWeekHigh")
                current_price = info.get("currentPrice") or info.get(
                    "regularMarketPrice"
                )

                if pe and pbr and high_52w and current_price:
                    drop_pct = ((current_price - high_52w) / high_52w) * 100

                    # 조건: 5 <= PER <= 15, 0 <= PBR <= 10, drop_pct <= -30
                    if 5 <= pe <= 15 and 0 <= pbr <= 10 and drop_pct <= -30:
                        filtered.append(
                            {
                                "symbol": symbol,
                                "pe": pe,
                                "pbr": pbr,
                                "current": current_price,
                                "high": high_52w,
                                "drop_pct": drop_pct,
                            }
                        )
            except Exception:
                continue

    if not filtered:
        return "🔍 [S&P 500 특이 종목 (5≤PER≤15, 0≤PBR≤10, -30%↓)]\n• 조건에 해당하는 종목이 없습니다."

    # 하락률이 높은 순서로 정렬
    filtered.sort(key=lambda x: x["drop_pct"])

    lines = [
        f"🔍 [S&P 500 특이 종목 (5≤PER≤15, 0≤PBR≤10, -30%↓)] (상위 300개 중 {len(filtered)}개)"
    ]

    # 카카오톡 글자 수 초과 방지: 최대 10개까지만 메시지에 포함
    display_limit = 10
    for item in filtered[:display_limit]:
        lines.append(
            f"• {item['symbol']} (PER{item['pe']:.1f}/PBR{item['pbr']:.1f}): ${item['current']:,.1f} / 고점 ${item['high']:,.1f} ({item['drop_pct']:.1f}%)"
        )

    if len(filtered) > display_limit:
        lines.append(f"• 외 {len(filtered) - display_limit}개 종목 생략")

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

        # 카카오톡 텍스트 글자 수 제한(1,000자) 안전 장치
        if len(full_message) > 980:
            full_message = full_message[:970] + "\n...(길이 제한으로 생략)"

        send_kakao_message(full_message, token)