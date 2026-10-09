import config
from datetime import datetime

# พยายาม Import MySQL connector โดยรองรับทั้ง mysql.connector และ pymysql
try:
    import mysql.connector
    from mysql.connector import errorcode
    USE_MYSQL_CONNECTOR = True
except ImportError:
    USE_MYSQL_CONNECTOR = False
    try:
        import pymysql
        import pymysql.cursors
    except ImportError:
        pass


def get_connection():
    """
    สร้างและส่งคืน Database Connection สำหรับ MySQL
    ใช้ค่าการตั้งค่าจาก config.py
    """
    if USE_MYSQL_CONNECTOR:
        return mysql.connector.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset="utf8mb4"
        )
    else:
        # Fallback กรณีใช้ pymysql
        return pymysql.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )


def run_query(sql, params=None):
    """
    ฟังก์ชันสำหรับรันคำสั่ง SELECT เพื่อดึงข้อมูลออกมา
    - sql: คำสั่ง SQL เช่น "SELECT * FROM course WHERE level = %s"
    - params: tuple หรือ list ของพารามิเตอร์ที่จะแทนที่ใน %s ป้องกัน SQL Injection
    คืนค่าเป็น: list of dicts (แถวข้อมูลในรูปแบบ Dictionary)
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        if USE_MYSQL_CONNECTOR:
            cursor = conn.cursor(dictionary=True)
        else:
            cursor = conn.cursor()

        cursor.execute(sql, params or ())
        results = cursor.fetchall()
        return results
    except Exception as e:
        print(f"[Error in run_query]: {e}")
        raise e
    finally:
        if cursor:
            cursor.close()
        if conn and (hasattr(conn, 'is_connected') and conn.is_connected() or hasattr(conn, 'open') and conn.open):
            conn.close()


def run_command(sql, params=None):
    """
    ฟังก์ชันสำหรับรันคำสั่ง INSERT, UPDATE, DELETE หรือ DDL
    - sql: คำสั่ง SQL เช่น "INSERT INTO learner (first_name, last_name) VALUES (%s, %s)"
    - params: tuple หรือ list ของพารามิเตอร์ที่จะแทนที่ใน %s
    คืนค่าเป็น: dict ที่มี lastrowid (ID แถวล่าสุดที่เพิ่ม) และ rowcount (จำนวนแถวที่ได้รับผลกระทบ)
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        if USE_MYSQL_CONNECTOR:
            cursor = conn.cursor()
        else:
            cursor = conn.cursor()

        cursor.execute(sql, params or ())
        conn.commit()
        return {
            "lastrowid": cursor.lastrowid,
            "rowcount": cursor.rowcount
        }
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[Error in run_command]: {e}")
        raise e
    finally:
        if cursor:
            cursor.close()
        if conn and (hasattr(conn, 'is_connected') and conn.is_connected() or hasattr(conn, 'open') and conn.open):
            conn.close()


# ==========================================================
# 1. ฟังก์ชัน CRUD สำหรับ Course (คอร์สเรียน)
# ==========================================================

def get_all_courses():
    """ดึงข้อมูลคอร์สเรียนทั้งหมด เรียงตาม course_id"""
    sql = """
        SELECT c.*, p.title AS prerequisite_title, p.course_code AS prerequisite_code 
        FROM course c
        LEFT JOIN course p ON c.prerequisite_course_id = p.course_id
        ORDER BY c.course_id ASC;
    """
    return run_query(sql)


def search_courses(keyword=None, level=None):
    """
    ค้นหาคอร์สตาม Keyword (ชื่อ, รหัส, คำอธิบาย) หรือระดับความยาก
    ใช้ %s เสมอเพื่อป้องกัน SQL Injection
    """
    sql = """
        SELECT c.*, p.title AS prerequisite_title, p.course_code AS prerequisite_code 
        FROM course c
        LEFT JOIN course p ON c.prerequisite_course_id = p.course_id
        WHERE 1=1
    """
    params = []

    if keyword:
        sql += " AND (c.title LIKE %s OR c.course_code LIKE %s OR c.description LIKE %s)"
        like_term = f"%{keyword}%"
        params.extend([like_term, like_term, like_term])

    if level:
        sql += " AND c.level = %s"
        params.append(level)

    sql += " ORDER BY c.course_id ASC;"
    return run_query(sql, tuple(params))


