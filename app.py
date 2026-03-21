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
    
    if not os.path.exists(font_path):
        urllib.request.urlretrieve(font_url, font_path)
        
    fm.fontManager.addfont(font_path)
    font_prop = fm.FontProperties(fname=font_path)
    font_name = font_prop.get_name()
    
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
            
            df['만_나이'] = df['생년월일'].apply(calculate_age)
            filtered_df = df[df['만_나이'] >= 63]
            filtered_df = filtered_df.sort_values(by=['협력회사명', '성명']).reset_index(drop=True)

        if filtered_df.empty:
            st.warning("만 63세 이상 근로자가 없습니다.")
        else:
            final_df = pd.DataFrame({
                'No.': range(1, len(filtered_df) + 1),
                '협력회사': filtered_df['협력회사명'],
                '이름': filtered_df['성명'],
                '공종': filtered_df['직종'],
                '서명란': [''] * len(filtered_df)
            })

            st.subheader(f"✅ 추출된 명단 (총 {len(final_df)}명)")
            st.dataframe(final_df, hide_index=True)

            # --- 엑셀 다운로드 (포맷팅 및 인쇄 설정 포함) ---
            
            # 수기 작성을 위한 빈 행 10줄 추가
            excel_df = final_df.copy()
            empty_rows = pd.DataFrame([[''] * len(excel_df.columns)] * 10, columns=excel_df.columns)
            excel_df = pd.concat([excel_df, empty_rows], ignore_index=True)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                excel_df.to_excel(writer, index=False, sheet_name='고령자명단')
                
                workbook = writer.book
                worksheet = writer.sheets['고령자명단']
                
                # 엑셀 셀 서식 정의 (테두리, 가운데 정렬, 배경색)
                header_format = workbook.add_format({
                    'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9D9D9'
                })
                cell_format = workbook.add_format({
                    'border': 1, 'align': 'center', 'valign': 'vcenter'
                })
                
                # 헤더 서식 덮어쓰기
                for col_num, value in enumerate(excel_df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    
                # 데이터 서식 덮어쓰기 (빈 줄 10줄까지 모두 테두리 적용)
                for row_num in range(len(excel_df)):
                    for col_num in range(len(excel_df.columns)):
                        val = excel_df.iloc[row_num, col_num]
                        if pd.isna(val): 
                            val = ''
                        worksheet.write(row_num + 1, col_num, val, cell_format)
                
                # 열 너비 설정 (E열 서명란 확장)
                worksheet.set_column('A:A', 6)  # No.
                worksheet.set_column('B:B', 25) # 협력회사
                worksheet.set_column('C:C', 12) # 이름
                worksheet.set_column('D:D', 16) # 공종
                worksheet.set_column('E:E', 30) # 서명란 (크게)
                
                # 인쇄 설정 (A4, 1장 너비 맞춤, 1행 반복)
                worksheet.set_paper(9) # 9 = A4 용지
                worksheet.fit_to_pages(1, 0) # 1페이지 너비에 맞춤, 길이는 제한 없음
                worksheet.repeat_rows(0) # 첫 번째 줄(헤더)을 모든 인쇄 페이지 상단에 반복
            
            output.seek(0)
            
            st.download_button(
                label="📥 엑셀 파일 다운로드",
                data=output,
                file_name="만63세이상_명단.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # --- 이미지 생성 ---
            st.markdown("---")
            st.subheader("🖼️ 명단 이미지 (서명란 제외, A4 사이즈)")
            
            img_df = final_df[['No.', '협력회사', '이름', '공종']].copy()
            img_df['협력회사'] = img_df['협력회사'].apply(lambda x: wrap_text_column(x, width=16))
            
            a4_inch = (8.27, 11.69)
            fig, ax = plt.subplots(figsize=a4_inch, dpi=300) 
            ax.axis('tight')
            ax.axis('off')
            
            col_widths = [0.08, 0.45, 0.20, 0.27]
            
            table = ax.table(
                cellText=img_df.values, 
                colLabels=img_df.columns, 
                colWidths=col_widths, 
                cellLoc='center', 
                loc='center'
            )
            
            table.auto_set_font_size(False)
            table.set_fontsize(11)

            num_rows = len(img_df)
            if num_rows <= 10:
                row_scale = 3.5
            elif num_rows <= 25:
                row_scale = 2.8
            else:
                row_scale = 2.2 
            
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
