import streamlit as st
import pandas as pd
from datetime import datetime
import io
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import urllib.request
import os
import textwrap # ★ 줄바꿈을 위해 추가된 라이브러리 ★

# 1. 한글 폰트 확실하게 설정하기 (Streamlit Cloud 호환)
@st.cache_resource
def set_korean_font():
    """구글 폰트에서 나눔고딕을 다운로드하고 Matplotlib에 강제 적용합니다."""
    font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    font_path = "NanumGothic.ttf"
    
    # 폰트 파일이 없으면 다운로드
    if not os.path.exists(font_path):
        urllib.request.urlretrieve(font_url, font_path)
        
    # Matplotlib에 폰트 추가 및 이름 추출
    fm.fontManager.addfont(font_path)
    font_prop = fm.FontProperties(fname=font_path)
    font_name = font_prop.get_name()
    
    # 전역 폰트 설정
    plt.rc('font', family=font_name)
    plt.rcParams['axes.unicode_minus'] = False
    
    return font_name

def calculate_age(ssn_str):
    """생년월일(YYMMDD) 기반으로 만 나이를 계산하는 함수"""
    try:
        s = str(ssn_str).replace("-", "").strip()
        if len(s) < 6:
            return -1
            
        yy = int(s[:2])
        mm = int(s[2:4])
        dd = int(s[4:6])

        if yy <= 26:  
            year = 2000 + yy
        else:
            year = 1900 + yy

        birth_date = datetime(year, mm, dd)
        today = datetime.now()
        
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except:
        return -1 

# ★ 긴 업체명 줄바꿈을 위한 함수 ★
def wrap_text_column(text, width=12):
    """지정한 너비(글자 수)를 넘으면 줄바꿈을 삽입합니다."""
    if not isinstance(text, str):
        return text
    # textwrap.wrap은 공백 기준으로 자르지만, 한국어는 공백이 적어 brutal split을 방지하기 위해 break_long_words=True를 사용
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=True))

# 폰트 적용 실행
font_name = set_korean_font()

st.set_page_config(page_title="고령 근로자 명단 추출", layout="wide")
st.title("만 63세 이상 근로자 명단 추출기")

uploaded_file = st.file_uploader("엑셀 파일을 업로드해 주세요 (A열부터 데이터가 시작한다고 가정)", type=['xlsx', 'xls'])

if uploaded_file is not None:
    try:
        with st.spinner("데이터를 처리하고 있습니다..."):
            df = pd.read_excel(
                uploaded_file, 
                usecols=[1, 2, 3, 4, 6], 
                names=['협력회사명', '직종', '성명', '국적', '생년월일']
            )
            
            # 나이 계산 및 63세 이상 필터링
            df['만_나이'] = df['생년월일'].apply(calculate_age)
            filtered_df = df[df['만_나이'] >= 63]

            # 협력회사명 1순위, 성명 2순위로 가나다순 정렬
            filtered_df = filtered_df.sort_values(by=['협력회사명', '성명']).reset_index(drop=True)

        if filtered_df.empty:
            st.warning("만 63세 이상 근로자가 없습니다.")
        else:
            # 엑셀 다운로드용 데이터프레임 구성 (서명란 포함)
            final_df = pd.DataFrame({
                'No.': range(1, len(filtered_df) + 1), # A열
                '협력회사': filtered_df['협력회사명'],   # B열
                '이름': filtered_df['성명'],           # C열
                '공종': filtered_df['직종'],           # D열
                '서명란': [''] * len(filtered_df)      # E열
            })

            st.subheader(f"✅ 추출된 명단 (총 {len(final_df)}명)")
            st.dataframe(final_df, hide_index=True)

            # 엑셀 다운로드 
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

            # 이미지 생성 (A4 사이즈, 서명란 제외)
            st.markdown("---")
            st.subheader("🖼️ 명단 이미지 (서명란 제외, A4 사이즈)")
            
            # 이미지용 데이터 추출
            img_df = final_df[['No.', '협력회사', '이름', '공종']].copy()
            
            # ★ 텍스트 줄바꿈 적용 ★
            # 업체명 컬럼에 대해 한 줄에 약 12~13자 정도만 표시되도록 줄바꿈을 적용합니다. 
            # 한글은 영문보다 너비가 넓으므로, width 값을 조정해 보면서 최적의 값을 찾으시면 됩니다.
            img_df['협력회사'] = img_df['협력회사'].apply(lambda x: wrap_text_column(x, width=12))
            
            a4_inch = (8.27, 11.69)
            fig, ax = plt.subplots(figsize=a4_inch, dpi=300) 
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
            table.set_fontsize(11) # 조금 더 작게 설정하여 더 많은 내용을 담을 수 있게 함

            # ★ 행 높이 동적 조정 ★
            # 명단이 많을수록 행 높이를 줄여서 A4에 더 잘 맞춥니다.
            num_rows = len(img_df)
            if num_rows <= 10:
                row_scale = 3.0
            elif num_rows <= 25:
                row_scale = 2.3
            else:
                row_scale = 1.8 # 25명 이상일 때 행 높이를 최소로
            
            table.scale(1, row_scale) # 셀 세로 크기 조정

            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', bbox_inches='tight', dpi=300)
            img_buf.seek(0)
            
            st.image(img_buf, use_container_width=True)

            img_buf.seek(0)
            st.download_button(
                label="📥 명단 이미지 다운로드 (A4 PNG)",
                data=img_buf,
                file_name="만63세이상_명단.png",
                mime="image/png"
            )

    except Exception as e:
        st.error(f"파일을 처리하는 중 오류가 발생했습니다: {e}")