def get_course_by_id(course_id):
    """ดึงข้อมูลคอร์สเรียนเดี่ยวตาม ID พร้อมชื่อวิชาบังคับก่อน"""
    sql = """
        SELECT 
            c.*, 
            p.title AS prerequisite_title, 
            p.course_code AS prerequisite_code
        FROM course c
        LEFT JOIN course p ON c.prerequisite_course_id = p.course_id
        WHERE c.course_id = %s;
    """
    results = run_query(sql, (course_id,))
    return results[0] if results else None


def get_subsequent_courses(course_id):
    """ค้นหาคอร์สที่สามารถเรียนต่อได้หลังจากจบคอร์สนี้ (วิชาที่มีคอร์สนี้เป็น Prerequisite)"""
    sql = """
        SELECT course_id, course_code, title, level, price, description
        FROM course
        WHERE prerequisite_course_id = %s
        ORDER BY course_id ASC;
    """
    return run_query(sql, (course_id,))



def create_course(course_code, title, description, price, level, prerequisite_course_id=None):
    """เพิ่มคอร์สเรียนใหม่ (INSERT)"""
    sql = """
        INSERT INTO course (course_code, title, description, price, level, prerequisite_course_id)
        VALUES (%s, %s, %s, %s, %s, %s);
    """
    # ถ้าค่าเป็นสตริงว่างให้แปลงเป็น None (NULL ในฐานข้อมูล)
    prereq = int(prerequisite_course_id) if prerequisite_course_id else None
    params = (course_code, title, description, float(price), level, prereq)
    return run_command(sql, params)


def update_course(course_id, course_code, title, description, price, level, prerequisite_course_id=None):
    """แก้ไขข้อมูลคอร์สเรียน (UPDATE)"""
    sql = """
        UPDATE course 
        SET course_code = %s, title = %s, description = %s, price = %s, 
            level = %s, prerequisite_course_id = %s
        WHERE course_id = %s;
    """
    prereq = int(prerequisite_course_id) if prerequisite_course_id else None
    params = (course_code, title, description, float(price), level, prereq, course_id)
    return run_command(sql, params)


def delete_course(course_id):
    """ลบคอร์สเรียน (DELETE)"""
    sql = "DELETE FROM course WHERE course_id = %s;"
    return run_command(sql, (course_id,))


# ==========================================================
# 2. ฟังก์ชัน CRUD สำหรับ Learner (ผู้เรียน)
# ==========================================================

def get_all_learners():
    """ดึงข้อมูลผู้เรียนทั้งหมด"""
    sql = "SELECT * FROM learner ORDER BY learner_id ASC;"
    return run_query(sql)


def get_learner_by_id(learner_id):
    """ดึงข้อมูลผู้เรียนเดี่ยวตาม ID"""
    sql = "SELECT * FROM learner WHERE learner_id = %s;"
    results = run_query(sql, (learner_id,))
    return results[0] if results else None


def create_learner(first_name, last_name, email, phone=None):
    """เพิ่มผู้เรียนใหม่ (INSERT)"""
    sql = """
        INSERT INTO learner (first_name, last_name, email, phone)
        VALUES (%s, %s, %s, %s);
    """
    params = (first_name, last_name, email, phone)
    return run_command(sql, params)


def update_learner(learner_id, first_name, last_name, email, phone=None):
    """แก้ไขข้อมูลผู้เรียน (UPDATE)"""
    sql = """
        UPDATE learner 
        SET first_name = %s, last_name = %s, email = %s, phone = %s
        WHERE learner_id = %s;
    """
    params = (first_name, last_name, email, phone, learner_id)
    return run_command(sql, params)


