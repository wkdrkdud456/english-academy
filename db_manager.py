"""
데이터베이스 관리 모듈 - SQLite3 기반
대치앨리영어 학원 관리 시스템
"""
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "academy.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. 기초 테이블 생성
    cursor.execute("CREATE TABLE IF NOT EXISTS schools (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            day_of_week TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            notes TEXT DEFAULT ''
        )
    """)

    # 2. students 테이블 마이그레이션
    cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='students'")
    if cursor.fetchone()[0] > 0:
        cursor.execute("PRAGMA table_info(students)")
        cols = [c[1] for c in cursor.fetchall()]
        if 'school_id' not in cols:
            cursor.execute("ALTER TABLE students ADD COLUMN school_id INTEGER")
        if 'parent_phone' not in cols:
            cursor.execute("ALTER TABLE students ADD COLUMN parent_phone TEXT DEFAULT ''")
    else:
        cursor.execute("""
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                remaining_sessions INTEGER DEFAULT 8,
                parent_phone TEXT DEFAULT '',
                school_id INTEGER,
                next_payment_date TEXT DEFAULT '',
                FOREIGN KEY (class_id) REFERENCES classes(id),
                FOREIGN KEY (school_id) REFERENCES schools(id)
            )
        """)

    # 3. 출석 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    # 4. 성적 기록 테이블 (4대 영역별)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            listening INTEGER DEFAULT 0,
            vocabulary INTEGER DEFAULT 0,
            grammar INTEGER DEFAULT 0,
            reading INTEGER DEFAULT 0,
            test_name TEXT DEFAULT '',
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    # 5. 히스토리 & 리포트
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            notes TEXT DEFAULT '',
            week_label TEXT DEFAULT '',
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    # 6. 학교 시험지/기출 분석
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS school_exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_name TEXT NOT NULL,
            grade TEXT NOT NULL,
            year TEXT NOT NULL,
            semester TEXT NOT NULL,
            analysis_json TEXT DEFAULT '',
            ai_report TEXT DEFAULT ''
        )
    """)
    
    # 7. 🔥 NEW: 결제/횟수 관리 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            type TEXT NOT NULL,  -- 'charge' (충전), 'deduct' (차감), 'payment' (결제)
            amount INTEGER NOT NULL,  -- +8 (충전), -1 (차감)
            balance_after INTEGER NOT NULL,  -- 거래 후 잔여횟수
            note TEXT DEFAULT '',
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    # 8. 반별 영역 설정 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS class_areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            area_name TEXT NOT NULL,
            FOREIGN KEY (class_id) REFERENCES classes(id)
        )
    """)

    # 9. student_scores 마이그레이션 (score_details 컬럼)
    cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='student_scores'")
    if cursor.fetchone()[0] > 0:
        cursor.execute("PRAGMA table_info(student_scores)")
        score_cols = [c[1] for c in cursor.fetchall()]
        if 'score_details' not in score_cols:
            cursor.execute("ALTER TABLE student_scores ADD COLUMN score_details TEXT DEFAULT ''")

    schools_list = ["대치중학교", "대청중학교", "단대부중", "숙명여중", "역삼중학교"]
    for sname in schools_list:
        cursor.execute("INSERT OR IGNORE INTO schools (name) VALUES (?)", (sname,))

    conn.commit()
    conn.close()

# ========== 통계 ==========
def get_dashboard_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM students")
    total_students = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM classes")
    total_classes = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM schools")
    total_schools = cursor.fetchone()['cnt']
    cursor.execute("SELECT SUM(remaining_sessions) as cnt FROM students")
    total_sessions = cursor.fetchone()['cnt'] or 0
    conn.close()
    return {
        "total_students": total_students,
        "total_classes": total_classes,
        "total_schools": total_schools,
        "total_sessions": total_sessions
    }

def get_monthly_new_students():
    """월별 전체 학생 수 (SQLite 간소화)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM students
    """)
    total = cursor.fetchone()['cnt']
    conn.close()
    # 단순히 현재 월에 total 표시
    now = datetime.now()
    return [{"month": now.strftime("%Y-%m"), "cnt": total}]

def get_monthly_attendance_stats(year_month):
    """월별 출석 통계 (출석/결석/지각/영상보강/미입력 건수)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT status, COUNT(*) as cnt FROM attendance
        WHERE date LIKE ?
        GROUP BY status
    """, (f"{year_month}%",))
    rows = cursor.fetchall()
    conn.close()
    stats = {"출석": 0, "결석": 0, "지각": 0, "영상보강": 0, "미입력": 0}
    for r in rows:
        stats[r['status']] = r['cnt']
    return stats

# ---------- 학교 관리 ----------
def get_all_schools():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schools ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_school(name):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO schools (name) VALUES (?)", (name,))
        conn.commit()
        return True
    except: return False
    finally: conn.close()

def delete_school(school_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schools WHERE id=?", (school_id,))
    conn.commit()
    conn.close()

# ---------- 클래스/반 ----------
def get_all_classes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_class(name, day_of_week, time_slot, notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO classes (name, day_of_week, time_slot, notes) VALUES (?, ?, ?, ?)",
                   (name, day_of_week, time_slot, notes))
    conn.commit()
    conn.close()

def delete_class(class_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE class_id=?", (class_id,))
    cursor.execute("DELETE FROM classes WHERE id=?", (class_id,))
    conn.commit()
    conn.close()

# ---------- 학생 ----------
def get_all_students():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, c.name AS class_name, c.day_of_week, c.time_slot, sch.name as school_name
        FROM students s JOIN classes c ON s.class_id = c.id
        LEFT JOIN schools sch ON s.school_id = sch.id ORDER BY s.name
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_students_by_class(class_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, sch.name as school_name 
        FROM students s LEFT JOIN schools sch ON s.school_id = sch.id
        WHERE s.class_id = ? ORDER BY s.name
    """, (class_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_student(class_id, name, phone, remaining_sessions=8, parent_phone="", school_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO students (class_id, name, phone, remaining_sessions, parent_phone, school_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (class_id, name, phone, remaining_sessions, parent_phone, school_id))
    conn.commit()
    conn.close()

def update_student(student_id, name, phone, parent_phone, class_id, school_id, remaining_sessions):
    """기존 학생 정보 수정"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE students SET name=?, phone=?, parent_phone=?, class_id=?, school_id=?, remaining_sessions=?
        WHERE id=?
    """, (name, phone, parent_phone, class_id, school_id, remaining_sessions, student_id))
    conn.commit()
    conn.close()

def delete_student(student_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM payment_transactions WHERE student_id=?", (student_id,))
    cursor.execute("DELETE FROM attendance WHERE student_id=?", (student_id,))
    cursor.execute("DELETE FROM student_history WHERE student_id=?", (student_id,))
    cursor.execute("DELETE FROM student_scores WHERE student_id=?", (student_id,))
    cursor.execute("DELETE FROM students WHERE id=?", (student_id,))
    conn.commit()
    conn.close()

def get_student(student_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, c.name AS class_name, c.day_of_week, c.time_slot, sch.name as school_name
        FROM students s JOIN classes c ON s.class_id = c.id
        LEFT JOIN schools sch ON s.school_id = sch.id
        WHERE s.id = ?
    """, (student_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# ---------- 🔥 NEW: 횟수/결제 관리 ----------
def add_payment_transaction(student_id, trans_type, amount, note=""):
    """
    결제/차감 내역 기록 및 잔여횟수 업데이트
    trans_type: 'charge' (충전/+), 'deduct' (차감/-), 'payment' (결제/직접입력)
    """
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 현재 잔여횟수 조회
    cursor.execute("SELECT remaining_sessions FROM students WHERE id=?", (student_id,))
    current = cursor.fetchone()['remaining_sessions']
    balance_after = max(0, current + amount)
    
    # 잔여횟수 업데이트
    cursor.execute("UPDATE students SET remaining_sessions = ? WHERE id=?", (balance_after, student_id))
    
    # 거래내역 기록
    cursor.execute("""
        INSERT INTO payment_transactions (student_id, date, type, amount, balance_after, note)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_id, today, trans_type, amount, balance_after, note))
    conn.commit()
    conn.close()
    return balance_after

def get_payment_transactions(student_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM payment_transactions 
        WHERE student_id = ? ORDER BY date DESC
    """, (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def set_next_payment_date(student_id, date_str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE students SET next_payment_date = ? WHERE id=?", (date_str, student_id))
    conn.commit()
    conn.close()

# ---------- 출석 (🔥 ALL STATUSES DEDUCT) ----------
def mark_attendance(student_id, status, date_str=None):
    """
    모든 상태(출석/결석/지각/영상보강) = 1회 차감
    '미입력' = 차감 없음
    """
    if not date_str: date_str = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, status FROM attendance WHERE student_id = ? AND date = ?", (student_id, date_str))
    existing = cursor.fetchone()
    
    if existing:
        old_status = existing['status']
        cursor.execute("UPDATE attendance SET status = ? WHERE id = ?", (status, existing['id']))
        
        # 상태 변경 처리
        # 이전에 차감된 상태였는데 지금은 미입력이면 환불
        # 이전에 미입력이었는데 지금은 유효상태면 차감
        # 그 외에는 상태만 변경 (차감 추가 없음)
        old_deducted = old_status != "미입력"
        new_deducted = status != "미입력"
        
        if old_deducted and not new_deducted:
            # 미입력으로 변경 = 세션 환불
            add_payment_transaction_internal(cursor, student_id, 1, f"[환불] {date_str} {old_status}→{status}")
        elif not old_deducted and new_deducted:
            # 유효상태로 변경 = 세션 차감
            add_payment_transaction_internal(cursor, student_id, -1, f"[차감] {date_str} {status}")
        # else: 상태만 변경 (이미 차감됨)
    else:
        cursor.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                       (student_id, date_str, status))
        if status != "미입력":
            add_payment_transaction_internal(cursor, student_id, -1, f"[차감] {date_str} {status}")
    
    conn.commit()
    conn.close()

def add_payment_transaction_internal(cursor, student_id, amount, note):
    """내부 트랜잭션용 - add_payment_transaction의 내부 버전"""
    cursor.execute("SELECT remaining_sessions FROM students WHERE id=?", (student_id,))
    current = cursor.fetchone()['remaining_sessions']
    balance_after = max(0, current + amount)
    cursor.execute("UPDATE students SET remaining_sessions = ? WHERE id=?", (balance_after, student_id))
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    trans_type = "charge" if amount > 0 else "deduct"
    cursor.execute("""
        INSERT INTO payment_transactions (student_id, date, type, amount, balance_after, note)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_id, today, trans_type, amount, balance_after, note))

