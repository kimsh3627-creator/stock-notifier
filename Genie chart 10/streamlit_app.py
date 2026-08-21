import re
import io
import requests
import streamlit as st


def extract_video_id(url: str) -> str | None:
    if not url:
        return None
    patterns = [
        r"youtu\.be/([\w-]{11})",
        r"v=([\w-]{11})",
        r"/embed/([\w-]{11})",
        r"/v/([\w-]{11})",
        r"/shorts/([\w-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    tokens = re.findall(r"[\w-]{11}", url)
    return tokens[0] if tokens else None


def thumbnail_url(video_id: str, name: str) -> str:
    return f"https://img.youtube.com/vi/{video_id}/{name}.jpg"


@st.cache_data
def fetch_image_bytes(url: str) -> bytes | None:
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            return r.content
    except Exception:
        return None


def main():
    st.set_page_config(page_title="YouTube 썸네일 뷰어", layout="centered")
    st.title("YouTube 썸네일 보기")

    with st.form("video_form"):
        url = st.text_input("유튜브 URL을 입력하세요")
        submit = st.form_submit_button("썸네일 보기")

    if submit:
        vid = extract_video_id(url)
        if not vid:
            st.error("유효한 유튜브 URL에서 비디오 ID를 찾을 수 없습니다.")
            return

        res_choice = st.radio("해상도 선택", ["auto(최고 해상도 우선)", "maxresdefault", "hqdefault", "mqdefault", "sddefault"], index=0)

        sizes_to_try = []
        if res_choice == "auto(최고 해상도 우선)":
            sizes_to_try = ["maxresdefault", "hqdefault", "sddefault", "mqdefault"]
        else:
            sizes_to_try = [res_choice]

        found = None
        for s in sizes_to_try:
            url_img = thumbnail_url(vid, s)
            data = fetch_image_bytes(url_img)
            if data:
                found = (s, url_img, data)
                break

        if not found:
            st.error("썸네일을 불러오지 못했습니다.")
            return

        sname, thumb_url, img_bytes = found

        st.markdown(f"**비디오 ID:** {vid}  \n**선택 해상도:** {sname}")

        cols = st.columns([3, 1])
        with cols[0]:
            st.image(img_bytes, use_container_width=True)
        with cols[1]:
            st.write("원본 링크")
            st.text_input("썸네일 URL", value=thumb_url, key="thumb_link")
            st.download_button("썸네일 다운로드", data=io.BytesIO(img_bytes), file_name=f"{vid}_{sname}.jpg", mime="image/jpeg")
            st.write(f"이미지 크기: {len(img_bytes)} bytes")


if __name__ == "__main__":
    main()