def delete_learner(learner_id):
    """ลบข้อมูลผู้เรียน (DELETE)"""
    sql = "DELETE FROM learner WHERE learner_id = %s;"
    return run_command(sql, (learner_id,))


# ==========================================================
# 3. ฟังก์ชัน CRUD สำหรับ Enrollment (การลงทะเบียน)
# ==========================================================

def get_all_enrollments():
    """ดึงข้อมูลการลงทะเบียนทั้งหมด พร้อมชื่อผู้เรียน ชื่อคอร์ส และข้อมูลการชำระเงิน"""
    sql = """
        SELECT 
            e.enrollment_id,
            e.enrollment_date,
            e.status,
            e.completion_date,
            e.payment_method,
            e.amount_paid,
            l.learner_id,
            CONCAT(l.first_name, ' ', l.last_name) AS learner_name,
            l.email AS learner_email,
            c.course_id,
            c.course_code,
            c.title AS course_title,
            c.price AS course_price
        FROM enrollment e
        JOIN learner l ON e.learner_id = l.learner_id
        JOIN course c ON e.course_id = c.course_id
        ORDER BY e.enrollment_date DESC;
    """
    return run_query(sql)


STATUS_THAI = {
    'ENROLLED': 'ลงทะเบียนแล้ว (ยังไม่เริ่มเรียน)',
    'IN_PROGRESS': 'กำลังเรียนอยู่ (ยังไม่จบ)',
    'COMPLETED': 'เรียนจบหลักสูตรแล้ว (ผ่าน)',
    'DROPPED': 'ถอนการเรียน'
}


def is_already_enrolled(learner_id, course_id):
    """
    ตรวจสอบว่าผู้เรียนลงทะเบียนในคอร์สนี้แล้วหรือไม่
    คืนค่าเป็น tuple: (already_enrolled: bool, current_status: str | None)
    """
    sql = "SELECT enrollment_id, status FROM enrollment WHERE learner_id = %s AND course_id = %s;"
    results = run_query(sql, (learner_id, course_id))
    if results:
        return True, results[0]["status"]
    return False, None


def check_prerequisite_satisfied(learner_id, course_id):
    """
    ตรวจสอบว่าผู้เรียนมีคุณสมบัติผ่านวิชาบังคับก่อน (Prerequisite) ของคอร์สนี้หรือไม่
    เงื่อนไข: หากคอร์สมีวิชาบังคับก่อน ผู้เรียนต้องมีประวัติการลงทะเบียนในวิชานั้น และมีสถานะเป็น 'COMPLETED' เท่านั้น
    คืนค่าเป็น tuple: (is_satisfied: bool, message: str, prereq_course_info: dict | None)
    """
    course = get_course_by_id(course_id)
    if not course:
        return False, "ไม่พบคอร์สเรียนที่ระบุในระบบ", None

    prereq_id = course.get("prerequisite_course_id")
    if not prereq_id:
        # ไม่มีวิชาบังคับก่อน สามารถลงเรียนได้ทันที
        return True, "คอร์สนี้ไม่มีวิชาบังคับก่อน สามารถลงทะเบียนได้ทันที", None

    prereq_course = get_course_by_id(prereq_id)
    prereq_label = f"[{prereq_course['course_code']}] {prereq_course['title']}" if prereq_course else f"ID #{prereq_id}"

    # ตรวจสอบประวัติการลงทะเบียนในวิชาบังคับก่อนของผู้เรียน
    sql = """
        SELECT enrollment_id, status 
        FROM enrollment 
        WHERE learner_id = %s AND course_id = %s;
    """
    results = run_query(sql, (learner_id, prereq_id))

    if not results:
        return False, f"ผู้เรียนยังไม่ได้ลงทะเบียนเรียนวิชาบังคับก่อน: {prereq_label}", prereq_course

    status = results[0]["status"]
    if status != "COMPLETED":
        status_text = STATUS_THAI.get(status, status)
        return False, f"ผู้เรียนยังเรียนวิชาบังคับก่อนไม่ผ่าน: {prereq_label} (สถานะปัจจุบัน: {status_text}) ต้องมีสถานะ 'COMPLETED' เท่านั้นจึงจะลงทะเบียนได้", prereq_course

    return True, f"ผู้เรียนผ่านวิชาบังคับก่อน {prereq_label} เรียบร้อยแล้ว", prereq_course