def get_attendance_by_date(student_id, date_str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance WHERE student_id = ? AND date = ?", (student_id, date_str))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_month_attendance(student_id, year_month):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance WHERE student_id = ? AND date LIKE ? ORDER BY date",
                   (student_id, f"{year_month}%"))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_month_attendance(year_month):
    """전체 학생의 월별 출석 통계"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT status, COUNT(*) as cnt FROM attendance
        WHERE date LIKE ?
        GROUP BY status
    """, (f"{year_month}%",))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_attendance(attendance_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attendance WHERE id=?", (attendance_id,))
    conn.commit()
    conn.close()

# ---------- 성적 ----------
def add_score(student_id, listening, vocabulary, grammar, reading, test_name="", date_str=None, score_details=""):
    if not date_str: date_str = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO student_scores (student_id, date, listening, vocabulary, grammar, reading, test_name, score_details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (student_id, date_str, listening, vocabulary, grammar, reading, test_name, score_details))
    conn.commit()
    conn.close()

def update_score(score_id, listening, vocabulary, grammar, reading, test_name, score_details=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE student_scores 
        SET listening=?, vocabulary=?, grammar=?, reading=?, test_name=?, score_details=?
        WHERE id=?
    """, (listening, vocabulary, grammar, reading, test_name, score_details, score_id))
    conn.commit()
    conn.close()

def get_student_scores(student_id, limit=20):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_scores WHERE student_id = ? ORDER BY date DESC LIMIT ?", (student_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_monthly_avg_scores(student_id, year_month):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT AVG(listening) as listening, AVG(vocabulary) as vocabulary, 
               AVG(grammar) as grammar, AVG(reading) as reading
        FROM student_scores 
        WHERE student_id = ? AND date LIKE ?
    """, (student_id, f"{year_month}%"))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row and row['listening'] is not None else None

# ---------- 기출/학교시험 ----------
def save_school_exam(school_name, grade, year, semester, analysis_json, ai_report=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO school_exams (school_name, grade, year, semester, analysis_json, ai_report)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (school_name, grade, year, semester, analysis_json, ai_report))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_school_exams(school_name=None):
    conn = get_connection()
    cursor = conn.cursor()
    if school_name:
        cursor.execute("SELECT * FROM school_exams WHERE school_name = ? ORDER BY year DESC, semester", (school_name,))
    else:
        cursor.execute("SELECT * FROM school_exams ORDER BY school_name, year DESC, semester")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_distinct_schools_from_exams():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT school_name FROM school_exams ORDER BY school_name")
    rows = cursor.fetchall()
    conn.close()
    return [r["school_name"] for r in rows]

# ---------- 히스토리 ----------
def add_student_history(student_id, category, notes, week_label=""):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO student_history (student_id, date, category, notes, week_label) VALUES (?, ?, ?, ?, ?)",
                   (student_id, today, category, notes, week_label))
    conn.commit()
    conn.close()

