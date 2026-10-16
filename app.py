import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import io
import urllib.request
import os
from excel_export import create_excel, measurement_date_label, measurement_title
from image_export import create_image
from history_store import list_reports, load_report, save_report

# --- 1. 기본 설정 및 함수 ---
st.set_page_config(page_title="고령자 혈압측정 명단", layout="wide")

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


def show_report(roster, title, excel, png):
    tab1, tab2 = st.tabs(["엑셀 명단", "이미지 명단"])
    with tab1:
        st.subheader(title)
        st.dataframe(roster, width='stretch', hide_index=True)
        st.download_button(
            label="엑셀 다운로드", data=excel, file_name=f"{title}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )
    with tab2:
        st.subheader("인쇄용 이미지")
        st.caption("이미지에는 협력회사, 이름, 공종이 표시됩니다. 혈압 기록용 서식은 엑셀로 내려받으세요.")
        st.image(png, width='stretch')
        st.download_button(label="이미지 다운로드 (PNG)", data=png,
                           file_name=f"{title}.png", mime="image/png")


st.title("고령자 혈압측정 명단")
st.markdown("근로자 명단에서 만 63세 이상을 골라 혈압 측정용 명단을 만듭니다.")
mode = st.sidebar.radio("메뉴", ["명단 만들기", "생성 기록"])
if mode == "생성 기록":
    st.subheader("생성 기록")
    st.caption("생성 당시의 명단과 파일을 다시 확인할 수 있습니다.")
    try:
        reports = list_reports()
        if not reports:
            st.info("아직 생성한 명단이 없습니다. ‘명단 만들기’에서 엑셀 파일을 올려 주세요.")
        else:
            records = {report['id']: report for report in reports}
            selected = st.selectbox(
                "기록 선택", options=list(records),
                format_func=lambda key: records[key]['label'] + " · " +
                datetime.fromisoformat(records[key]['created_at']).strftime('%m.%d %H:%M:%S'),
            )
            report = load_report(selected)
            if report is None:
                st.warning("기록을 찾을 수 없습니다. 목록을 새로고침해 주세요.")
            else:
                roster = pd.read_json(io.StringIO(report['roster']), orient='split', dtype=False)
                created = datetime.fromisoformat(report['created_at']).strftime('%Y.%m.%d %H:%M')
                st.caption(f"생성일: {created} · 대상자: {len(roster)}명")
                show_report(roster, report['title'], report['excel'], report['png'])
    except Exception as e:
        st.error(f"생성 기록을 불러오지 못했습니다.\n\n오류 내용: {e}")
    st.sidebar.caption("기록은 현재 서버에 저장됩니다. 서버 교체나 재배포 시 초기화될 수 있으니 필요한 파일은 내려받아 보관해 주세요.")
    st.stop()

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
        "- **L열**: 생년월일 (YYMMDD-1)"
    )

# --- 3. 메인 화면 ---
if end_date < start_date:
    st.warning("종료일을 시작일과 같거나 이후 날짜로 설정해 주세요.")
    st.stop()

report_title = measurement_title(start_date, end_date)
st.caption(f"명단 제목: {report_title}")

if uploaded_file is None:
    st.info("왼쪽에서 근로자 명단 파일과 혈압 측정 기간을 선택해 주세요.")
else:
    try:
        with st.spinner("명단을 정리하고 있습니다."):
            # ★ 변경된 열(Column) 위치 반영 ★
            # D(3), E(4), F(5), J(9), L(11)
            df = pd.read_excel(
                uploaded_file, 
                usecols=[3, 4, 5, 9, 11], 
                names=['협력회사명', '직종', '성명', '국적', '생년월일']
            )
            
            total_workers = len(df)
            
            df['만_나이'] = df['생년월일'].apply(calculate_age)
            filtered_df = df[df['만_나이'] >= 63]
            filtered_df = filtered_df.sort_values(by=['협력회사명', '성명']).reset_index(drop=True)
            extracted_workers = len(filtered_df)

        # --- 대시보드 (요약 메트릭) ---
        st.markdown("---")
        col1, col2 = st.columns(2)
        col1.metric(label="전체 근로자", value=f"{total_workers} 명")
        col2.metric(label="만 63세 이상", value=f"{extracted_workers} 명")
        
        if filtered_df.empty:
            st.warning("만 63세 이상 근로자가 없습니다.")
        else:
            final_df = pd.DataFrame({
                'No.': range(1, len(filtered_df) + 1),
                '협력회사': filtered_df['협력회사명'],
                '이름': filtered_df['성명'],
                '공종': filtered_df['직종'],
                '혈압잰 일자': [measurement_date_label(start_date, end_date)] * len(filtered_df),
                '오늘의 혈압': ['     /     '] * len(filtered_df),
                '서명란': [''] * len(filtered_df)
            })
            
            output = create_excel(final_df, start_date, end_date)
            image = create_image(final_df, report_title, font_path)
            try:
                save_report(final_df, start_date, end_date, report_title, total_workers,
                            output, image)
                st.caption("생성 기록에 저장했습니다. 왼쪽 ‘생성 기록’에서 다시 볼 수 있습니다.")
            except Exception as e:
                st.warning(f"파일은 생성했지만 기록을 저장하지 못했습니다. 필요한 파일을 내려받아 주세요. ({e})")
            show_report(final_df, report_title, output, image)

    except Exception as e:
        st.error(f"명단을 만들지 못했습니다. 파일 형식과 열 위치를 확인해 주세요.\n\n오류 내용: {e}")