def get_learners_with_eligibility(course_id):
    """
    ดึงรายชื่อผู้เรียนทั้งหมดพร้อมสถานะความพร้อมในการลงทะเบียนคอร์สนี้
    (ตรวจสอบทั้งการลงทะเบียนซ้ำ และการผ่านเงื่อนไขวิชาบังคับก่อน)
    """
    learners = get_all_learners()
    for l in learners:
        lid = l['learner_id']
        already, cur_status = is_already_enrolled(lid, course_id)
        satisfied, reason, prereq_info = check_prerequisite_satisfied(lid, course_id)

        l['already_enrolled'] = already
        l['current_status'] = cur_status
        l['current_status_th'] = STATUS_THAI.get(cur_status, cur_status) if cur_status else None
        l['prereq_satisfied'] = satisfied
        l['eligibility_message'] = reason

        if already:
            l['can_enroll'] = False
            l['reason_tag'] = f"ลงทะเบียนแล้ว ({l['current_status_th']})"
        elif not satisfied:
            l['can_enroll'] = False
            l['reason_tag'] = "ไม่ผ่านวิชาบังคับก่อน"
        else:
            l['can_enroll'] = True
            l['reason_tag'] = "พร้อมลงทะเบียน"

    return learners


def enroll_course(learner_id, course_id, status='ENROLLED', payment_method='PromptPay', amount_paid=None):
    """
    ลงทะเบียนเรียนใหม่ (INSERT) 
    บังคับตรวจสอบ:
    1. ตรวจสอบการลงทะเบียนซ้ำ (ป้องกันลงทะเบียนวิชาเดิมซ้ำ)
    2. ตรวจสอบวิชาบังคับก่อน (Prerequisite) ต้องผ่าน (COMPLETED) เท่านั้น
    """
    # 1. ตรวจสอบว่าเคยลงทะเบียนคอร์สนี้แล้วหรือไม่
    already, current_status = is_already_enrolled(learner_id, course_id)
    if already:
        status_text = STATUS_THAI.get(current_status, current_status)
        raise ValueError(f"ผู้เรียนท่านนี้ได้ลงทะเบียนคอร์สนี้ไปแล้ว (สถานะปัจจุบัน: {status_text})")

    # 2. ตรวจสอบเงื่อนไขวิชาบังคับก่อน (Prerequisite)
    satisfied, reason, _ = check_prerequisite_satisfied(learner_id, course_id)
    if not satisfied:
        raise ValueError(f"ไม่สามารถลงทะเบียนได้: {reason}")

    if amount_paid is None:
        course = get_course_by_id(course_id)
        amount_paid = float(course['price']) if course and 'price' in course else 0.0

    sql = """
        INSERT INTO enrollment (learner_id, course_id, status, payment_method, amount_paid)
        VALUES (%s, %s, %s, %s, %s);
    """
    params = (learner_id, course_id, status, payment_method, float(amount_paid))
    return run_command(sql, params)


def update_enrollment_status(enrollment_id, status):
    """
    แก้ไขสถานะการเรียน (UPDATE)
    หากสถานะเป็น COMPLETED จะบันทึก completion_date ปัจจุบันด้วย
    """
    if status == 'COMPLETED':
        sql = """
            UPDATE enrollment 
            SET status = %s, completion_date = NOW()
            WHERE enrollment_id = %s;
        """
        params = (status, enrollment_id)
    else:
        sql = """
            UPDATE enrollment 
            SET status = %s, completion_date = NULL
            WHERE enrollment_id = %s;
        """
        params = (status, enrollment_id)
    return run_command(sql, params)


