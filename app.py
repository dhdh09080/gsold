import streamlit as st
import pandas as pd
from datetime import datetime
import io
import matplotlib.pyplot as plt

# 폰트 설정 (환경에 따라 'Malgun Gothic' 또는 'AppleGothic', 'NanumGothic' 등으로 변경 필요)
plt.rcParams['font.family'] = 'Malgun Gothic' 
plt.rcParams['axes.unicode_minus'] = False

def calculate_age(ssn_str):
    """생년월일(YYMMDD) 기반으로 만 나이를 계산하는 함수"""
    try:
        # 문자열로 변환 후 공백 및 하이픈 제거
        s = str(ssn_str).replace("-", "").strip()
        if len(s) < 6:
            return -1
            
        yy = int(s[:2])
        mm = int(s[2:4])
        dd = int(s[4:6])

        # 출생 연도 판별 (26년도 이하를 2000년대생으로 가정 시, 63세 이상 조건에 어차피 부합하지 않음)
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

st.set_page_config(page_title="고령 근로자 명단 추출", layout="wide")
st.title("만 63세 이상 근로자 명단 추출기")

# 1. 엑셀 파일 업로드
uploaded_file = st.file_uploader("엑셀 파일을 업로드해 주세요 (A열부터 데이터가 시작한다고 가정)", type=['xlsx', 'xls'])

if uploaded_file is not None:
    # 엑셀 읽기 (B=1, C=2, D=3, E=4, G=6번째 인덱스 컬럼)
    # 헤더가 1행에 있다고 가정
    try:
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

            # 4. 이미지로 명단 생성 (서명란 제외)
            st.markdown("---")
            st.subheader("🖼️ 명단 이미지 (서명란 제외)")
            
            # 서명란을 제외한 데이터 추출
            img_df = final_df[['No.', '성명', '협력회사명', '직종']]
            
            # matplotlib을 이용한 표 이미지화
            fig, ax = plt.subplots(figsize=(8, len(img_df) * 0.5 + 1))
            ax.axis('tight')
            ax.axis('off')
            
            table = ax.table(
                cellText=img_df.values, 
                colLabels=img_df.columns, 
                cellLoc='center', 
                loc='center'
            )
            table.auto_set_font_size(False)
            table.set_fontsize(11)
            table.scale(1, 2) # 셀 크기 조정

            # 이미지를 메모리 버퍼에 저장 후 출력
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', bbox_inches='tight', dpi=300)
            img_buf.seek(0)
            
            st.image(img_buf, use_container_width=True)

    except Exception as e:
        st.error(f"파일을 처리하는 중 오류가 발생했습니다: {e}")
