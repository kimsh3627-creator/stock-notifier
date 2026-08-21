import json
import os
import requests
import yfinance as yf

# 환경변수에서 카카오 키/토큰 가져오기
KAKAO_REST_KEY = os.environ.get("KAKAO_REST_KEY")
KAKAO_REFRESH_TOKEN = os.environ.get("KAKAO_REFRESH_TOKEN")


def get_access_token():
    """Refresh Token을 이용해 새로운 Access Token을 발급받습니다."""
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_KEY,
        "refresh_token": KAKAO_REFRESH_TOKEN,
    }
    response = requests.post(url, data=data)
    result = response.json()
    return result.get("access_token")


def fetch_market_data(ticker_symbol):
    """지정한 티커의 [현재가, 1일전, 2일전, 1주일전, 1개월전] 종가를 가져옵니다."""
    ticker = yf.Ticker(ticker_symbol)
    # 최근 2개월치 일별 데이터 다운로드
    df = ticker.history(period="2mo")

    if len(df) == 0:
        return None

    # 거래일 기준 데이터 추출
    latest = df.iloc[-1]["Close"]
    day_1 = df.iloc[-2]["Close"] if len(df) >= 2 else None
    day_2 = df.iloc[-3]["Close"] if len(df) >= 3 else None
    week_1 = df.iloc[-6]["Close"] if len(df) >= 6 else None
    month_1 = df.iloc[-22]["Close"] if len(df) >= 22 else None

    return {
        "current": latest,
        "1d": day_1,
        "2d": day_2,
        "1w": week_1,
        "1m": month_1,
    }


def format_change(current, past):
    """과거 가격 대비 등락률을 계산하여 문자열로 반환합니다."""
    if past is None or past == 0:
        return "N/A"
    diff = current - past
    rate = (diff / past) * 100
    sign = "+" if diff > 0 else ""
    return f"{current:,.2f} ({sign}{rate:.2f}%)"


def build_message():
    """지수 및 환율 데이터를 취합하여 카카오톡 메시지 본문을 구성합니다."""
    targets = {
        "나스닥 (NASDAQ)": "^IXIC",
        "S&P 500": "^GSPC",
        "원/달러 환율": "KRW=X",
    }

    msg_lines = ["📊 [오늘의 증시 & 환율 리포트]\n"]

    for name, symbol in targets.items():
        data = fetch_market_data(symbol)
        if not data:
            msg_lines.append(f"• {name}: 데이터 조회 실패\n")
            continue

        curr = data["current"]
        msg_lines.append(f"[{name}]")
        msg_lines.append(f"• 현재가: {curr:,.2f}")
        msg_lines.append(f"• 1일전: {format_change(curr, data['1d'])}")
        msg_lines.append(f"• 2일전: {format_change(curr, data['2d'])}")
        msg_lines.append(f"• 1주일전: {format_change(curr, data['1w'])}")
        msg_lines.append(f"• 1개월전: {format_change(curr, data['1m'])}\n")

    return "\n".join(msg_lines)


def send_kakao_message(text):
    """카카오톡 나와의 채팅방으로 메시지를 전송합니다."""
    access_token = get_access_token()
    if not access_token:
        print("Access Token 발급 실패")
        return

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}

    # 카카오톡 텍스트 템플릿 규격
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
    
# 토큰 요청 post 직후 응답 내용을 출력하도록 수정
res = requests.post("https://kauth.kakao.com/oauth/token", data=payload)
print("카카오 토큰 응답 전문:", res.json())  # <-- 이 줄 추가

if "access_token" in res.json():
    return res.json()["access_token"]
else:
    print("Access Token 발급 실패")


    res = requests.post(url, headers=headers, data=payload)
    print("전송 결과:", res.json())
    

if __name__ == "__main__":
    message_content = build_message()
    send_kakao_message(message_content)