def delete_enrollment(enrollment_id):
    """ยกเลิกการลงทะเบียน (DELETE)"""
    sql = "DELETE FROM enrollment WHERE enrollment_id = %s;"
    return run_command(sql, (enrollment_id,))


# ==========================================================
# 4. ฟังก์ชันสำหรับ Lesson (บทเรียน)
# ==========================================================

def get_lessons_by_course(course_id):
    """ดึงบทเรียนย่อยทั้งหมดในคอร์ส เรียงตาม lesson_order"""
    sql = """
        SELECT * FROM lesson 
        WHERE course_id = %s 
        ORDER BY lesson_order ASC;
    """
    return run_query(sql, (course_id,))


# ==========================================================
# 5. รายงานบังคับ 3 รายการ (Mandatory Reports)
# ==========================================================

def report_popular_courses():
    """
    รายงานที่ 1: คอร์สยอดนิยม ตามจำนวนผู้ลงทะเบียน
    เทคนิค: JOIN + GROUP BY + COUNT
    เรียงลำดับจากจำนวนผู้ลงทะเบียนมากที่สุดไปน้อยที่สุด
    """
    sql = """
        SELECT 
            c.course_id,
            c.course_code,
            c.title AS course_title,
            c.level,
            c.price,
            COUNT(e.enrollment_id) AS total_enrolled
        FROM course c
        LEFT JOIN enrollment e ON c.course_id = e.course_id
        GROUP BY 
            c.course_id, 
            c.course_code, 
            c.title, 
            c.level, 
            c.price
        ORDER BY total_enrolled DESC, c.course_code ASC;
    """
    return run_query(sql)


def report_course_completion_rate():
    """
    รายงานที่ 2: อัตราการเรียนจบ ของแต่ละคอร์สจากสถานะใน enrollment
    เทคนิค: GROUP BY + การคำนวณสัดส่วน (Completion Rate Percentage)
    สูตร: (จำนวนคนที่เรียนจบ / จำนวนคนลงทะเบียนทั้งหมด) * 100
    """
    sql = """
        SELECT 
            c.course_id,
            c.course_code,
            c.title AS course_title,
            COUNT(e.enrollment_id) AS total_enrolled,
            SUM(CASE WHEN e.status = 'COMPLETED' THEN 1 ELSE 0 END) AS total_completed,
            SUM(CASE WHEN e.status = 'IN_PROGRESS' THEN 1 ELSE 0 END) AS total_in_progress,
            SUM(CASE WHEN e.status = 'DROPPED' THEN 1 ELSE 0 END) AS total_dropped,
            ROUND(
                (SUM(CASE WHEN e.status = 'COMPLETED' THEN 1 ELSE 0 END) * 100.0) 
                / NULLIF(COUNT(e.enrollment_id), 0), 2
            ) AS completion_rate_percentage
        FROM course c
        JOIN enrollment e ON c.course_id = e.course_id
        GROUP BY 
            c.course_id, 
            c.course_code, 
            c.title
        ORDER BY completion_rate_percentage DESC, total_enrolled DESC;
    """
    return run_query(sql)


def report_courses_with_prerequisites():
    """
    รายงานที่ 3: คอร์สพร้อมชื่อวิชาที่เป็น Prerequisite
    เทคนิค: Self-JOIN ของตาราง course (c เชื่อมกับ p ด้วย prerequisite_course_id)
    แสดงทั้งคอร์สที่มีและไม่มีวิชาบังคับก่อน
    """
    sql = """
        SELECT 
            c.course_id,
            c.course_code,
            c.title AS course_title,
            c.level AS course_level,
            c.price,
            p.course_code AS prerequisite_code,
            COALESCE(p.title, 'ไม่มีวิชาบังคับก่อน') AS prerequisite_title,
            COALESCE(p.level, '-') AS prerequisite_level
        FROM course c
        LEFT JOIN course p ON c.prerequisite_course_id = p.course_id
        ORDER BY c.course_id ASC;
    """
    return run_query(sql)


