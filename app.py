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
from docx import Document

# 내부 모듈
from db_manager import *
from ai_service import *
from messaging import send_solapi_message, send_message, send_kakao_alimtalk, check_solapi_balance

# ─── 페이지 설정 ─────────────────────────────────────────────
st.set_page_config(
    page_title="대치앨리영어 AI 대시보드",
    page_icon="🎀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── 스타일링 & 기본 테마 설정 ──────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    
    html, body, [data-testid="stSidebar"] {
        font-family: 'Noto Sans KR', sans-serif;
    }
    
    /* 기본 배경색 화이트 강제 */
    .stApp {
        background-color: white !important;
    }

    .main-header { font-size: 2.2rem; font-weight: 700; color: #D81B60; padding: 0.5rem 0; }
    .sub-header { font-size: 1.5rem; font-weight: 600; color: #AD1457; padding: 0.3rem 0; border-bottom: 2px solid #FCE4EC; margin-bottom: 1rem; }
    
    .stButton>button {
        border-radius: 20px;
        transition: all 0.3s;
        font-weight: 600;
        width: 100%;
    }
    
    [data-testid="stSidebar"] {
        background-color: #FFF5F8 !important;
        border-right: 1px solid #FCE4EC;
    }
    
    .info-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 2px 15px rgba(0,0,0,0.05);
        border: 1px solid #FCE4EC;
        margin-bottom: 1rem;
    }

    .report-box {
        background-color: #F9FAFB; border: 2px solid #E5E7EB;
        padding: 1.5rem; border-radius: 10px; margin: 1rem 0;
        white-space: pre-wrap; line-height: 1.8;
    }

    /* 관리 게시판 스타일 */
    .admin-card {
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #eee;
        background: #fafafa;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ─── 세션 상태 초기화 ──────────────────────────────────────
if "db_initialized" not in st.session_state:
    init_database()
    st.session_state.db_initialized = True
if "menu" not in st.session_state:
    st.session_state.menu = "📊 대시보드"
if "last_exam_result" not in st.session_state:
    st.session_state.last_exam_result = None
if "vocab_result" not in st.session_state:
    st.session_state.vocab_result = None
if "ocr_feedback" not in st.session_state:
    st.session_state.ocr_feedback = []

# ─── 상단 로고 & 헤더 ───────────────────────────────
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; padding:1rem; background:white; border-radius:15px; margin-bottom:1.5rem; border:1px solid #FCE4EC;">
    <div style="display:flex; align-items:center; gap:15px;">
        <span style="font-size:2.5rem;">🎀</span>
        <div>
            <div style="font-size:1.8rem; font-weight:800; color:#D81B60; line-height:1.2;">대치앨리영어</div>
            <div style="font-size:0.9rem; color:#888;">For My Beloved Allie</div>
        </div>
    </div>
    <div style="text-align:right;">
        <div style="font-size:0.9rem; color:#666; font-weight:500;">{datetime.now().strftime('%Y년 %m월 %d일')}</div>
        <div style="font-size:0.75rem; color:#AD1457;">오늘도 행복한 하루 되세요 원장님! ✨</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── 사이드바 네비게이션 ───────────────────────────────
with st.sidebar:
    st.markdown("<div style='text-align:center; padding:1rem;'>", unsafe_allow_html=True)
    st.markdown("<span style='font-size:5rem;'>👩‍🏫</span>", unsafe_allow_html=True)
    st.markdown("<h3 style='color:#D81B60; margin:0;'>Menu</h3></div>", unsafe_allow_html=True)
    
    nav_items = {
        "📊 대시보드": "📊 대시보드",
        "⚙️ 학원 관리 게시판": "⚙️ 학원 관리 게시판",
        "📖 교재분석 & 단어장": "📖 교재분석 & 단어장",
        "🔬 시험지 OCR 진단": "🔬 시험지 OCR 진단",
        "🏫 학교별 기출경향": "🏫 학교별 기출경향",
        "📋 히스토리 & 리포트": "📋 히스토리 & 리포트"
    }
    
    for label, val in nav_items.items():
        if st.button(label, use_container_width=True, type="primary" if st.session_state.menu == val else "secondary"):
            st.session_state.menu = val
            st.rerun()

    st.divider()
    
    with st.expander("🔑 API & 시스템 설정"):
        st.text_input("Gemini API Key", value=os.getenv("GEMINI_API_KEY", ""), type="password", key="gemini_key_input")
        st.text_input("Solapi Key", value=os.getenv("SOLAPI_API_KEY", ""), key="solapi_key_input")
        st.text_input("Solapi Secret", value=os.getenv("SOLAPI_API_SECRET", ""), type="password", key="solapi_secret_input")
        st.text_input("발신 번호", value=os.getenv("SOLAPI_FROM_NUMBER", ""), key="solapi_from_input")
        
        if st.button("🔄 시스템 초기화 (주의)", use_container_width=True):
            with st.spinner("DB를 초기화 중입니다..."):
                if os.path.exists("academy.db"): os.remove("academy.db")
                init_database()
            st.toast("✅ 초기화 완료!", icon="🎉")
            st.rerun()

# ─── 메뉴 1: 대시보드 ─────────────────────────
if st.session_state.menu == "📊 대시보드":
    st.markdown("<div class='main-header'>📊 실시간 학원 현황</div>", unsafe_allow_html=True)
    
    low_s = get_low_session_students(1)
    for s in low_s:
        st.warning(f"🔔 **{s['name']}** 학생 수강료 재등록 시점입니다! (잔여 {s['remaining_sessions']}회)")

    all_s = get_all_students()
    all_c = get_all_classes()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 학생수", f"{len(all_s)}명")
    c2.metric("운영 반 수", f"{len(all_c)}개")
    c3.metric("재등록 필요", f"{len(low_s)}명")
    c4.metric("오늘 수업", f"{sum(1 for c in all_c if ['월','화','수','목','금','토','일'][datetime.now().weekday()] in c['day_of_week'])}개")

    st.divider()
    
    st.markdown("<div class='sub-header'>📅 반별 출석 체크 및 충전</div>", unsafe_allow_html=True)
    if all_c:
        sel_c_name = st.selectbox("수업 선택", [c["name"] for c in all_c])
        curr_c = next(c for c in all_c if c["name"] == sel_c_name)
        st.caption(f"📍 {curr_c['day_of_week']} | {curr_c['time_slot']} | {curr_c.get('notes', '')}")
        
        students = get_students_by_class(curr_c["id"])
        if not students:
            st.info("이 반에는 아직 등록된 학생이 없습니다.")
        for s in students:
            cc1, cc2, cc3, cc4 = st.columns([3, 1, 1, 1])
            cc1.markdown(f"**{s['name']}** ({s['school_name'] or '미지정'}) - 잔여 {s['remaining_sessions']}회")
            
            # 출석 버튼
            att = get_today_attendance(s["id"])
            if att: 
                cc2.success(f"{att['status']}")
            else:
                if cc2.button("✅ 출석", key=f"att_{s['id']}"):
                    with st.spinner("출석 처리 중..."):
                        mark_attendance(s["id"], "출석")
                    st.toast(f"✅ {s['name']} 출석 완료!", icon="🌸")
                    st.rerun()
                if cc3.button("❌ 결석", key=f"abs_{s['id']}"):
                    with st.spinner("결석 처리 중..."):
                        mark_attendance(s["id"], "결석")
                    st.toast(f"❌ {s['name']} 결석 처리됨", icon="📍")
                    st.rerun()
            
            # 충전 버튼
            if cc4.button("➕8회 충전", key=f"rec_{s['id']}"):
                with st.spinner("충전 중..."):
                    recharge_sessions(s["id"], 8)
                st.toast(f"💰 {s['name']} 학생 8회 충전 완료!", icon="💳")
                st.rerun()
    else:
        st.info("관리 게시판에서 먼저 반을 등록해주세요.")

# ─── 메뉴: 학원 관리 게시판 ──────────────────────
elif st.session_state.menu == "⚙️ 학원 관리 게시판":
    st.markdown("<div class='main-header'>⚙️ 학원 관리 게시판</div>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["👥 학생 관리", "📚 반 관리", "🏫 학교 관리"])
    
    with tab1:
        st.markdown("<div class='sub-header'>학생 명단 및 수정</div>", unsafe_allow_html=True)
        all_s = get_all_students()
        all_c = get_all_classes()
        all_sch = get_all_schools()
        
        col_list, col_add = st.columns([2, 1])
        
        with col_list:
            for s in all_s:
                with st.container():
                    st.markdown(f"""
                    <div class="admin-card">
                        <b>{s['name']}</b> | {s['school_name'] or '학교미지정'} | {s['class_name']}<br>
                        <small>연락처: {s['phone']} | 잔여: {s['remaining_sessions']}회</small>
                    </div>
                    """, unsafe_allow_html=True)
                    c_del_col, _ = st.columns([1, 4])
                    if c_del_col.button("삭제", key=f"del_s_{s['id']}"):
                        with st.spinner("학생 정보 삭제 중..."):
                            delete_student(s["id"])
                        st.toast(f"🗑️ {s['name']} 삭제됨")
                        st.rerun()
        
        with col_add:
            st.markdown("**➕ 학생 추가**")
            r_name = st.text_input("이름", key="add_s_name")
            r_phone = st.text_input("연락처", key="add_s_phone")
            r_class = st.selectbox("반", [c["name"] for c in all_c], key="add_s_class")
            r_school = st.selectbox("학교", [s["name"] for s in all_sch], key="add_s_school")
            r_sessions = st.number_input("초기 잔여 횟수", min_value=0, value=8)
            if st.button("학생 등록", type="primary"):
                if r_name and r_phone:
                    with st.spinner("학생 정보를 등록 중입니다..."):
                        cid = next(c["id"] for c in all_c if c["name"] == r_class)
                        sid = next(s["id"] for s in all_sch if s["name"] == r_school)
                        add_student(cid, r_name, r_phone, r_sessions, "", sid)
                    st.toast("✅ 등록되었습니다!", icon="🎀")
                    st.rerun()

    with tab2:
        st.markdown("<div class='sub-header'>운영 반 목록</div>", unsafe_allow_html=True)
        all_c = get_all_classes()
        col_c_list, col_c_add = st.columns([2, 1])
        
        with col_c_list:
            for c in all_c:
                st.markdown(f"""
                <div class="admin-card">
                    <b>{c['name']}</b> ({c['day_of_week']})<br>
                    <small>시간: {c['time_slot']} | 비고: {c.get('notes', '')}</small>
                </div>
                """, unsafe_allow_html=True)
                if st.button("삭제", key=f"del_c_{c['id']}"):
                    with st.spinner("반 삭제 중..."):
                        delete_class(c["id"])
                    st.rerun()
        
        with col_c_add:
            st.markdown("**➕ 새 반 만들기**")
            bc_name = st.text_input("반 이름", key="add_c_name")
            bc_day = st.multiselect("요일", ["월", "화", "수", "목", "금", "토", "일"], key="add_c_day")
            
            # 오전/오후 형식 시간 선택
            hours = [f"오전 {i}시" for i in range(1, 13)] + [f"오후 {i}시" for i in range(1, 13)]
            mins = [f"{i:02d}분" for i in range(0, 60, 5)]
            c_time_h = st.selectbox("시간", hours, index=14) # 오후 2시 기본
            c_time_m = st.selectbox("분", mins, index=0)
            bc_time_str = f"{c_time_h} {c_time_m}"
            
            bc_notes = st.text_area("참고사항", key="add_c_notes")
            if st.button("반 등록", type="primary"):
                if bc_name and bc_day:
                    with st.spinner("반을 생성 중입니다..."):
                        add_class(bc_name, "/".join(bc_day), bc_time_str, bc_notes)
                    st.toast("✅ 생성 완료!", icon="📚")
                    st.rerun()

    with tab3:
        st.markdown("<div class='sub-header'>학교 목록</div>", unsafe_allow_html=True)
        all_sch = get_all_schools()
        col_sch_list, col_sch_add = st.columns([2, 1])
        
        with col_sch_list:
            for sch in all_sch:
                sc1, sc2 = st.columns([4, 1])
                sc1.write(f"🏫 {sch['name']}")
                if sc2.button("🗑️", key=f"del_sch_board_{sch['id']}"):
                    delete_school(sch["id"])
                    st.rerun()
        
        with col_sch_add:
            st.markdown("**➕ 학교 추가**")
            new_s_name = st.text_input("학교명", key="add_sch_name")
            if st.button("학교 등록", type="primary"):
                if new_s_name:
                    with st.spinner("학교 추가 중..."):
                        add_school(new_s_name)
                    st.rerun()

# ─── 메뉴 2: 교재 분석 ──────────────────────
elif st.session_state.menu == "📖 교재분석 & 단어장":
    st.markdown("<div class='main-header'>📖 교재 분석 & 단어장 생성</div>", unsafe_allow_html=True)
    file = st.file_uploader("교재 업로드 (PDF/PNG/JPG)", type=["pdf", "png", "jpg", "jpeg"])
    if file:
        if st.button("🤖 AI 50개 핵심 단어 추출", type="primary", use_container_width=True):
            with st.spinner("AI가 교재 내용을 정독하며 핵심 단어를 엄선하고 있습니다... (약 1분 소요)"):
                api_key = st.session_state.gemini_key_input
                if file.name.lower().endswith('.pdf'):
                    text, _ = process_pdf_with_ocr(api_key, file.getvalue())
                else:
                    text, _ = extract_text_from_image(api_key, file.getvalue())
                
                if text:
                    st.session_state.vocab_result = extract_vocabulary(api_key, text)
                    st.toast("✅ 분석이 완료되었습니다!", icon="✨")
                    st.rerun()
                else:
                    st.error("텍스트를 추출할 수 없습니다.")

    if st.session_state.vocab_result:
        df = pd.DataFrame(st.session_state.vocab_result)
        st.markdown("<div class='sub-header'>📋 단어 선택 및 다운로드</div>", unsafe_allow_html=True)
        
        selected = []
        for i, row in df.iterrows():
            c1, c2 = st.columns([1, 9])
            if c1.checkbox(f"{i+1}", key=f"v_{i}", value=True): selected.append(i)
            c2.markdown(f"**{row['word']}** ({row['meaning']})")
        
        if st.button("📥 선택한 단어 파일(워드/엑셀) 생성", use_container_width=True):
            with st.spinner("파일을 생성 중입니다..."):
                sel_df = df.iloc[selected]
                # Excel
                output_ex = io.BytesIO()
                with pd.ExcelWriter(output_ex, engine='openpyxl') as writer:
                    sel_df.to_excel(writer, index=False)
                # Word
                doc = Document()
                doc.add_heading('🎀 대치앨리영어 단어장', 0)
                table = doc.add_table(rows=1, cols=3); table.style = 'Table Grid'
                for h in ['단어', '뜻', '파생어']: table.rows[0].cells[['단어', '뜻', '파생어'].index(h)].text = h
                for _, r in sel_df.iterrows():
                    cells = table.add_row().cells
                    cells[0].text, cells[1].text, cells[2].text = str(r['word']), str(r['meaning']), str(r['derivatives'])
                output_wd = io.BytesIO(); doc.save(output_wd)
            
            st.success("✅ 파일 생성 완료! 아래 버튼을 눌러 저장하세요.")
            st.download_button("📂 Excel 다운로드", output_ex.getvalue(), "앨리단어장.xlsx")
            st.download_button("📂 Word 다운로드", output_wd.getvalue(), "앨리단어장.docx")

# ─── 메뉴 3: 시험지 OCR ──────────────────────
elif st.session_state.menu == "🔬 시험지 OCR 진단":
    st.markdown("<div class='main-header'>🔬 시험지 OCR 진단 및 채점</div>", unsafe_allow_html=True)
    
    all_s = get_all_students()
    if not all_s:
        st.info("게시판에서 학생을 먼저 등록해주세요.")
    else:
        c1, c2 = st.columns(2)
        student_map = {f"{s['name']} ({s['school_name'] or '미지정'})": s for s in all_s}
        sel_s = c1.selectbox("채점 대상 학생", list(student_map.keys()))
        week = c2.selectbox("해당 주차", [f"{i}주차" for i in range(1, 21)])
        
        files = st.file_uploader("시험지 업로드 (이미지/PDF 다중 가능)", accept_multiple_files=True, type=["pdf", "png", "jpg", "jpeg"])
        if files:
            with st.expander("📂 업로드된 파일 미리보기"):
                for f in files:
                    if f.name.lower().endswith(('.png', '.jpg', '.jpeg')): st.image(f, width=400)
                    else: st.caption(f"📄 {f.name}")
            
            if st.button("🔍 AI 자동 채점 시작", type="primary", use_container_width=True):
                with st.spinner("AI가 시험지를 분석하고 정답을 체크 중입니다..."):
                    api_key = st.session_state.gemini_key_input
                    f_info = [{"type": "pdf" if f.name.lower().endswith(".pdf") else "image", "bytes": f.getvalue()} for f in files]
                    st.session_state.last_exam_result = analyze_exam_multi(api_key, f_info, week)
                st.toast("✅ 채점 완료! 결과를 확인하고 수정하세요.", icon="✅")

        if st.session_state.last_exam_result:
            res = st.session_state.last_exam_result
            st.markdown("<div class='sub-header'>✅ 정답 여부 검토 및 수정</div>", unsafe_allow_html=True)
            
            total_q = res.get('total_questions', 0)
            new_feedback = []
            if total_q > 0:
                cols = st.columns(min(total_q, 5) if total_q > 0 else 1)
                for i in range(total_q):
                    with cols[i % len(cols)]:
                        new_val = st.toggle(f"Q{i+1}", value=True, key=f"ox_fix_{i}")
                        new_feedback.append(new_val)
            
            correct = sum(new_feedback)
            res['correct_count'] = correct
            res['incorrect_count'] = total_q - correct
            
            st.divider()
            st.markdown(f"### 📈 {sel_s} - {week} 분석 리포트")
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("정답 문항", f"{correct} / {total_q}")
            cc2.metric("정답률", f"{int(correct/total_q*100) if total_q>0 else 0}%")
            
            if res.get('area_accuracy_percent'):
                area_df = pd.DataFrame([{"영역": k, "정답률": v} for k, v in res['area_accuracy_percent'].items()])
                st.bar_chart(area_df.set_index("영역"), height=250)
            
            st.info(f"**AI 피드백**: {res.get('weakness_analysis', '')}")
            
            if st.button("💾 이 결과를 학생 히스토리에 최종 저장", type="primary", use_container_width=True):
                with st.spinner("저장 중..."):
                    s_obj = student_map[sel_s]
                    notes = f"[{week} 시험] {correct}/{total_q} 정답. {res.get('weakness_analysis', '')}"
                    add_student_history(s_obj["id"], "성적", notes, week)
                st.toast("✅ 히스토리에 저장되었습니다!", icon="💾")

# ─── 메뉴 4: 학교별 기출경향 ──────────────────────
elif st.session_state.menu == "🏫 학교별 기출경향":
    st.markdown("<div class='main-header'>🏫 학교별 내신 분석 및 트렌드</div>", unsafe_allow_html=True)
    
    tab_view, tab_upload = st.tabs(["📊 분석 대시보드", "📤 기출 데이터 업로드"])
    
    with tab_upload:
        st.markdown("**신규 기출문제 등록**")
        sch_name = st.selectbox("학교 선택", [s["name"] for s in get_all_schools()], key="exam_sch")
        col_y, col_s, col_g = st.columns(3)
        exam_y = col_y.text_input("연도", value="2024")
        exam_s = col_s.selectbox("학기", ["1학기 중간", "1학기 기말", "2학기 중간", "2학기 기말"])
        exam_g = col_g.selectbox("학년", ["중1", "중2", "중3", "고1", "고2", "고3"])
        
        exam_file = st.file_uploader("기출 파일 업로드 (PDF/이미지)", type=["pdf", "png", "jpg", "jpeg"], key="exam_file_up")
        if exam_file and st.button("🤖 AI 기출 분석 및 저장", use_container_width=True, type="primary"):
            with st.spinner("AI가 기출 유형을 정밀 분석 중입니다..."):
                api_key = st.session_state.gemini_key_input
                if exam_file.name.lower().endswith('.pdf'):
                    text, _ = process_pdf_with_ocr(api_key, exam_file.getvalue())
                else:
                    text, _ = extract_text_from_image(api_key, exam_file.getvalue())
                
                res = analyze_school_exam_pdf(api_key, text)
                if res:
                    save_school_exam(sch_name, exam_g, exam_y, exam_s, json.dumps(res.get('analysis', {})), res.get('key_features', ''))
            st.toast(f"✅ {sch_name} 분석 완료!", icon="🏫")

    with tab_view:
        sch_list = get_distinct_schools_from_exams()
        if sch_list:
            sel_sch = st.selectbox("학교별 리포트 조회", sch_list)
            exams = get_school_exams(sel_sch)
            
            st.markdown(f"### 📈 {sel_sch} 전용 대시보드")
            for e in exams:
                with st.expander(f"📄 {e['year']} {e['semester']} ({e['grade']})"):
                    st.write(e['ai_report'])
                    st.json(e['analysis_json'])
        else:
            st.info("먼저 기출 파일을 업로드하여 분석을 진행해주세요.")

# ─── 메뉴 5: 히스토리 ──────────────────────
elif st.session_state.menu == "📋 히스토리 & 리포트":
    st.markdown("<div class='main-header'>📋 학생 히스토리 및 주간 리포트</div>", unsafe_allow_html=True)
    all_s = get_all_students()
    if all_s:
        student_names = {f"{s['name']} ({s['school_name'] or '미지정'})": s for s in all_s}
        sel_name = st.selectbox("학생 선택", list(student_names.keys()), key="hist_sel_s")
        s_obj = student_names[sel_name]
        
        col_h1, col_h2 = st.columns([2, 1])
        
        with col_h1:
            st.markdown("<div class='sub-header'>📅 주간 리포트 생성 (월~일 기준)</div>", unsafe_allow_html=True)
            curr_week_start = datetime.now() - timedelta(days=datetime.now().weekday())
            s_date = st.date_input("시작일", value=curr_week_start)
            e_date = st.date_input("종료일", value=s_date + timedelta(days=6))
            
            if st.button("📄 AI 리포트 초안 생성", type="primary", use_container_width=True):
                with st.spinner("일주일간의 데이터를 취합하여 리포트를 작성 중입니다..."):
                    api_key = st.session_state.gemini_key_input
                    hist = get_weekly_history(s_obj["id"], s_date.strftime("%Y-%m-%d"), e_date.strftime("%Y-%m-%d"))
                    report = generate_weekly_report(api_key, s_obj, [], hist, {})
                    st.session_state.weekly_report_editable = report
                st.toast("✅ 리포트가 생성되었습니다!", icon="📝")

            if st.session_state.get("weekly_report_editable"):
                final = st.text_area("내용 수정 및 발송", value=st.session_state.weekly_report_editable, height=300)
                if st.button("💬 카톡/문자 발송", use_container_width=True):
                    with st.spinner("메시지를 발송 중입니다..."):
                        sol_key = st.session_state.get("solapi_key_input")
                        sol_sec = st.session_state.get("solapi_secret_input")
                        sol_from = st.session_state.get("solapi_from_input")
                        res = send_message(sol_key, sol_sec, s_obj["parent_phone"] or s_obj["phone"], sol_from, final)
                    st.success(res["message"])
        
        with col_h2:
            st.markdown("<div class='sub-header'>📜 전체 기록</div>", unsafe_allow_html=True)
            histories = get_student_history(s_obj["id"])
            for h in histories:
                st.caption(f"{h['date']} [{h['category']}]")
                st.write(h['notes'])
                st.divider()
    else:
        st.info("등록된 학생이 없습니다.")

st.markdown("<br><br><div style='text-align:center; color:#AD1457; font-size:0.8rem;'>© 2025 대치앨리영어 | Made with ❤️ for Allie</div>", unsafe_allow_html=True)
