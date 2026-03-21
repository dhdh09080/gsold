import streamlit as st
import pandas as pd
from datetime import datetime
import io
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib import rcParams
import requests
from PIL import Image

# 1. 한글 폰트 다운로드 및 설정 (Streamlit Cloud 환경 대응)
@st.cache_resource # 폰트는 한 번만 다운로드하도록 캐싱
def load_nanum_font():
    """구글에서 나눔고딕 폰트를 다운로드하여 Matplotlib에 등록합니다."""
    # 나눔고딕 TTF 파일 URL
    font_url = 'https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf'
    font_response = requests.get(font_url)
    if font_response.status_code == 200:
        with open("NanumGothic-Bold.ttf", "wb") as f:
            f.write(font_response.content)
        
        # 폰트 등록
        fm.fontManager.addfont("NanumGothic-Bold.ttf")
        return "NanumGothic-Bold" # 폰트 이름 반환
    return None

def calculate_age(ssn_str):
    """생년월일(YYMMDD) 기반으로 만 나이를 계산하는 함수"""
    try:
        s = str(ssn_str).replace("-", "").strip()
        if len(s) < 6:
            return -1
            
        yy = int(s[:2])
        mm = int(s[2:4])
        dd = int(s[4:6])

        # 1926년생(만 100세) 이상의 경우 2026년생(만 0세)으로 인식되어 제외되므로, 실무상 고령자 필터링에 문제없음
        if yy <= 26:  
            year = 2000 + yy
        else:
            year = 1900 + yy

        birth_date = datetime(year, mm, dd)
        today = datetime.now()
        
        # 생일이 지났는지 여부에 따라 만 나이 계산
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except:
        return -1 # 날짜 형식이 잘못된 경우

# 폰트 로드 시도
font_name = load_nanum_font()
if font_name:
    plt.rcParams['font.family'] = font_name
else:
    # 폰트 다운로드 실패 시 로컬에서 맑은 고딕 시도
    plt.rcParams['font.family'] = 'Malgun Gothic' 

plt.rcParams['axes.unicode_minus'] = False # 마이너스 기호 깨짐 방지

st.set_page_config(page_title="고령 근로자 명단 추출", layout="wide")
st.title("만 63세 이상 근로자 명단 추출기 (A4 이미지 생성 지원)")

# 1. 엑셀 파일 업로드
uploaded_file = st.file_uploader("엑셀 파일을 업로드해 주세요 (A열부터 데이터가 시작한다고 가정)", type=['xlsx', 'xls'])

if uploaded_file is not None:
    # 엑셀 읽기 (B=1, C=2, D=3, E=4, G=6번째 인덱스 컬럼)
    # 헤더가 1행에 있다고 가정
    try:
        with st.spinner("엑셀 파일을 처리하는 중입니다..."):
            df = pd.read_excel(
                uploaded_file, 
                usecols=[1, 2, 3, 4, 6], 
                names=['협력회사명', '직종', '성명', '국적', '생년월일']
            )
            
            # 2. 데이터 변환 및 조건 필터링
            df['만_나이'] = df['생년월일'].apply(calculate_age)
            filtered_df = df[df['만_나이'] >= 63].reset_index(drop=True)

        if filtered_df.empty:
            st.warning("만 63세 이상 근로자가 없습니다.")
        else:
            # 최종 출력용 데이터프레임 구성
            final_df = pd.DataFrame({
                'No.': range(1, len(filtered_df) + 1),
                '성명': filtered_df['성명'],
                '협력회사명': filtered_df['협력회사명'],
                '직종': filtered_df['직종'],
                '서명란': [''] * len(filtered_df)
            })

            st.subheader(f"✅ 추출된 명단 (총 {len(final_df)}명)")
            st.dataframe(final_df, hide_index=True)

            # 3. 엑셀 다운로드 버튼
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                final_df.to_excel(writer, index=False, sheet_name='고령자명단')
            output.seek(0)
            
            st.download_button(
                label="📥 엑셀 파일 다운로드",
                data=output,
                file_name="만63세이상_명단.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # 4. 이미지로 명단 생성 (A4 사이즈, 서명란 제외)
            st.markdown("---")
            st.subheader("🖼️ 명단 이미지 (서명란 제외, A4 사이즈)")
            
            # 서명란을 제외한 데이터 추출
            img_df = final_df[['No.', '성명', '협력회사명', '직종']]
            
            # Matplotlib을 이용한 표 이미지화 (A4 사이즈 설정)
            # A4: 210mm x 297mm ≈ 8.27인치 x 11.69인치
            a4_inch = (8.27, 11.69)
            fig, ax = plt.subplots(figsize=a4_inch, dpi=300) # 고해상도 설정
            ax.axis('tight')
            ax.axis('off')
            
            # 표 생성
            table = ax.table(
                cellText=img_df.values, 
                colLabels=img_df.columns, 
                cellLoc='center', 
                loc='center'
            )
            
            # 표 스타일 및 폰트 설정
            table.auto_set_font_size(False)
            table.set_fontsize(14)
            table.scale(1, 2.5) # 셀 세로 크기 조정 (A4에 맞게 여백을 둠)
            
            # 이미지 제목 추가
            today_str = datetime.now().strftime("%Y-%m-%d")
            plt.title(f"만 63세 이상 고령 근로자 명단 ({today_str})", fontsize=20, fontfamily=font_name, pad=30)

            # 이미지를 메모리 버퍼에 저장 후 출력
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', bbox_inches='tight', dpi=300)
            img_buf.seek(0)
            
            # PIL로 이미지 열기 (크기 확인 및 다운로드 버튼 제공)
            img = Image.open(img_buf)
            
            st.image(img, use_container_width=True)

            # 이미지 다운로드 버튼 추가
            img_buf.seek(0)
            st.download_button(
                label="📥 명단 이미지 다운로드 (A4 PNG)",
                data=img_buf,
                file_name="만63세이상_명단.png",
                mime="image/png"
            )

    except Exception as e:
        st.error(f"파일을 처리하는 중 오류가 발생했습니다: {e}")
