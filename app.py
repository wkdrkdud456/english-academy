"""
앨리영어 - 1인 학원 맞춤형 AI 종합 관리 대시보드 시스템
Streamlit 웹 애플리케이션
"""
import streamlit as st
import pandas as pd
import json
import os
import io
import base64
from datetime import datetime, timedelta
from PIL import Image

# 내부 모듈
from db_manager import *
from ai_service import *
from messaging import send_solapi_message

# ─── 페이지 설정 ─────────────────────────────────────────────
st.set_page_config(
    page_title="앨리영어 AI 대시보드",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── 스타일링 ────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: 700; color: #1E3A5F; padding: 0.5rem 0; }
    .sub-header { font-size: 1.3rem; font-weight: 600; color: #2E5A8F; padding: 0.3rem 0; }
    .warning-banner {
        background-color: #FFE4E4; border-left: 5px solid #FF0000;
        padding: 1rem; border-radius: 5px; margin: 0.5rem 0; color: #CC0000; font-weight: 600;
    }
    .info-card {
        background-color: #F0F6FF; border: 1px solid #D0E0FF;
        padding: 1.2rem; border-radius: 10px; margin: 0.5rem 0;
    }
    .analysis-box {
        background-color: #FFF8E1; border: 1px solid #FFE082;
        padding: 1rem; border-radius: 8px; margin: 0.5rem 0;
    }
    .timeline-item {
        border-left: 3px solid #2E5A8F; padding-left: 1rem; margin: 0.5rem 0;
    }
    .stButton button {
        width: 100%; border-radius: 8px; font-weight: 600;
    }
    .report-box {
        background-color: #F9FAFB; border: 2px solid #E5E7EB;
        padding: 1.5rem; border-radius: 10px; margin: 1rem 0;
        white-space: pre-wrap; font-family: 'Malgun Gothic', sans-serif;
        line-height: 1.8;
    }
</style>
""", unsafe_allow_html=True)

# ─── 세션 상태 초기화 ──────────────────────────────────────
if "db_initialized" not in st.session_state:
    init_database()
    st.session_state.db_initialized = True
if "api_key_checked" not in st.session_state:
    st.session_state.api_key_checked = False
if "last_exam_result" not in st.session_state:
    st.session_state.last_exam_result = None
if "weekly_report" not in st.session_state:
    st.session_state.weekly_report = None
if "weekly_report_editable" not in st.session_state:
    st.session_state.weekly_report_editable = ""

# ─── 상단 우측 설정 버튼 ───────────────────────────────
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; padding:0 0 0.5rem 0;">
    <div style="display:flex; align-items:center; gap:10px;">
        <span style="font-size:2rem;">📚</span>
        <div>
            <span style="font-size:1.4rem; font-weight:700; color:#1E3A5F;">앨리영어</span>
            <span style="font-size:0.8rem; color:#888; margin-left:8px;">대치동 1인 학원 AI 시스템</span>
        </div>
    </div>
    <div style="display:flex; align-items:center; gap:4px;">
        <span style="font-size:0.75rem; color:#999;">{datetime.now().strftime('%Y-%m-%d')}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── 사이드바 ───────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/000000/english-mustache.png", width=60)
    st.markdown("<h2 style='text-align: center;'>앨리영어</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>대치동 1인 학원 AI 시스템</p>", unsafe_allow_html=True)
    st.divider()
    
    # ⚙️ 설정 (사이드바 상단에 톱니바퀴 스타일로)
    with st.expander("⚙️ 설정", expanded=False):
        st.markdown("**🔑 API 키**")
        gemini_api_key = st.text_input(
            "Google Gemini API 키",
            value="AIzaSyD09hiLSytx9ssdYxphAvMWJ8JZChTpdaI",
            type="password",
            key="gemini_key_input",
            help="gemini-2.5-flash 모델 사용. 변경하려면 수정하세요."
        )
        solapi_api_key = st.text_input(
            "솔라피 API Key",
            value=os.getenv("SOLAPI_API_KEY", ""),
            type="password",
            key="solapi_key_input"
        )
        solapi_api_secret = st.text_input(
            "솔라피 API Secret",
            value=os.getenv("SOLAPI_API_SECRET", ""),
            type="password",
            key="solapi_secret_input"
        )
        solapi_from_number = st.text_input(
            "발신 번호",
            value=os.getenv("SOLAPI_FROM_NUMBER", ""),
            key="solapi_from_input"
        )
        if st.button("💾 설정 저장", use_container_width=True):
            st.success("✅ 설정이 저장되었습니다.")
            st.rerun()
        
        st.divider()
        
        st.markdown("**🗄️ 데이터베이스**")
        if st.button("🔄 DB 초기화 (academy.db 삭제 후 재생성)", use_container_width=True, type="secondary"):
            import os
            db_path = "academy.db"
            if os.path.exists(db_path):
                os.remove(db_path)
            init_database()
            st.success("✅ DB가 초기화되었습니다! (샘플 데이터 2개 반, 3명 학생)")
            st.rerun()
        
        st.caption("💡 API 키 수정이 필요하면 여기서 변경하세요.")
    
    st.divider()
    
    # 메뉴 네비게이션
    menu = st.radio(
        "📋 메뉴 선택",
        ["📊 대시보드 & 출석 관리",
         "📖 교재 분석 & 단어장",
         "🔬 시험지 OCR 진단",
         "🏫 학교별 기출 경향",
         "📋 학생 히스토리 & 주간 발송"],
        index=0
    )
    
    st.divider()
    st.caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.caption("© 2025 앨리영어 Academy AI System v1.0")


# ─── 메뉴 1: 대시보드 & 출석 관리 ─────────────────────────
if menu == "📊 대시보드 & 출석 관리":
    st.markdown("<div class='main-header'>📊 대시보드 & 출석 관리</div>", unsafe_allow_html=True)
    
    # 알림판: 잔여 수업 1회 이하 학생
    low_students = get_low_session_students(1)
    if low_students:
        for s in low_students:
            st.markdown(
                f"<div class='warning-banner'>⚠️ [{s['name']}] 수강료 재등록 시점입니다! (잔여 {s['remaining_sessions']}회)</div>",
                unsafe_allow_html=True
            )
    else:
        st.info("✅ 모든 학생의 수강 잔여 횟수가 충분합니다.")
    
    # 통계 카드
    all_students = get_all_students()
    all_classes = get_all_classes()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📚 전체 반", len(all_classes))
    with col2:
        st.metric("👨‍🎓 전체 학생", len(all_students))
    with col3:
        active = sum(1 for s in all_students if s["remaining_sessions"] > 0)
        st.metric("✅ 수업 진행중", active)
    with col4:
        need_renew = sum(1 for s in all_students if s["remaining_sessions"] <= 1)
        st.metric("⚠️ 재등록 필요", need_renew)
    
    st.divider()
    st.markdown("<div class='sub-header'>📅 주간 수업 일정</div>", unsafe_allow_html=True)
    
    # 요일 매핑
    day_map = {"월": "Monday", "화": "Tuesday", "수": "Wednesday", "목": "Thursday", "금": "Friday", "토": "Saturday", "일": "Sunday"}
    day_map_kr = {"월": "월요일", "화": "화요일", "수": "수요일", "목": "목요일", "금": "금요일", "토": "토요일", "일": "일요일"}
    
    # 달력 표시용 데이터
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    
    cols = st.columns(7)
    days_kr = ["월", "화", "수", "목", "금", "토", "일"]
    for i, (col, day) in enumerate(zip(cols, days_kr)):
        date = week_start + timedelta(days=i)
        with col:
            st.markdown(f"**{day_map_kr[day]}**\n\n{date.strftime('%m/%d')}", help=f"{date.strftime('%Y-%m-%d')}")
            classes_today = [c for c in all_classes if day in c["day_of_week"]]
            if classes_today:
                for c in classes_today:
                    st.markdown(f"""
                    <div style='background:#E8F0FE; border-radius:8px; padding:8px; margin:4px 0; font-size:0.85rem; text-align:center;'>
                        <strong>{c['name']}</strong><br>
                        🕐 {c['time_slot']}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("휴무")
    
    st.divider()
    st.markdown("<div class='sub-header'>👨‍🎓 반별 출석 관리</div>", unsafe_allow_html=True)
    
    # 반 선택
    class_options = {c["name"]: c["id"] for c in all_classes}
    selected_class_name = st.selectbox("반을 선택하세요", list(class_options.keys()), key="class_select")
    selected_class_id = class_options[selected_class_name]
    
    students_in_class = get_students_by_class(selected_class_id)
    
    if students_in_class:
        st.markdown(f"**{selected_class_name} - 학생 목록**")
        for student in students_in_class:
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])
            with col1:
                today_att = get_today_attendance(student["id"])
                status_icon = ""
                if today_att:
                    if today_att["status"] == "출석":
                        status_icon = "✅"
                    elif today_att["status"] == "결석":
                        status_icon = "❌"
                    else:
                        status_icon = "🔄"
                st.markdown(f"{status_icon} **{student['name']}** (잔여 {student['remaining_sessions']}회)")
            
            with col3:
                if st.button(f"✅ 출석", key=f"att_{student['id']}"):
                    today_att = get_today_attendance(student["id"])
                    if today_att:
                        st.warning(f"{student['name']}은(는) 이미 오늘 출석이 기록되었습니다.")
                    else:
                        mark_attendance(student["id"], "출석")
                        st.success(f"{student['name']} 출석 처리 완료! (잔여 {student['remaining_sessions']-1}회)")
                        st.rerun()
            
            with col4:
                if st.button(f"❌ 결석", key=f"abs_{student['id']}"):
                    today_att = get_today_attendance(student["id"])
                    if today_att:
                        st.warning(f"{student['name']}은(는) 이미 오늘 기록이 있습니다.")
                    else:
                        mark_attendance(student["id"], "결석")
                        st.success(f"{student['name']} 결석 처리 완료.")
                        st.rerun()
            
            with col5:
                if today_att:
                    st.caption(f"✔ 오늘: {today_att['status']}")
    else:
        st.info("해당 반에 등록된 학생이 없습니다.")


