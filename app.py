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

# ─── 스타일링 ────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    
    html, body, [data-testid="stSidebar"] {
        font-family: 'Noto Sans KR', sans-serif;
    }
    
    .main-header { font-size: 2.2rem; font-weight: 700; color: #D81B60; padding: 0.5rem 0; }
    .sub-header { font-size: 1.5rem; font-weight: 600; color: #AD1457; padding: 0.3rem 0; border-bottom: 2px solid #FCE4EC; margin-bottom: 1rem; }
    
    .stButton>button {
        border-radius: 20px;
        transition: all 0.3s;
        font-weight: 600;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(216, 27, 96, 0.2);
    }
    
    [data-testid="stSidebar"] {
        background-color: #FFF5F8;
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
        <div style="font-size:0.75rem; color:#AD1457;">오늘도 화이팅하세요 원장님! ✨</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── 사이드바 네비게이션 ───────────────────────────────
with st.sidebar:
    st.markdown("<div style='text-align:center; padding:1rem;'>", unsafe_allow_html=True)
    st.image("https://img.icons8.com/bubbles/100/000000/woman-profile.png", width=80)
    st.markdown("<h3 style='color:#D81B60; margin:0;'>안녕하세요!</h3></div>", unsafe_allow_html=True)
    
    nav_menus = ["📊 대시보드", "📖 교재분석 & 단어장", "🔬 시험지 OCR 진단", "🏫 학교별 기출경향", "📋 히스토리 & 리포트"]
    for m in nav_menus:
        if st.button(m, use_container_width=True, type="primary" if st.session_state.menu == m else "secondary"):
            st.session_state.menu = m
            st.rerun()

    st.divider()
    
    with st.expander("⚙️ 설정 및 관리"):
        st.markdown("**🏫 학교 목록 관리**")
        all_schools = get_all_schools()
        for sch in all_schools:
            c1, c2 = st.columns([4, 1])
            c1.caption(sch["name"])
            if c2.button("🗑️", key=f"del_sch_{sch['id']}"):
                delete_school(sch["id"])
                st.rerun()
        
        new_sch = st.text_input("새 학교 추가")
        if st.button("➕ 추가", use_container_width=True):
            if new_sch: add_school(new_sch); st.rerun()
        
        st.divider()
        st.markdown("**🔑 API 설정**")
        st.text_input("Gemini API Key", value="AIzaSyD09hiLSytx9ssdYxphAvMWJ8JZChTpdaI", type="password", key="gemini_key_input")
        st.text_input("Solapi Key", key="solapi_key_input")
        st.text_input("Solapi Secret", type="password", key="solapi_secret_input")
        st.text_input("발신 번호", key="solapi_from_input")
        
        if st.button("🔄 DB 초기화", use_container_width=True):
            if os.path.exists("academy.db"): os.remove("academy.db")
            init_database(); st.rerun()

# ─── 메뉴 1: 대시보드 ─────────────────────────
if st.session_state.menu == "📊 대시보드":
    st.markdown("<div class='main-header'>📊 학원 관리 대시보드</div>", unsafe_allow_html=True)
    
    # 알림
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
    col_l, col_r = st.columns([2, 1])
    
    with col_l:
        st.markdown("<div class='sub-header'>📅 반별 출석 체크</div>", unsafe_allow_html=True)
        if all_c:
            sel_c_name = st.selectbox("수업 선택", [c["name"] for c in all_c])
            curr_c = next(c for c in all_c if c["name"] == sel_c_name)
            st.caption(f"📍 {curr_c['day_of_week']} | {curr_c['time_slot']} | {curr_c.get('notes', '')}")
            
            students = get_students_by_class(curr_c["id"])
            for s in students:
                cc1, cc2, cc3 = st.columns([3, 1, 1])
                cc1.markdown(f"**{s['name']}** ({s['school_name'] or '미지정'}) - 잔여 {s['remaining_sessions']}회")
                att = get_today_attendance(s["id"])
                if att: cc2.success(f"{att['status']}")
                else:
                    if cc2.button("✅ 출석", key=f"att_{s['id']}"): mark_attendance(s["id"], "출석"); st.rerun()
                    if cc3.button("❌ 결석", key=f"abs_{s['id']}"): mark_attendance(s["id"], "결석"); st.rerun()
        else:
            st.info("먼저 반을 등록해주세요.")

    with col_r:
        st.markdown("<div class='sub-header'>👤 통합 관리</div>", unsafe_allow_html=True)
        with st.expander("➕ 학생 등록", expanded=False):
            r_name = st.text_input("이름")
            r_phone = st.text_input("연락처")
            r_class = st.selectbox("반 선택", [c["name"] for c in all_c], key="reg_c")
            r_school = st.selectbox("학교 선택", [s["name"] for s in all_schools], key="reg_s")
            if st.button("등록", use_container_width=True):
                cid = next(c["id"] for c in all_c if c["name"] == r_class)
                sid = next(s["id"] for s in all_schools if s["name"] == r_school)
                add_student(cid, r_name, r_phone, 8, "", sid); st.rerun()
        
        with st.expander("📋 반 등록", expanded=False):
            bc_name = st.text_input("반 이름")
            bc_day = st.multiselect("요일", ["월", "화", "수", "목", "금", "토", "일"])
            bc_time = st.time_input("시간")
            bc_notes = st.text_area("비고")
            if st.button("반 생성", use_container_width=True):
                add_class(bc_name, "/".join(bc_day), bc_time.strftime("%H:%M"), bc_notes); st.rerun()

# ─── 메뉴 2: 교재 분석 ──────────────────────
elif st.session_state.menu == "📖 교재분석 & 단어장":
    st.markdown("<div class='main-header'>📖 교재 분석 & 단어장 생성</div>", unsafe_allow_html=True)
    file = st.file_uploader("교재 PDF 업로드", type=["pdf"])
    if file:
        if st.button("🤖 AI 단어 추출 (50개)", type="primary", use_container_width=True):
            with st.spinner("AI가 교재를 정독하고 있습니다..."):
                api_key = st.session_state.gemini_key_input
                text, _ = process_pdf_with_ocr(api_key, file.getvalue())
                st.session_state.vocab_result = extract_vocabulary(api_key, text)
                st.rerun()

    if st.session_state.vocab_result:
        df = pd.DataFrame(st.session_state.vocab_result)
        st.markdown("<div class='sub-header'>📋 단어 선택 및 다운로드</div>", unsafe_allow_html=True)
        
        selected = []
        for i, row in df.iterrows():
            c1, c2 = st.columns([1, 9])
            if c1.checkbox(f"{i+1}", key=f"v_{i}", value=True): selected.append(i)
            c2.markdown(f"**{row['word']}** ({row['meaning']})")
        
        if st.button("📥 선택한 단어 파일로 받기"):
            sel_df = df.iloc[selected]
            # Word Doc
            doc = Document()
            doc.add_heading('🎀 대치앨리영어 단어장', 0)
            table = doc.add_table(rows=1, cols=3)
            table.style = 'Table Grid'
            for h in ['단어', '뜻', '파생어']: table.rows[0].cells[['단어', '뜻', '파생어'].index(h)].text = h
            for _, r in sel_df.iterrows():
                cells = table.add_row().cells
                cells[0].text, cells[1].text, cells[2].text = str(r['word']), str(r['meaning']), str(r['derivatives'])
            buf = io.BytesIO(); doc.save(buf)
            st.download_button("Word 다운로드", buf.getvalue(), "voca.docx")

# ─── 메뉴 3: 시험지 OCR ──────────────────────
elif st.session_state.menu == "🔬 시험지 OCR 진단":
    st.markdown("<div class='main-header'>🔬 시험지 OCR 분석</div>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    student_map = {f"{s['name']} ({s['school_name']})": s for s in get_all_students()}
    sel_s = c1.selectbox("학생 선택", list(student_map.keys()))
    week = c2.selectbox("주차 선택", [f"{i}주차" for i in range(1, 21)])
    
    files = st.file_uploader("시험지 이미지/PDF 업로드", accept_multiple_files=True)
    
    if files:
        with st.expander("📂 업로드된 파일 확인", expanded=True):
            for f in files:
                if not f.name.endswith(".pdf"): st.image(f, width=300)
                else: st.caption(f"📄 {f.name}")
        
        if st.button("🔍 AI 분석 시작", type="primary"):
            api_key = st.session_state.gemini_key_input
            f_info = [{"type": "pdf" if f.name.endswith(".pdf") else "image", "bytes": f.getvalue()} for f in files]
            with st.spinner("AI가 채점 중입니다..."):
                st.session_state.last_exam_result = analyze_exam_multi(api_key, f_info, week)
                # 초기 OX 피드백 생성
                st.session_state.ocr_feedback = [{"q": f"문항 {i+1}", "ox": True} for i in range(st.session_state.last_exam_result.get('total_questions', 0))]

    if st.session_state.last_exam_result:
        res = st.session_state.last_exam_result
        st.markdown("<div class='sub-header'>✅ 정답 여부 수정 (O/X 선택 가능)</div>", unsafe_allow_html=True)
        
        # OX 수정 인터페이스
        new_feedback = []
        cols = st.columns(5)
        for i in range(res['total_questions']):
            with cols[i % 5]:
                val = st.toggle(f"Q{i+1}", value=True, key=f"ox_{i}")
                new_feedback.append(val)
        
        # 수정된 데이터로 리포트 갱신
        correct = sum(new_feedback)
        res['correct_count'] = correct
        res['incorrect_count'] = res['total_questions'] - correct
        
        st.divider()
        st.markdown(f"### 📈 {sel_s} - {week} 최종 리포트")
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("최종 정답", f"{res['correct_count']} / {res['total_questions']}")
        
        area_df = pd.DataFrame([{"영역": k, "정답률": v} for k, v in res['area_accuracy_percent'].items()])
        st.bar_chart(area_df.set_index("영역"), height=200)
        
        st.info(f"**AI 진단**: {res['weakness_analysis']}")
        if st.button("💾 히스토리 최종 저장"):
            s_obj = student_map[sel_s]
            notes = f"[{week} 시험] 정답률 {res['correct_count']}/{res['total_questions']}. {res['weakness_analysis']}"
            add_student_history(s_obj["id"], "성적", notes, week)
            st.success("저장 완료!")

# ─── 메뉴 4: 학교별 기출 ──────────────────────
elif st.session_state.menu == "🏫 학교별 기출경향":
    st.markdown("<div class='main-header'>🏫 학교별 내신 대쉬보드</div>", unsafe_allow_html=True)
    schs = get_distinct_schools_from_exams()
    if schs:
        sel_sch = st.selectbox("학교 선택", schs)
        exams = get_school_exams(sel_sch)
        
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown(f"<div class='info-card'><h4>{sel_sch} 출제 경향</h4>", unsafe_allow_html=True)
            for e in exams:
                st.write(f"📅 **{e['year']} {e['semester']}** : {e['ai_report']}")
            st.markdown("</div>", unsafe_allow_html=True)
        with c2:
            st.markdown("<div class='info-card'><h4>영역별 비중 변화</h4>", unsafe_allow_html=True)
            # 여기에는 연도별 차트 등을 시각화 가능
            st.caption("누적된 데이터를 기반으로 트렌드가 표시됩니다.")
            st.markdown("</div>", unsafe_allow_html=True)

# ─── 메뉴 5: 히스토리 ──────────────────────
elif st.session_state.menu == "📋 히스토리 & 리포트":
    st.markdown("<div class='main-header'>📋 학생 히스토리 & 주간 리포트</div>", unsafe_allow_html=True)
    all_s = get_all_students()
    if all_s:
        student_names = {f"{s['name']} ({s['school_name']})": s for s in all_s}
        sel_name = st.selectbox("학생 선택", list(student_names.keys()))
        s_obj = student_names[sel_name]
        
        st.markdown("### 📅 주간 리포트 생성 (월~일 기준)")
        curr_week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        s_date = st.date_input("시작일", value=curr_week_start)
        e_date = st.date_input("종료일", value=s_date + timedelta(days=6))
        
        if st.button("📄 리포트 초안 AI 생성"):
            api_key = st.session_state.gemini_key_input
            hist = get_weekly_history(s_obj["id"], s_date.strftime("%Y-%m-%d"), e_date.strftime("%Y-%m-%d"))
            report = generate_weekly_report(api_key, s_obj, [], hist, {})
            st.session_state.weekly_report_editable = report

        if st.session_state.get("weekly_report_editable"):
            final = st.text_area("내용 수정", value=st.session_state.weekly_report_editable, height=300)
            if st.button("💬 카톡/문자 발송"):
                sol_key = st.session_state.get("solapi_key_input")
                sol_sec = st.session_state.get("solapi_secret_input")
                sol_from = st.session_state.get("solapi_from_input")
                res = send_message(sol_key, sol_sec, s_obj["parent_phone"] or s_obj["phone"], sol_from, final)
                st.write(res["message"])

st.markdown("<br><br><div style='text-align:center; color:#AD1457; font-size:0.8rem;'>© 2025 대치앨리영어 | Made with ❤️ for Allie</div>", unsafe_allow_html=True)
