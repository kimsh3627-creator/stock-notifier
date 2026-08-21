import requests

REST_API_KEY = "91d96cd7e112cd05f0e13dfa04c47974"
AUTHORIZATION_CODE = "PaFZLoUWjtYI9l2SrvZPp3KaxUNfUJNRaAraCeU-D30UdyAWd0t-qwAAAAQKDSAbAAABoCTd-Bl-jFVpBnvzXw"

url = "https://kauth.kakao.com/oauth/token"
data = {
    "grant_type": "authorization_code",
    "client_id": REST_API_KEY,
    "redirect_uri": "https://localhost:3000",
    "code": AUTHORIZATION_CODE,
}

response = requests.post(url, data=data)
result = response.json()

print("카카오 응답 전문:", result)
print("----------------------------------------")
print("Refresh Token:", result.get("refresh_token"))
print("----------------------------------------")