# ─── 메뉴 2: 교재 분석 & 단어장 생성 ──────────────────────
elif menu == "📖 교재 분석 & 단어장":
    st.markdown("<div class='main-header'>📖 교재 분석 & 단어장 생성</div>", unsafe_allow_html=True)
    st.markdown("PDF 파일을 업로드하면 AI가 핵심 단어 **50개**를 추출합니다. 원하는 단어만 골라 엑셀로 다운로드할 수 있습니다.")
    
    uploaded_pdf = st.file_uploader("📄 수업용 PDF 파일 업로드", type=["pdf"], key="pdf_uploader")
    
    if uploaded_pdf is not None:
        pdf_bytes = uploaded_pdf.getvalue()
        api_key = st.session_state.get("gemini_key_input", os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")))
        if not api_key:
            st.warning("⚠️ Google Gemini API 키가 필요합니다. 스캔 PDF OCR + 단어장 생성을 위해 사이드바에서 API 키를 입력해주세요.")
        
        pdf_text = None
        with st.spinner("📄 PDF 텍스트 추출 중..."):
            try:
                if api_key:
                    pdf_text, used_ocr = process_pdf_with_ocr(api_key, pdf_bytes)
                    if pdf_text is None:
                        st.error(f"PDF 처리 실패: {used_ocr}")
                        st.info("스캔 PDF의 경우 Gemini API 키가 필요합니다. 사이드바에서 설정해주세요.")
                    else:
                        method = "🔍 OCR (스캔 PDF)" if used_ocr else "📄 일반 텍스트 추출"
                        st.success(f"✅ {method} 완료! (약 {len(pdf_text)}자)")
                else:
                    import pdfplumber
                    import io
                    pdf_text = ""
                    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                pdf_text += text + "\n"
                    if not pdf_text.strip():
                        st.error("PDF에서 텍스트를 추출할 수 없습니다. 스캔 PDF는 Gemini API 키 설정이 필요합니다.")
                        pdf_text = None
                    else:
                        st.success(f"✅ 텍스트 추출 완료! (약 {len(pdf_text)}자)")
            except Exception as e:
                st.error(f"PDF 처리 중 오류: {str(e)}")
        
        if pdf_text and pdf_text.strip():
            with st.expander("📝 추출된 텍스트 미리보기"):
                st.text_area("원문", pdf_text[:2000], height=200)
            
            st.divider()
            
            if api_key:
                if st.button("🤖 AI 단어장 생성하기 (50개)", use_container_width=True, type="primary"):
                    with st.spinner("🧠 AI가 핵심 단어 50개를 분석 중입니다..."):
                        result = extract_vocabulary(api_key, pdf_text)
                        if result is None:
                            st.error("API 키가 유효하지 않습니다.")
                        elif isinstance(result, dict) and "error" in result:
                            st.error(f"분석 중 오류: {result['error']}")
                            if "raw_result" in result:
                                st.code(result["raw_result"])
                        else:
                            st.session_state.vocab_result = result
                            st.success("✅ 50개 단어 분석 완료!")
                            st.rerun()
    
    # 결과 표시 + 선택형 엑셀 다운로드
    if "vocab_result" in st.session_state and st.session_state.vocab_result is not None:
        st.markdown("<div class='sub-header'>📋 AI 생성 단어장 (50개)</div>", unsafe_allow_html=True)
        
        result = st.session_state.vocab_result
        if isinstance(result, list):
            df = pd.DataFrame(result)
            
            # 번호 컬럼 추가
            df.index = df.index + 1
            df.index.name = "번호"
            
            # 각 단어에 체크박스를 위한 데이터 준비
            st.markdown("**✅ 엑셀에 포함할 단어를 선택하세요 (기본 전체 선택)**")
            
            # 세션에 선택 상태 저장
            if "vocab_selected" not in st.session_state or len(st.session_state.vocab_selected) != len(df):
                st.session_state.vocab_selected = [True] * len(df)
            
            # 전체 선택/해제 토글
            col_all1, col_all2 = st.columns([1, 5])
            with col_all1:
                if st.button("✅ 전체 선택", use_container_width=True):
                    st.session_state.vocab_selected = [True] * len(df)
                    st.rerun()
            with col_all2:
                if st.button("⬜ 전체 해제", use_container_width=True):
                    st.session_state.vocab_selected = [False] * len(df)
                    st.rerun()
            
            # 단어 목록을 체크박스로 표시 (10개씩 행으로)
            selected_words = []
            cols_per_row = 5
            for i in range(0, len(df), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    idx = i + j
                    if idx < len(df):
                        row = df.iloc[idx]
                        checked = col.checkbox(
                            f"{idx+1}. {row['word']} ({row['meaning']})",
                            value=st.session_state.vocab_selected[idx],
                            key=f"vocab_cb_{idx}"
                        )
                        st.session_state.vocab_selected[idx] = checked
                        if checked:
                            selected_words.append(idx)
            
            st.divider()
            
            # 선택된 단어 수 표시
            st.info(f"📌 **{len(selected_words)}개** / {len(df)}개 단어 선택됨")
            
            # 선택된 단어만 데이터프레임으로
            if selected_words:
                df_selected = df.iloc[selected_words].copy()
                df_selected.index = range(1, len(df_selected) + 1)
                df_selected.index.name = "번호"
                
                st.markdown("**📊 선택된 단어 미리보기**")
                st.dataframe(df_selected, use_container_width=True,
                            column_config={
                                "word": "단어",
                                "meaning": "뜻",
                                "synonyms": "유의어",
                                "antonyms": "반의어",
                                "derivatives": "파생어/품사"
                            })
                
                # 엑셀 다운로드
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_selected.to_excel(writer, index=True, sheet_name="단어장")
                excel_data = output.getvalue()
                
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    st.download_button(
                        label=f"📥 선택한 {len(selected_words)}개 엑셀 다운로드",
                        data=excel_data,
                        file_name=f"vocabulary_{datetime.now().strftime('%Y%m%d_%H%M')}_{len(selected_words)}words.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary"
                    )
                with col_dl2:
                    # 전체 엑셀 다운로드
                    output_all = io.BytesIO()
                    with pd.ExcelWriter(output_all, engine='openpyxl') as writer:
                        df.to_excel(writer, index=True, sheet_name="단어장")
                    st.download_button(
                        label="📥 전체 50개 엑셀 다운로드",
                        data=output_all.getvalue(),
                        file_name=f"vocabulary_full_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                st.warning("선택된 단어가 없습니다. 엑셀 다운로드하려면 단어를 선택해주세요.")
        
        elif isinstance(result, dict) and "raw_result" in result:
            st.error(f"JSON 파싱 오류. 원본 응답:")
            st.code(result.get("raw_result", "N/A"))


# ─── 메뉴 3: 시험지 OCR 진단 ──────────────────────────────
elif menu == "🔬 시험지 OCR 진단":
    st.markdown("<div class='main-header'>🔬 시험지 OCR 진단</div>", unsafe_allow_html=True)
    st.markdown("시험지 사진(PNG/JPG)이나 PDF를 업로드하면 AI가 문항별 분석과 취약점을 진단합니다. **여러 파일을 한 번에 업로드**할 수 있고, **주차별로 구분**하여 기록됩니다.")
    
    # 학생 선택
    all_students = get_all_students()
    student_options = {f"{s['name']} ({s['class_name']})": s["id"] for s in all_students}
    
    if not student_options:
        st.warning("등록된 학생이 없습니다.")
    else:
        selected_student_label = st.selectbox("학생 선택", list(student_options.keys()), key="exam_student")
        selected_student_id = student_options[selected_student_label]
        student_info = get_student_by_id(selected_student_id)
        
        # 주차 입력
        week_label = st.text_input(
            "📅 주차 입력 (선택, 예: 3주차, 4월 2주차)",
            value="",
            placeholder="입력 없으면 자동으로 N주차로 저장됩니다",
            key="week_input"
        )
        if not week_label:
            # 자동 주차 계산: DB에 저장된 이 시험지 +1
            existing = get_student_history(selected_student_id)
            exam_count = sum(1 for h in existing if h["category"] == "성적" and "시험지 진단" in h.get("notes", ""))
            week_label = f"{exam_count + 1}주차"
        
        st.caption(f"📌 저장될 주차: **{week_label}**")
        
        # 여러 파일 업로드 (이미지 + PDF)
        uploaded_files = st.file_uploader(
            "📸 시험지 파일 업로드 (여러 개 선택 가능, PNG/JPG/PDF)",
            type=["png", "jpg", "jpeg", "pdf"],
            accept_multiple_files=True,
            key="exam_files"
        )
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)}개 파일 업로드됨")
            
            # 미리보기
            with st.expander("📂 업로드된 파일 미리보기", expanded=False):
                for i, f in enumerate(uploaded_files):
                    if f.type == "application/pdf":
                        st.caption(f"{i+1}. 📄 {f.name}")
                    else:
                        st.image(f, caption=f"{i+1}. {f.name}", width=200)
            
            api_key = st.session_state.get("gemini_key_input", os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")))
            if not api_key:
                st.warning("⚠️ Google Gemini API 키가 필요합니다. 사이드바에서 API 키를 입력해주세요.")
            else:
                if st.button("🔍 AI 시험지 분석 시작", use_container_width=True, type="primary"):
                    with st.spinner(f"🧠 AI가 {len(uploaded_files)}개 파일을 분석 중입니다... (주차: {week_label})"):
                        # 파일 정보 구성
                        files_info = []
                        for f in uploaded_files:
                            if f.type == "application/pdf":
                                files_info.append({"type": "pdf", "bytes": f.getvalue()})
                            else:
                                files_info.append({"type": "image", "bytes": f.getvalue()})
                        
                        result = analyze_exam_multi(api_key, files_info, week_label)
                        
                        if result is None:
                            st.error("API 키가 유효하지 않습니다.")
                        elif isinstance(result, dict) and "error" in result:
                            st.error(f"분석 중 오류: {result['error']}")
                            if "raw_result" in result:
                                st.code(result["raw_result"])
                        else:
                            st.session_state.last_exam_result = result
                            st.session_state.last_exam_week = week_label
                            
                            # student_history에 저장 (주차 포함)
                            weakness = result.get("weakness_analysis", "")
                            prescription = result.get("prescription", "")
                            report_week = result.get("week", week_label)
                            notes = f"[{report_week} 시험지 진단] 총{result.get('total_questions',0)}문항 중 {result.get('correct_count',0)}개 정답. "
                            notes += f"취약점: {weakness[:150]}... " if weakness else ""
                            notes += f"처방: {prescription[:150]}..." if prescription else ""
                            add_student_history(selected_student_id, "성적", notes)
                            
                            st.success(f"✅ {student_info['name']}님의 {report_week} 시험지 분석 완료! 결과가 히스토리에 저장되었습니다.")
                            st.rerun()
        
        # 분석 결과 표시
        if st.session_state.last_exam_result is not None:
            result = st.session_state.last_exam_result
            report_week = result.get("week", st.session_state.get("last_exam_week", ""))
            
            st.divider()
            st.markdown(f"<div class='sub-header'>📊 진단 결과 {f'({report_week})' if report_week else ''}</div>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📝 전체 문항", result.get("total_questions", 0))
            with col2:
                st.metric("✅ 정답", result.get("correct_count", 0))
            with col3:
                st.metric("❌ 오답", result.get("incorrect_count", 0))
            
            # 영역별 정답률 차트
            area_accuracy = result.get("area_accuracy_percent", {})
            if area_accuracy:
                st.markdown("**📈 영역별 정답률**")
                df_area = pd.DataFrame({
                    "영역": list(area_accuracy.keys()),
                    "정답률(%)": [float(v) for v in area_accuracy.values()]
                })
                
                import altair as alt
                chart = alt.Chart(df_area).mark_bar(color="#2E5A8F").encode(
                    x=alt.X("영역", sort=None),
                    y=alt.Y("정답률(%)", scale=alt.Scale(domain=[0, 100])),
                    tooltip=["영역", "정답률(%)"]
                ).properties(height=300)
                st.altair_chart(chart, use_container_width=True)
            
            # 취약점 분석
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("<div class='analysis-box'><strong>🔍 취약점 분석</strong><br><br>" + 
                          result.get("weakness_analysis", "분석 결과 없음") + "</div>", unsafe_allow_html=True)
            with col2:
                st.markdown("<div class='analysis-box' style='background:#E8F5E9; border-color:#A5D6A7;'><strong>💊 학습 처방전</strong><br><br>" + 
                          result.get("prescription", "처방 결과 없음") + "</div>", unsafe_allow_html=True)


# ─── 메뉴 4: 학교별 기출 경향 분석 ─────────────────────────
elif menu == "🏫 학교별 기출 경향":
    st.markdown("<div class='main-header'>🏫 학교별 기출 경향 분석</div>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📤 새 시험지 업로드", "📊 경향 분석 대시보드"])
    
    # 탭 1: 새 시험지 업로드
    with tab1:
        st.markdown("<div class='sub-header'>기출 시험지 업로드 및 분석</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            school_name = st.text_input("🏫 학교명", placeholder="예: 대치중학교")
            grade = st.selectbox("📚 학년", ["중1", "중2", "중3", "고1", "고2", "고3"])
        with col2:
            year = st.text_input("📅 연도", value=str(datetime.now().year))
            semester = st.selectbox("📖 학기", ["1학기", "2학기", "중간고사", "기말고사"])
        
        exam_pdf = st.file_uploader("📄 기출 시험지 PDF 업로드", type=["pdf"], key="exam_pdf_uploader")
        
        if exam_pdf and school_name and grade:
            api_key = st.session_state.get("gemini_key_input", os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")))
            if not api_key:
                st.warning("⚠️ Google Gemini API 키가 필요합니다.")
            else:
                if st.button("🤖 AI 분석 및 저장", use_container_width=True, type="primary"):
                    with st.spinner("📄 PDF 분석 중..."):
                        try:
                            import pdfplumber
                            pdf_text = ""
                            with pdfplumber.open(exam_pdf) as pdf:
                                for page in pdf.pages:
                                    text = page.extract_text()
                                    if text:
                                        pdf_text += text + "\n"
                            
                            if not pdf_text.strip():
                                st.error("PDF에서 텍스트를 추출할 수 없습니다.")
                            else:
                                result = analyze_school_exam_pdf(api_key, pdf_text)
                                if result and "error" not in result:
                                    analysis_json = json.dumps(result.get("analysis", {}), ensure_ascii=False)
                                    ai_report = result.get("key_features", "")
                                    
                                    save_school_exam(school_name, grade, year, semester, analysis_json, ai_report)
                                    st.success(f"✅ {school_name} {grade} {year} {semester} 데이터가 저장되었습니다!")
                                    
                                    # 결과 미리보기
                                    st.markdown("**분석 결과 미리보기**")
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("전체 문항", result.get("total_questions", 0))
                                    with col2:
                                        st.metric("난이도", result.get("difficulty", "중"))
                                    with col3:
                                        analysis = result.get("analysis", {})
                                        if analysis:
                                            top_area = max(analysis, key=analysis.get)
                                            st.metric("최다 출제 영역", f"{top_area} ({analysis[top_area]}%)")
                                    
                                    st.markdown(f"**주요 특징:** {result.get('key_features', '')}")
                                    if result.get("notable_topics"):
                                        st.markdown(f"**주요 토픽:** {', '.join(result['notable_topics'])}")
                                else:
                                    error_msg = result.get("error", "알 수 없는 오류") if result else "API 응답 없음"
                                    st.error(f"분석 실패: {error_msg}")
                        except Exception as e:
                            st.error(f"처리 중 오류: {str(e)}")
        elif exam_pdf and not school_name:
            st.info("학교명을 입력해주세요.")
    
    # 탭 2: 경향 분석 대시보드
    with tab2:
        st.markdown("<div class='sub-header'>📊 학교별 기출 경향 대시보드</div>", unsafe_allow_html=True)
        
        schools = get_distinct_schools()
        if not schools:
            st.info("아직 저장된 시험 데이터가 없습니다. '새 시험지 업로드' 탭에서 데이터를 추가해주세요.")
        else:
            selected_school = st.selectbox("학교 선택", schools, key="school_select")
            
            if selected_school:
                exam_data = get_school_exams(selected_school)
                
                if exam_data:
                    # 데이터 요약
                    st.markdown(f"**📊 {selected_school} - 등록된 시험 데이터: {len(exam_data)}건**")
                    
                    # 데이터프레임 표시
                    df_exams = pd.DataFrame([{
                        "연도": e["year"],
                        "학기": e["semester"],
                        "학년": e["grade"],
                        "분석": e.get("ai_report", "")[:50] + "..." if e.get("ai_report") else ""
                    } for e in exam_data])
                    st.dataframe(df_exams, use_container_width=True, hide_index=True)
                    
                    st.divider()
                    
                    # AI 트렌드 리포트 생성
                    api_key = st.session_state.get("gemini_key_input", os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")))
                    if api_key:
                        if st.button("🤖 AI 트렌드 리포트 생성", use_container_width=True, type="primary"):
                            with st.spinner("🧠 AI가 경향 분석 리포트를 생성 중입니다..."):
                                # 기존 데이터를 분석 가능한 형태로 변환
                                exam_list = []
                                for e in exam_data:
                                    analysis = json.loads(e.get("analysis_json", "{}")) if e.get("analysis_json") else {}
                                    exam_list.append({
                                        "year": e["year"],
                                        "semester": e["semester"],
                                        "grade": e["grade"],
                                        **analysis
                                    })
                                
                                trend_data, report = generate_trend_report(api_key, selected_school, exam_list)
                                
                                if report:
                                    st.session_state.trend_report = report
                                    st.session_state.trend_chart_data = trend_data
                                    st.success("✅ 리포트 생성 완료!")
                                else:
                                    st.error("리포트 생성에 실패했습니다.")
                    
                    # 트렌드 리포트 표시
                    if "trend_report" in st.session_state and st.session_state.trend_report:
                        st.markdown("<div class='sub-header'>📈 학교별 트렌드 분석 리포트</div>", unsafe_allow_html=True)
                        
                        # 트렌드 차트
                        if st.session_state.trend_chart_data:
                            df_trend = pd.DataFrame(st.session_state.trend_chart_data)
                            if not df_trend.empty:
                                df_trend_melted = df_trend.melt(
                                    id_vars=["year", "semester"],
                                    value_vars=["어휘", "문법", "독해", "듣기"],
                                    var_name="영역", value_name="비율(%)"
                                )
                                df_trend_melted["label"] = df_trend_melted["year"] + " " + df_trend_melted["semester"]
                                
                                import altair as alt
                                chart = alt.Chart(df_trend_melted).mark_line(point=True).encode(
                                    x=alt.X("label", sort=None, title="학기"),
                                    y=alt.Y("비율(%)", scale=alt.Scale(domain=[0, 100])),
                                    color=alt.Color("영역", scale=alt.Scale(
                                        domain=["어휘", "문법", "독해", "듣기"],
                                        range=["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A"]
                                    )),
                                    tooltip=["label", "영역", "비율(%)"]
                                ).properties(height=400)
                                st.altair_chart(chart, use_container_width=True)
                        
                        # 리포트 텍스트
                        st.markdown(f"<div class='report-box'>{st.session_state.trend_report}</div>", unsafe_allow_html=True)


# ─── 메뉴 5: 학생 히스토리 & 주간 카톡 발송 ─────────────
elif menu == "📋 학생 히스토리 & 주간 발송":
    st.markdown("<div class='main-header'>📋 학생 히스토리 & 주간 리포트 발송</div>", unsafe_allow_html=True)
    
    all_students = get_all_students()
    student_options = {f"{s['name']} ({s['class_name']})": s["id"] for s in all_students}
    
    if not student_options:
        st.warning("등록된 학생이 없습니다.")
    else:
        selected_label = st.selectbox("👨‍🎓 학생 선택", list(student_options.keys()), key="history_student")
        selected_id = student_options[selected_label]
        student_info = get_student_by_id(selected_id)
        
        if student_info:
            # 학생 기본 정보
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("이름", student_info["name"])
            with col2:
                st.metric("반", student_info["class_name"])
            with col3:
                st.metric("연락처", student_info["phone"])
            with col4:
                st.metric("잔여 횟수", student_info["remaining_sessions"])
            
            st.divider()
            
            # 히스토리 타임라인
            col_left, col_right = st.columns([3, 2])
            
            with col_left:
                st.markdown("<div class='sub-header'>📜 학생 히스토리 타임라인</div>", unsafe_allow_html=True)
                
                history = get_student_history(selected_id)
                if history:
                    for h in history:
                        category_emoji = {"태도": "💪", "성적": "📊", "과제": "📝", "상담": "💬"}
                        emoji = category_emoji.get(h["category"], "📌")
                        date_obj = datetime.strptime(h["date"], "%Y-%m-%d")
                        date_str = date_obj.strftime("%m월 %d일")
                        st.markdown(f"""
                        <div class='timeline-item'>
                            <span style='font-size:0.85rem; color:#888;'>{date_str}</span>
                            <span style='font-size:0.85rem; color:#2E5A8F; font-weight:600;'> [{h['category']}]</span>
                            <br>{h['notes']}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("아직 기록된 히스토리가 없습니다.")
            
            with col_right:
                st.markdown("<div class='sub-header'>✏️ 새 특이사항 기록</div>", unsafe_allow_html=True)
                
                new_category = st.selectbox("카테고리", ["태도", "성적", "과제", "상담"], key="new_cat")
                new_notes = st.text_area("내용", placeholder="특이사항을 입력하세요...", key="new_notes", height=150)
                
                if st.button("💾 저장", use_container_width=True, key="save_history"):
                    if new_notes.strip():
                        add_student_history(selected_id, new_category, new_notes.strip())
                        st.success("✅ 히스토리가 저장되었습니다!")
                        st.rerun()
                    else:
                        st.warning("내용을 입력해주세요.")
            
            st.divider()
            
            # 주간 리포트 섹션
            st.markdown("<div class='sub-header'>📬 주간 리포트 & 알림장</div>", unsafe_allow_html=True)
            
            col_a, col_b = st.columns([1, 1])
            
            with col_a:
                if st.button("📄 이번 주 주간 리포트 생성", use_container_width=True, type="primary", key="gen_report"):
                    with st.spinner("📊 데이터 취합 및 AI 리포트 생성 중..."):
                        # 데이터 취합
                        att_records = get_attendance_record(selected_id, 7)
                        weekly_history = get_weekly_history(selected_id)
                        
                        # 출석률 계산
                        total_days = 5  # 주 5회 기준
                        present_days = sum(1 for r in att_records if r["status"] == "출석")
                        att_rate = round(present_days / total_days * 100, 1) if total_days > 0 else 0
                        
                        api_key = st.session_state.get("gemini_key_input", os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")))
                        if api_key:
                            report = generate_weekly_report(
                                api_key,
                                {"name": student_info["name"], "class": student_info["class_name"]},
                                {"출석률": f"{att_rate}%", "출석일": present_days, "전체": total_days},
                                weekly_history,
                                st.session_state.last_exam_result if st.session_state.last_exam_result else {}
                            )
                            if report:
                                st.session_state.weekly_report = report
                                st.session_state.weekly_report_editable = report
                                st.success("✅ 리포트 생성 완료!")
                                st.rerun()
                            else:
                                # API 키 없으면 기본 리포트 생성
                                fallback_report = f"""📋 {student_info['name']} 학생 주간 학습 리포트

📅 기간: {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} ~ {datetime.now().strftime('%Y-%m-%d')}

📊 출석 현황: {present_days}/{total_days}회 출석 (출석률 {att_rate}%)
"""
                                if weekly_history:
                                    fallback_report += "\n📝 금주 특이사항:\n"
                                    for h in weekly_history:
                                        fallback_report += f"  - [{h['category']}] {h['notes']}\n"
                                
                                fallback_report += "\n🤖 AI 리포트를 생성하려면 Gemini API 키를 설정해주세요."
                                st.session_state.weekly_report = fallback_report
                                st.session_state.weekly_report_editable = fallback_report
                                st.success("✅ 기본 리포트 생성 완료!")
                                st.rerun()
                        else:
                            st.info("Gemini API 키가 없어 기본 리포트를 생성합니다.")
                            fallback_report = f"""📋 {student_info['name']} 학생 주간 학습 리포트

📅 기간: {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} ~ {datetime.now().strftime('%Y-%m-%d')}

📊 출석 현황: {present_days}/{total_days}회 출석 (출석률 {att_rate}%)
"""
                            if weekly_history:
                                fallback_report += "\n📝 금주 특이사항:\n"
                                for h in weekly_history:
                                    fallback_report += f"  - [{h['category']}] {h['notes']}\n"
                            
                            st.session_state.weekly_report = fallback_report
                            st.session_state.weekly_report_editable = fallback_report
                            st.rerun()
            
            with col_b:
                # 부모 연락처 확인
                parent_phone = student_info.get("parent_phone", "")
                if not parent_phone:
                    parent_phone = student_info.get("phone", "")
                st.caption(f"📞 발송 대상: {parent_phone}")
            
            # 리포트 표시 및 편집
            if st.session_state.weekly_report and st.session_state.weekly_report_editable:
                st.divider()
                st.markdown("**✏️ 주간 알림장 (편집 가능)**")
                edited_report = st.text_area(
                    "내용을 직접 수정할 수 있습니다:",
                    value=st.session_state.weekly_report_editable,
                    height=300,
                    key="report_editor"
                )
                st.session_state.weekly_report_editable = edited_report
                
                # 발송 섹션
                st.divider()
                st.markdown("**📤 메시지 발송**")
                
                solapi_key = st.session_state.get("solapi_key_input", os.getenv("SOLAPI_API_KEY", ""))
                solapi_secret = st.session_state.get("solapi_secret_input", os.getenv("SOLAPI_API_SECRET", ""))
                solapi_from = st.session_state.get("solapi_from_input", os.getenv("SOLAPI_FROM_NUMBER", ""))
                
                col_send1, col_send2 = st.columns(2)
                
                with col_send1:
                    if st.button("💬 카카오 알림톡 발송", use_container_width=True, key="send_kakao"):
                        if not parent_phone:
                            st.error("발송할 학부모 연락처가 없습니다.")
                        else:
                            result = send_solapi_message(solapi_key, solapi_secret, parent_phone, solapi_from, edited_report)
                            if result["success"]:
                                st.success(result["message"])
                            else:
                                st.warning(result["message"])
                
                with col_send2:
                    if st.button("📱 SMS 문자 발송", use_container_width=True, key="send_sms"):
                        if not parent_phone:
                            st.error("발송할 학부모 연락처가 없습니다.")
                        else:
                            result = send_solapi_message(solapi_key, solapi_secret, parent_phone, solapi_from, edited_report)
                            if result["success"]:
                                st.success(result["message"])
                            else:
                                st.warning(result["message"])


# ─── 푸터 ──────────────────────────────────────────────────
st.divider()
st.caption("앨리영어 AI 종합 관리 시스템 v1.0 | 대치동 1인 학원 맞춤형 | © 2025")