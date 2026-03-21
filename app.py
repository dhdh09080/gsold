import streamlit as st
import pandas as pd
from datetime import datetime
import io
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import urllib.request
import os
import textwrap

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

def wrap_text_column(text, width=16):
    """지정한 너비를 넘으면 줄바꿈을 삽입합니다."""
    if not isinstance(text, str):
        return text
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
            # 최종 출력용 데이터프레임 구성
            final_df = pd.DataFrame({
                'No.': range(1, len(filtered_df) + 1),
                '협력회사': filtered_df['협력회사명'],
                '이름': filtered_df['성명'],
                '공종': filtered_df['직종'],
                '서명란': [''] * len(filtered_df)
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
            
            img_df = final_df[['No.', '협력회사', '이름', '공종']].copy()
            
            # 협력회사 열이 넓어졌으므로 줄바꿈 기준을 16자로 늘림
            img_df['협력회사'] = img_df['협력회사'].apply(lambda x: wrap_text_column(x, width=16))
            
            a4_inch = (8.27, 11.69)
            fig, ax = plt.subplots(figsize=a4_inch, dpi=300) 
            ax.axis('tight')
            ax.axis('off')
            
            # ★ 열 너비 비율 지정 (전체 합 = 1.0) ★
            # No: 8%, 협력회사: 45%, 이름: 20%, 공종: 27%
            col_widths = [0.08, 0.45, 0.20, 0.27]
            
            table = ax.table(
                cellText=img_df.values, 
                colLabels=img_df.columns, 
                colWidths=col_widths, # 열 너비 적용
                cellLoc='center', 
                loc='center'
            )
            
            table.auto_set_font_size(False)
            table.set_fontsize(11)

            # ★ 위아래 여백(셀 높이) 추가 확보 ★
            num_rows = len(img_df)
            if num_rows <= 10:
                row_scale = 3.5
            elif num_rows <= 25:
                row_scale = 2.8
            else:
                row_scale = 2.2 # 인원이 많아도 두 줄 텍스트가 잘리지 않도록 기본 높이 상향
            
            table.scale(1, row_scale)

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