def get_student_history(student_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_history WHERE student_id = ? ORDER BY date DESC", (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_weekly_history(student_id, start_date, end_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_history WHERE student_id = ? AND date BETWEEN ? AND ? ORDER BY date DESC",
                   (student_id, start_date, end_date))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ---------- 성적 삭제 ----------
def delete_score(score_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM student_scores WHERE id=?", (score_id,))
    conn.commit()
    conn.close()

# ---------- 거래내역 삭제 ----------
def delete_payment_transaction(transaction_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM payment_transactions WHERE id=?", (transaction_id,))
    conn.commit()
    conn.close()

# ---------- 반별 영역 관리 ----------
def get_class_areas(class_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM class_areas WHERE class_id = ? ORDER BY id", (class_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_class_area(class_id, area_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO class_areas (class_id, area_name) VALUES (?, ?)", (class_id, area_name))
    conn.commit()
    conn.close()

def delete_class_area(area_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM class_areas WHERE id=?", (area_id,))
    conn.commit()
    conn.close()

# ---------- 주간 출석 조회 ----------
def get_week_attendance(student_id, base_date=None):
    """이번 주 해당 반 수업일의 출석 정보 반환 (최대 2개)"""
    if not base_date:
        base_date = datetime.now()
    student = get_student(student_id)
    if not student:
        return []
    class_id = student['class_id']
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT day_of_week FROM classes WHERE id=?", (class_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return []
    day_map = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
    class_days = [day_map[d.strip()] for d in row['day_of_week'].split('/') if d.strip() in day_map]
    monday = base_date - timedelta(days=base_date.weekday())
    week_dates = []
    for day_idx in class_days:
        date = monday + timedelta(days=day_idx)
        if date <= base_date:
            week_dates.append(date)
    week_dates = sorted(week_dates, reverse=True)[:2]
    results = []
    for d in week_dates:
        date_str = d.strftime("%Y-%m-%d")
        att = get_attendance_by_date(student_id, date_str)
        results.append({
            'date': date_str,
            'day_name': ['월', '화', '수', '목', '금', '토', '일'][d.weekday()],
            'status': att['status'] if att else '미입력'
        })
    return results
