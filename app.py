import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import urllib.request
import os
from excel_export import create_excel, measurement_date_label, measurement_title
from image_export import create_image
from worker_filter import select_high_pressure_workers

# --- 1. 기본 설정 및 함수 ---
st.set_page_config(page_title="근로자 혈압측정 명단", layout="wide")

@st.cache_resource
def set_korean_font():
    font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    font_path = "NanumGothic.ttf"
    
    if not os.path.exists(font_path):
        urllib.request.urlretrieve(font_url, font_path)
        
    return font_path

def calculate_age(ssn_str):
    try:
        s = str(ssn_str).replace("-", "").strip()
        if len(s) < 6: return -1
        yy, mm, dd = int(s[:2]), int(s[2:4]), int(s[4:6])
        year = 2000 + yy if yy <= 26 else 1900 + yy
        birth_date = datetime(year, mm, dd)
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except:
        return -1 

font_path = set_korean_font()


def show_report(roster, title, excel, png, key):
    tab1, tab2 = st.tabs(["엑셀 명단", "이미지 명단"])
    with tab1:
        st.subheader(title)
        st.dataframe(roster, width='stretch', hide_index=True)
        st.download_button(
            label="엑셀 다운로드", data=excel, file_name=f"{title}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary", key=f"{key}_excel",
        )
    with tab2:
        st.subheader("인쇄용 이미지")
        st.caption("이미지에는 협력회사, 이름, 공종이 표시됩니다. 혈압 기록용 서식은 엑셀로 내려받으세요.")
        st.image(png, width='stretch')
        st.download_button(label="이미지 다운로드 (PNG)", data=png,
                           file_name=f"{title}.png", mime="image/png", key=f"{key}_png")


st.title("근로자 혈압측정 명단")
st.markdown("고령자와 고혈압 재측정 대상자를 구분해 혈압 측정용 명단을 만듭니다.")
# --- 2. 사이드바 (좌측 메뉴) ---
with st.sidebar:
    st.header("근로자 명단")
    uploaded_file = st.file_uploader("엑셀 파일 선택", type=['xlsx', 'xls'])
    st.subheader("혈압 측정 기간")
    today = datetime.now(ZoneInfo('Asia/Seoul')).date()
    start_date = st.date_input("시작일", value=today, format='YYYY.MM.DD')
    end_date = st.date_input("종료일", value=today, format='YYYY.MM.DD')
    st.caption("하루만 측정하면 시작일과 종료일을 같게 설정하세요. 여러 날이면 일자 칸에 측정한 날을 직접 적을 수 있습니다.")
    
    st.markdown("---")
    st.info(
        "**엑셀 양식 안내**\n\n"
        "첫 행은 열 제목으로 사용합니다. A열부터 시작하는 원본 양식에서 다음 열을 읽습니다.\n"
        "- **D열**: 협력회사명 (소속)\n"
        "- **E열**: 직종 (공종)\n"
        "- **F열**: 성명 (이름)\n"
        "- **J열**: 국적\n"
        "- **L열**: 생년월일 (YYMMDD-1)\n"
        "- **Q열**: 최종 혈압 측정일과 결과 (예: 2026.10.16(150/100))"
    )

# --- 3. 메인 화면 ---
if end_date < start_date:
    st.warning("종료일을 시작일과 같거나 이후 날짜로 설정해 주세요.")
    st.stop()

st.caption(f"측정 기간: {start_date:%Y.%m.%d} ~ {end_date:%Y.%m.%d}")

if uploaded_file is None:
    st.info("왼쪽에서 근로자 명단 파일과 혈압 측정 기간을 선택해 주세요.")
else:
    try:
        with st.spinner("명단을 정리하고 있습니다."):
            source = pd.read_excel(uploaded_file)
            if source.shape[1] < 12:
                raise ValueError("L열까지 포함된 원본 엑셀 파일을 선택해 주세요.")
            df = source.iloc[:, [3, 4, 5, 9, 11]].copy()
            df.columns = ['협력회사명', '직종', '성명', '국적', '생년월일']
            has_pressure_column = source.shape[1] >= 17
            df['최종혈압결과'] = source.iloc[:, 16] if has_pressure_column else None

            total_workers = len(df)
            
            df['만_나이'] = df['생년월일'].apply(calculate_age)
            filtered_df = df[df['만_나이'] >= 63]
            filtered_df = filtered_df.sort_values(by=['협력회사명', '성명']).reset_index(drop=True)
            extracted_workers = len(filtered_df)

        high_df, readings = select_high_pressure_workers(df)
        col1, col2, col3 = st.columns(3)
        col1.metric(label="전체 근로자", value=f"{total_workers} 명")
        col2.metric(label="만 63세 이상", value=f"{extracted_workers} 명")
        col3.metric(label="고혈압 재측정 대상", value=f"{len(high_df)} 명")

        older_tab, pressure_tab = st.tabs(["고령자 혈압측정", "고혈압 근로자 혈압측정"])
        for tab, workers, group, key in [
            (older_tab, filtered_df, '고령자', 'older'),
            (pressure_tab, high_df, '고혈압 근로자', 'pressure'),
        ]:
            with tab:
                if key == 'pressure':
                    st.caption("Q열의 최종 혈압이 수축기 150 이상 또는 이완기 100 이상인 근로자입니다. 만 63세 이상은 고령자 명단에만 포함합니다.")
                    if not has_pressure_column:
                        st.warning("Q열이 없어 고혈압 대상자를 확인할 수 없습니다. Q열까지 포함된 원본 파일을 선택해 주세요.")
                        continue
                    eligible = df['만_나이'].between(0, 62)
                    unreadable = int((eligible & readings.isna()).sum())
                    if unreadable:
                        st.warning(f"만 63세 미만 중 {unreadable}명은 Q열의 혈압값이 없거나 형식을 확인할 수 없어 제외했습니다.")
                    unknown_age = int((df['만_나이'] < 0).sum())
                    if unknown_age:
                        st.warning(f"생년월일을 확인할 수 없는 {unknown_age}명은 고령자 제외 여부를 판단할 수 없어 제외했습니다.")
                if workers.empty:
                    st.info("해당하는 근로자가 없습니다.")
                    continue
                final_df = pd.DataFrame({
                    'No.': range(1, len(workers) + 1),
                    '협력회사': workers['협력회사명'],
                    '이름': workers['성명'],
                    '공종': workers['직종'],
                    '혈압잰 일자': [measurement_date_label(start_date, end_date)] * len(workers),
                    '오늘의 혈압': ['     /     '] * len(workers),
                    '고혈압 복용 여부': ['□예  □아니오'] * len(workers),
                    '서명란': [''] * len(workers),
                })
                title = measurement_title(start_date, end_date, group)
                output = create_excel(final_df, start_date, end_date, group)
                image = create_image(final_df, title, font_path)
                show_report(final_df, title, output, image, key)

    except Exception as e:
        st.error(f"명단을 만들지 못했습니다. 파일 형식과 열 위치를 확인해 주세요.\n\n오류 내용: {e}")
