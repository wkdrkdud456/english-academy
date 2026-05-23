"""
데이터베이스 관리 모듈 - SQLite3 기반
앨리영어 학원 관리 시스템
"""
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "academy.db"

def get_connection():
    """데이터베이스 연결 반환"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """데이터베이스 초기화 및 테이블 생성, 샘플 데이터 적재"""
    if os.path.exists(DB_PATH):
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 테이블 생성
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            day_of_week TEXT NOT NULL,
            time_slot TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            remaining_sessions INTEGER DEFAULT 8,
            parent_phone TEXT DEFAULT '',
            FOREIGN KEY (class_id) REFERENCES classes(id)
        );
        
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('출석','결석','보강')),
            FOREIGN KEY (student_id) REFERENCES students(id)
        );
        
        CREATE TABLE IF NOT EXISTS student_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            category TEXT NOT NULL CHECK(category IN ('태도','성적','과제','상담')),
            notes TEXT DEFAULT '',
            FOREIGN KEY (student_id) REFERENCES students(id)
        );
        
        CREATE TABLE IF NOT EXISTS school_exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_name TEXT NOT NULL,
            grade TEXT NOT NULL,
            year TEXT NOT NULL,
            semester TEXT NOT NULL,
            analysis_json TEXT DEFAULT '',
            ai_report TEXT DEFAULT ''
        );
    """)
    
    # 샘플 데이터: 클래스 2개
    cursor.execute("INSERT INTO classes (name, day_of_week, time_slot) VALUES (?, ?, ?)",
                   ("초등 영어 기초 A", "월/수", "16:00"))
    cursor.execute("INSERT INTO classes (name, day_of_week, time_slot) VALUES (?, ?, ?)",
                   ("중등 영어 심화 B", "화/목", "18:00"))
    
    # 샘플 데이터: 학생 3명
    cursor.execute("INSERT INTO students (class_id, name, phone, remaining_sessions, parent_phone) VALUES (?, ?, ?, ?, ?)",
                   (1, "김민준", "010-1111-1111", 8, "010-1111-0000"))
    cursor.execute("INSERT INTO students (class_id, name, phone, remaining_sessions, parent_phone) VALUES (?, ?, ?, ?, ?)",
                   (1, "이서연", "010-2222-2222", 1, "010-2222-0000"))
    cursor.execute("INSERT INTO students (class_id, name, phone, remaining_sessions, parent_phone) VALUES (?, ?, ?, ?, ?)",
                   (2, "박지호", "010-3333-3333", 0, "010-3333-0000"))
    
    # 샘플 데이터: 출석 기록
    today = datetime.now()
    for i in range(5):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        cursor.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                       (1, d, "출석"))
        cursor.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                       (2, d, "출석"))
        cursor.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                       (3, d, "출석"))
    
    # 샘플 데이터: 학생 히스토리
    cursor.execute("INSERT INTO student_history (student_id, date, category, notes) VALUES (?, ?, ?, ?)",
                   (1, (today - timedelta(days=3)).strftime("%Y-%m-%d"), "태도", "수업 중 집중력이 좋아졌어요. 발표도 잘함."))
    cursor.execute("INSERT INTO student_history (student_id, date, category, notes) VALUES (?, ?, ?, ?)",
                   (2, (today - timedelta(days=2)).strftime("%Y-%m-%d"), "과제", "과제 제출률 100%! 꾸준히 잘 해오고 있음."))
    cursor.execute("INSERT INTO student_history (student_id, date, category, notes) VALUES (?, ?, ?, ?)",
                   (3, (today - timedelta(days=1)).strftime("%Y-%m-%d"), "상담", "학부모 상담 완료. 다음 달부터 주 2회로 확장 예정."))
    
    # 샘플 데이터: 학교별 기출 분석
    cursor.execute("""INSERT INTO school_exams (school_name, grade, year, semester, analysis_json, ai_report)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                   ("대치중학교", "중2", "2025", "1학기",
                    '{"어휘": 25, "문법": 30, "독해": 35, "듣기": 10}',
                    "어휘와 독해 영역의 비중이 높습니다. 문법은 꾸준히 출제되는 편이며, 듣기 비중이 낮은 것이 특징입니다."))
    
    conn.commit()
    conn.close()


# ---------- CRUD 함수들 ----------

def get_all_classes():
    """모든 수업 목록 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_students_by_class(class_id):
    """특정 반의 학생 목록 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE class_id = ? ORDER BY name", (class_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_students():
    """전체 학생 목록"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, c.name AS class_name, c.day_of_week, c.time_slot
        FROM students s
        JOIN classes c ON s.class_id = c.id
        ORDER BY s.name
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_student_by_id(student_id):
    """학생 ID로 상세 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, c.name AS class_name, c.day_of_week, c.time_slot
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.id = ?
    """, (student_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def mark_attendance(student_id, status):
    """출석 체크 및 remaining_sessions 차감"""
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                   (student_id, today, status))
    if status == "출석":
        cursor.execute("UPDATE students SET remaining_sessions = MAX(0, remaining_sessions - 1) WHERE id = ?",
                       (student_id,))
    conn.commit()
    conn.close()

def get_today_attendance(student_id):
    """오늘 출석 여부 확인"""
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT * FROM attendance WHERE student_id = ? AND date = ?",
                   (student_id, today))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_attendance_record(student_id, days=7):
    """특정 학생의 최근 출석 기록"""
    conn = get_connection()
    cursor = conn.cursor()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    cursor.execute("SELECT * FROM attendance WHERE student_id = ? AND date >= ? ORDER BY date DESC",
                   (student_id, since))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_attendance_rate(student_id, days=7):
    """특정 학생의 최근 출석률"""
    records = get_attendance_record(student_id, days)
    if not records:
        return 0.0
    present = sum(1 for r in records if r["status"] == "출석")
    return round(present / len(records) * 100, 1)

def get_low_session_students(threshold=1):
    """잔여 수업 횟수가 적은 학생 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, c.name AS class_name
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.remaining_sessions <= ?
        ORDER BY s.remaining_sessions
    """, (threshold,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_student_history(student_id, category, notes):
    """학생 히스토리 추가"""
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO student_history (student_id, date, category, notes) VALUES (?, ?, ?, ?)",
                   (student_id, today, category, notes))
    conn.commit()
    conn.close()

def get_student_history(student_id):
    """학생 히스토리 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_history WHERE student_id = ? ORDER BY date DESC",
                   (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_weekly_history(student_id):
    """최근 1주일 히스토리 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    cursor.execute("SELECT * FROM student_history WHERE student_id = ? AND date >= ? ORDER BY date DESC",
                   (student_id, since))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_school_exam(school_name, grade, year, semester, analysis_json, ai_report=""):
    """학교 시험 데이터 저장"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO school_exams (school_name, grade, year, semester, analysis_json, ai_report)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (school_name, grade, year, semester, analysis_json, ai_report))
    conn.commit()
    conn.close()

def get_school_exams(school_name=None):
    """학교 시험 데이터 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    if school_name:
        cursor.execute("SELECT * FROM school_exams WHERE school_name = ? ORDER BY year DESC, semester", (school_name,))
    else:
        cursor.execute("SELECT * FROM school_exams ORDER BY school_name, year DESC, semester")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_distinct_schools():
    """중복 없는 학교 목록"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT school_name FROM school_exams ORDER BY school_name")
    rows = cursor.fetchall()
    conn.close()
    return [r["school_name"] for r in rows]