# ==========================================================
# 4. รายงานระบบการเงิน (Money Management Reports)
# ==========================================================

def report_money_management_summary():
    """
    สรุปภาพรวมทางการเงิน: ยอดเงินรวม, จำนวนผู้เรียนที่จ่ายเงินแล้ว, 
    จำนวนที่กำลังเรียนอยู่, จำนวนที่เรียนจบ
    """
    sql = """
        SELECT 
            COUNT(*) AS total_transactions,
            COUNT(DISTINCT learner_id) AS total_paid_learners,
            COALESCE(SUM(CASE WHEN status != 'DROPPED' THEN amount_paid ELSE 0 END), 0) AS total_revenue,
            COUNT(CASE WHEN status = 'IN_PROGRESS' THEN 1 END) AS active_studying_count,
            COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) AS completed_count,
            COUNT(CASE WHEN status = 'ENROLLED' THEN 1 END) AS newly_enrolled_count
        FROM enrollment;
    """
    results = run_query(sql)
    return results[0] if results else {
        'total_transactions': 0,
        'total_paid_learners': 0,
        'total_revenue': 0.0,
        'active_studying_count': 0,
        'completed_count': 0,
        'newly_enrolled_count': 0
    }


def report_money_by_course():
    """
    รายงานรายได้รวมแยกตามแต่ละคอร์สเรียน พร้อมจำนวนผู้เรียนที่ลงทะเบียน
    """
    sql = """
        SELECT 
            c.course_id,
            c.course_code,
            c.title AS course_title,
            c.level,
            c.price,
            COUNT(e.enrollment_id) AS total_enrolled,
            COUNT(CASE WHEN e.status = 'IN_PROGRESS' THEN 1 END) AS active_count,
            COUNT(CASE WHEN e.status = 'COMPLETED' THEN 1 END) AS completed_count,
            COALESCE(SUM(CASE WHEN e.status != 'DROPPED' THEN e.amount_paid ELSE 0 END), 0) AS total_revenue
        FROM course c
        LEFT JOIN enrollment e ON c.course_id = e.course_id
        GROUP BY c.course_id, c.course_code, c.title, c.level, c.price
        ORDER BY total_revenue DESC, total_enrolled DESC;
    """
    return run_query(sql)


def report_money_by_payment_method():
    """
    รายงานรายได้แยกตามช่องทางการชำระเงิน (PromptPay, TrueMoney, Mastercard, บัตรทรูมันนี่)
    """
    sql = """
        SELECT 
            payment_method,
            COUNT(*) AS transaction_count,
            COALESCE(SUM(amount_paid), 0) AS total_amount
        FROM enrollment
        WHERE status != 'DROPPED'
        GROUP BY payment_method
        ORDER BY total_amount DESC;
    """
    return run_query(sql)


def report_paid_learners_status():
    """
    รายงานรายชื่อผู้เรียนที่ชำระเงินแล้ว กำลังเรียนคอร์สอะไรอยู่ ยอดเงิน และช่องทางที่จ่าย
    """
    sql = """
        SELECT 
            e.enrollment_id,
            e.enrollment_date,
            e.status,
            e.payment_method,
            e.amount_paid,
            l.learner_id,
            CONCAT(l.first_name, ' ', l.last_name) AS learner_name,
            l.email AS learner_email,
            l.phone AS learner_phone,
            c.course_id,
            c.course_code,
            c.title AS course_title,
            c.level AS course_level,
            c.price AS course_price
        FROM enrollment e
        JOIN learner l ON e.learner_id = l.learner_id
        JOIN course c ON e.course_id = c.course_id
        ORDER BY e.enrollment_date DESC;
    """
    return run_query(sql)

