"""
데이터베이스 관리 모듈 - SQLite3 기반
대치앨리영어 학원 관리 시스템
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
    conn = get_connection()
    cursor = conn.cursor()
    
    # 테이블 생성
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            day_of_week TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            notes TEXT DEFAULT ''
        );
        
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            remaining_sessions INTEGER DEFAULT 8,
            parent_phone TEXT DEFAULT '',
            school_id INTEGER,
            FOREIGN KEY (class_id) REFERENCES classes(id),
            FOREIGN KEY (school_id) REFERENCES schools(id)
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
            week_label TEXT DEFAULT '',
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
    
    # 기초 학교 데이터
    schools_list = ["대치중학교", "대청중학교", "단대부중", "숙명여중", "역삼중학교"]
    for sname in schools_list:
        cursor.execute("INSERT OR IGNORE INTO schools (name) VALUES (?)", (sname,))

    # 샘플 데이터: 클래스 2개
    cursor.execute("SELECT count(*) FROM classes")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO classes (name, day_of_week, time_slot, notes) VALUES (?, ?, ?, ?)",
                       ("초등 기초 파닉스", "월/수", "15:00", "7세~초2 대상"))
        cursor.execute("INSERT INTO classes (name, day_of_week, time_slot, notes) VALUES (?, ?, ?, ?)",
                       ("중등 내신 대비 B", "화/목", "18:30", "중2 집중반"))
    
    # 샘플 데이터: 학생 3명
    cursor.execute("SELECT count(*) FROM students")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO students (class_id, name, phone, remaining_sessions, parent_phone, school_id) VALUES (?, ?, ?, ?, ?, ?)",
                       (1, "김민준", "010-1111-1111", 8, "010-1111-0000", 1))
        cursor.execute("INSERT INTO students (class_id, name, phone, remaining_sessions, parent_phone, school_id) VALUES (?, ?, ?, ?, ?, ?)",
                       (1, "이서연", "010-2222-2222", 1, "010-2222-0000", 4))
        cursor.execute("INSERT INTO students (class_id, name, phone, remaining_sessions, parent_phone, school_id) VALUES (?, ?, ?, ?, ?, ?)",
                       (2, "박지호", "010-3333-3333", 0, "010-3333-0000", 2))
    
    conn.commit()
    conn.close()

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
    except:
        return False
    finally:
        conn.close()

def delete_school(school_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schools WHERE id=?", (school_id,))
    conn.commit()
    conn.close()

# ---------- CRUD 함수들 ----------

def get_all_classes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_students_by_class(class_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, sch.name as school_name 
        FROM students s 
        LEFT JOIN schools sch ON s.school_id = sch.id
        WHERE s.class_id = ? ORDER BY s.name
    """, (class_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_students():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, c.name AS class_name, c.day_of_week, c.time_slot, sch.name as school_name
        FROM students s
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN schools sch ON s.school_id = sch.id
        ORDER BY s.name
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_student_by_id(student_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, c.name AS class_name, sch.name as school_name
        FROM students s
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN schools sch ON s.school_id = sch.id
        WHERE s.id = ?
    """, (student_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def mark_attendance(student_id, status):
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
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT * FROM attendance WHERE student_id = ? AND date = ?", (student_id, today))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_attendance_record(student_id, days=7):
    conn = get_connection()
    cursor = conn.cursor()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    cursor.execute("SELECT * FROM attendance WHERE student_id = ? AND date >= ? ORDER BY date DESC",
                   (student_id, since))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_low_session_students(threshold=1):
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

def save_school_exam(school_name, grade, year, semester, analysis_json, ai_report=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO school_exams (school_name, grade, year, semester, analysis_json, ai_report)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (school_name, grade, year, semester, analysis_json, ai_report))
    conn.commit()
    conn.close()

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

# ---------- 학생 CRUD ----------

def add_student(class_id, name, phone, remaining_sessions=8, parent_phone="", school_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO students (class_id, name, phone, remaining_sessions, parent_phone, school_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (class_id, name, phone, remaining_sessions, parent_phone, school_id))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def update_student(student_id, class_id, name, phone, remaining_sessions, parent_phone="", school_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE students
        SET class_id=?, name=?, phone=?, remaining_sessions=?, parent_phone=?, school_id=?
        WHERE id=?
    """, (class_id, name, phone, remaining_sessions, parent_phone, school_id, student_id))
    conn.commit()
    conn.close()

def delete_student(student_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attendance WHERE student_id=?", (student_id,))
    cursor.execute("DELETE FROM student_history WHERE student_id=?", (student_id,))
    cursor.execute("DELETE FROM students WHERE id=?", (student_id,))
    conn.commit()
    conn.close()

def add_class(name, day_of_week, time_slot, notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO classes (name, day_of_week, time_slot, notes) VALUES (?, ?, ?, ?)",
                   (name, day_of_week, time_slot, notes))
    conn.commit()
    conn.close()

def update_class(class_id, name, day_of_week, time_slot, notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE classes SET name=?, day_of_week=?, time_slot=?, notes=? WHERE id=?",
                   (name, day_of_week, time_slot, notes, class_id))
    conn.commit()
    conn.close()

def delete_class(class_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE class_id=?", (class_id,))
    cursor.execute("DELETE FROM classes WHERE id=?", (class_id,))
    conn.commit()
    conn.close()
