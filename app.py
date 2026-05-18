import streamlit as st
import pandas as pd
from datetime import datetime
import io
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import urllib.request
import os
import textwrap

# --- 1. 기본 설정 및 함수 ---
st.set_page_config(page_title="고령 근로자 명단 추출기", page_icon="👷‍♂️", layout="wide")

@st.cache_resource
def set_korean_font():
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

def wrap_text_column(text, width=16):
    if not isinstance(text, str): return text
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=True))

font_name = set_korean_font()

# --- 2. 사이드바 (좌측 메뉴) ---
with st.sidebar:
    st.header("📁 엑셀 파일 업로드")
    uploaded_file = st.file_uploader("여기에 파일을 드래그 앤 드롭하세요.", type=['xlsx', 'xls'])
    
    st.markdown("---")
    st.info(
        "💡 **데이터 양식 안내**\n\n"
        "A열부터 시작해야 하며, 아래 열을 참조합니다.\n"
        "- **D열**: 협력회사\n"
        "- **E열**: 직종\n"
        "- **F열**: 성명\n"
        "- **I열**: 국적\n"
        "- **K열**: 주민번호 (YYMMDD-1)"
    )

# --- 3. 메인 화면 ---
st.title("👷‍♂️ 만 63세 이상 고령 근로자 추출기")
st.markdown("업로드한 엑셀 파일에서 만 63세 이상의 근로자를 자동으로 필터링하여 인쇄용 명단을 생성합니다.")

if uploaded_file is None:
    st.success("👈 좌측 사이드바에서 엑셀 파일을 업로드해 주세요!")
else:
    try:
        with st.spinner("데이터를 분석하고 이미지를 생성하는 중입니다... 잠시만 기다려주세요!"):
            # 변경된 열 인덱스 적용 (D=3, E=4, F=5, I=8, K=10)
            df = pd.read_excel(
                uploaded_file, 
                usecols=[3, 4, 5, 8, 10], 
                names=['협력회사명', '직종', '성명', '국적', '주민번호']
            )
            
            total_workers = len(df)
            
            # 생년월일 대신 주민번호 컬럼으로 나이 계산
            df['만_나이'] = df['주민번호'].apply(calculate_age)
            filtered_df = df[df['만_나이'] >= 63]
            filtered_df = filtered_df.sort_values(by=['협력회사명', '성명']).reset_index(drop=True)
            extracted_workers = len(filtered_df)

        # --- 대시보드 (요약 메트릭) ---
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric(label="📋 전체 근로자 수", value=f"{total_workers} 명")
        col2.metric(label="🚨 만 63세 이상 추출", value=f"{extracted_workers} 명", delta="대상자")
        
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

            # 오늘 날짜 가져오기 (YYYY-MM-DD 형식)
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            # --- 탭 구성 ---
            tab1, tab2 = st.tabs(["📊 엑셀 명단 확인 및 다운로드", "🖼️ A4 이미지 명단 (서명란 제외)"])
            
            # --- [TAB 1] 엑셀 화면 ---
            with tab1:
                st.subheader("✅ 엑셀 데이터 미리보기")
                st.dataframe(final_df, use_container_width=True, hide_index=True)

                excel_df = final_df.copy()
                empty_rows = pd.DataFrame([[''] * len(excel_df.columns)] * 10, columns=excel_df.columns)
                excel_df = pd.concat([excel_df, empty_rows], ignore_index=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    excel_df.to_excel(writer, index=False, sheet_name='고령자명단')
                    workbook = writer.book
                    worksheet = writer.sheets['고령자명단']
                    
                    header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9D9D9'})
                    cell_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
                    
                    for col_num, value in enumerate(excel_df.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                        
                    for row_num in range(len(excel_df)):
                        for col_num in range(len(excel_df.columns)):
                            val = excel_df.iloc[row_num, col_num]
                            if pd.isna(val): val = ''
                            worksheet.write(row_num + 1, col_num, val, cell_format)
                    
                    worksheet.set_column('A:A', 6)
                    worksheet.set_column('B:B', 25)
                    worksheet.set_column('C:C', 12)
                    worksheet.set_column('D:D', 16)
                    worksheet.set_column('E:E', 30)
                    
                    worksheet.set_paper(9)
                    worksheet.fit_to_pages(1, 0)
                    worksheet.repeat_rows(0)
                
                output.seek(0)
                
                # 파일명에 오늘 날짜 적용
                st.download_button(
                    label="📥 완벽하게 세팅된 엑셀 파일 다운로드",
                    data=output,
                    file_name=f"{today_str}_고령자 혈압 관리 명단.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

            # --- [TAB 2] 이미지 화면 ---
            with tab2:
                st.subheader("🖼️ A4 인쇄용 이미지 미리보기")
                st.caption("※ 서명란이 제외된 간략한 명단입니다. 우측 하단의 버튼을 눌러 저장하세요.")
                
                img_df = final_df[['No.', '협력회사', '이름', '공종']].copy()
                img_df['협력회사'] = img_df['협력회사'].apply(lambda x: wrap_text_column(x, width=16))
                
                a4_inch = (8.27, 11.69)
                fig, ax = plt.subplots(figsize=a4_inch, dpi=300) 
                ax.axis('tight')
                ax.axis('off')
                
                col_widths = [0.08, 0.45, 0.20, 0.27]
                table = ax.table(cellText=img_df.values, colLabels=img_df.columns, colWidths=col_widths, cellLoc='center', loc='center')
                table.auto_set_font_size(False)
                table.set_fontsize(11)

                num_rows = len(img_df)
                if num_rows <= 10: row_scale = 3.5
                elif num_rows <= 25: row_scale = 2.8
                else: row_scale = 2.2 
                table.scale(1, row_scale)

                img_buf = io.BytesIO()
                plt.savefig(img_buf, format='png', bbox_inches='tight', dpi=300)
                img_buf.seek(0)
                
                st.image(img_buf, use_container_width=True)

                # 이미지 파일명에도 동일하게 오늘 날짜 적용
                st.download_button(
                    label="📥 A4 명단 이미지 다운로드 (PNG)",
                    data=img_buf,
                    file_name=f"{today_str}_고령자 혈압 관리 명단.png",
                    mime="image/png"
                )

    except Exception as e:
        st.error(f"⚠️ 엑셀 파일을 읽는 중 오류가 발생했습니다. 양식이 맞는지 확인해주세요.\n\n상세 오류: {e}")
