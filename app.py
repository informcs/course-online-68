import sys
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import config
import db

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


@app.context_processor
def inject_db_status():
    """ส่งข้อมูลสถานะการเชื่อมต่อฐานข้อมูลไปยังทุกหน้า Template"""
    try:
        # ทดสอบเชื่อมต่อแบบรวดเร็ว
        conn = db.get_connection()
        if hasattr(conn, 'close'):
            conn.close()
        status_text = f"Connected ({config.DB_NAME})"
    except Exception:
        status_text = "DB Disconnected"
    return dict(db_status_badge=status_text)


# ==========================================================
# หน้าหลักและระบบค้นหาคอร์ส (Step 2: ตรวจสอบการรันครั้งแรก)
# ==========================================================
@app.route("/")
def index():
    demo_unimplemented = request.args.get("demo_unimplemented")
    search_query = request.args.get("q", "").strip()
    selected_level = request.args.get("level", "").strip()

    # กรณีทดสอบตามข้อกำหนดขั้นตอนที่ 2:
    # "หากกดค้นหาแล้วขึ้นข้อความแจ้งว่า 'ยังไม่ได้เขียน SQL' ถือว่าระบบเทมเพลตรันสำเร็จเรียบร้อย"
    if demo_unimplemented:
        return render_template(
            "index.html",
            courses=[],
            search_query=search_query,
            selected_level=selected_level,
            test_mode=True
        )

    courses = []
    try:
        courses = db.search_courses(keyword=search_query, level=selected_level)
    except Exception as e:
        flash(f"ไม่สามารถดึงข้อมูลจาก MySQL ได้ (กรุณาตรวจการตั้งค่าใน config.py หรือนำเข้า schema.sql): {e}", "danger")

    return render_template(
        "index.html",
        courses=courses,
        search_query=search_query,
        selected_level=selected_level,
        test_mode=False
    )


# ==========================================================
# การจัดการคอร์สเรียน (CRUD: Course)
# ==========================================================
@app.route("/courses")
def courses():
    try:
        all_courses = db.get_all_courses()
    except Exception as e:
        flash(f"ข้อผิดพลาดในการดึงข้อมูลคอร์ส: {e}", "danger")
        all_courses = []
    return render_template("courses.html", courses=all_courses)


@app.route("/courses/add", methods=["POST"])
def add_course_route():
    course_code = request.form.get("course_code", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "0.00")
    level = request.form.get("level", "Beginner")
    prereq = request.form.get("prerequisite_course_id") or None

    try:
        db.create_course(course_code, title, description, price, level, prereq)
        flash(f"เพิ่มคอร์สเรียน '{title}' สำเร็จแล้ว", "success")
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการเพิ่มคอร์ส: {e}", "danger")

    return redirect(url_for("courses"))


@app.route("/courses/edit/<int:course_id>", methods=["POST"])
def edit_course_route(course_id):
    course_code = request.form.get("course_code", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "0.00")
    level = request.form.get("level", "Beginner")
    prereq = request.form.get("prerequisite_course_id") or None

    try:
        db.update_course(course_id, course_code, title, description, price, level, prereq)
        flash(f"แก้ไขคอร์สเรียน '{title}' เรียบร้อยแล้ว", "success")
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการแก้ไขคอร์ส: {e}", "danger")

    return redirect(url_for("courses"))


@app.route("/courses/delete/<int:course_id>", methods=["POST"])
def delete_course_route(course_id):
    try:
        db.delete_course(course_id)
        flash(f"ลบคอร์สเรียน ID #{course_id} เรียบร้อยแล้ว", "success")
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการลบคอร์ส: {e}", "danger")

    return redirect(url_for("courses"))


# ==========================================================
# การจัดการผู้เรียน (CRUD: Learner)
# ==========================================================
@app.route("/learners")
def learners():
    try:
        all_learners = db.get_all_learners()
    except Exception as e:
        flash(f"ข้อผิดพลาดในการดึงข้อมูลผู้เรียน: {e}", "danger")
        all_learners = []
    return render_template("learners.html", learners=all_learners)


@app.route("/learners/add", methods=["POST"])
def add_learner_route():
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip() or None

    try:
        db.create_learner(first_name, last_name, email, phone)
        flash(f"เพิ่มผู้เรียน '{first_name} {last_name}' สำเร็จแล้ว", "success")
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการเพิ่มผู้เรียน: {e}", "danger")

    return redirect(url_for("learners"))


@app.route("/learners/edit/<int:learner_id>", methods=["POST"])
def edit_learner_route(learner_id):
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip() or None

    try:
        db.update_learner(learner_id, first_name, last_name, email, phone)
        flash(f"แก้ไขข้อมูลผู้เรียน ID #{learner_id} เรียบร้อยแล้ว", "success")
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการแก้ไขผู้เรียน: {e}", "danger")

    return redirect(url_for("learners"))


@app.route("/learners/delete/<int:learner_id>", methods=["POST"])
def delete_learner_route(learner_id):
    try:
        db.delete_learner(learner_id)
        flash(f"ลบข้อมูลผู้เรียน ID #{learner_id} เรียบร้อยแล้ว", "success")
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการลบผู้เรียน: {e}", "danger")

    return redirect(url_for("learners"))


# ==========================================================
# การลงทะเบียนเรียน (Enrollment: M:N)
# ==========================================================
@app.route("/enrollments")
def enrollments():
    prefill_course_id = request.args.get("prefill_course", type=int)
    try:
        all_enrollments = db.get_all_enrollments()
        all_learners = db.get_all_learners()
        all_courses = db.get_all_courses()
    except Exception as e:
        flash(f"ข้อผิดพลาดในการดึงข้อมูลการลงทะเบียน: {e}", "danger")
        all_enrollments = []
        all_learners = []
        all_courses = []

    return render_template(
        "enrollments.html",
        enrollments=all_enrollments,
        learners=all_learners,
        courses=all_courses,
        prefill_course_id=prefill_course_id
    )


@app.route("/enrollments/add", methods=["POST"])
def enroll_course_route():
    learner_id = request.form.get("learner_id")
    course_id = request.form.get("course_id")
    status = request.form.get("status", "ENROLLED")
    payment_method = request.form.get("payment_method", "PromptPay")
    amount_paid = request.form.get("amount_paid")

    if not learner_id or not course_id:
        flash("กรุณาเลือกผู้เรียนและคอร์สเรียนให้ครบถ้วน", "warning")
        return redirect(url_for("enrollments"))

    try:
        db.enroll_course(learner_id, course_id, status, payment_method, amount_paid)
        flash("ลงทะเบียนเรียนเรียบร้อยแล้ว", "success")
    except ValueError as ve:
        # ดักจับเงื่อนไข Business logic เช่น ติดวิชาบังคับก่อน หรือลงทะเบียนซ้ำ
        flash(f"{ve}", "danger")
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการลงทะเบียน: {e}", "danger")

    return redirect(url_for("enrollments"))


# ==========================================================
# หน้าชำระเงินและลงทะเบียนเรียน (Checkout & Payment)
# ==========================================================
@app.route("/checkout/<int:course_id>")
def checkout(course_id):
    try:
        course = db.get_course_by_id(course_id)
        if not course:
            flash("ไม่พบคอร์สเรียนที่ต้องการลงทะเบียน", "warning")
            return redirect(url_for("index"))
        
        subsequent_courses = db.get_subsequent_courses(course_id)
        # ดึงรายชื่อผู้เรียนพร้อมสถานะว่าใครผ่านเงื่อนไขวิชาบังคับก่อนบ้าง
        learners = db.get_learners_with_eligibility(course_id)
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการโหลดข้อมูลชำระเงิน: {e}", "danger")
        return redirect(url_for("index"))

    return render_template(
        "checkout.html",
        course=course,
        subsequent_courses=subsequent_courses,
        learners=learners
    )


@app.route("/checkout/<int:course_id>/pay", methods=["POST"])
def process_payment(course_id):
    learner_id = request.form.get("learner_id")
    payment_method = request.form.get("payment_method", "PromptPay")
    
    if not learner_id:
        flash("กรุณาเลือกผู้เรียนที่ต้องการลงทะเบียน", "warning")
        return redirect(url_for("checkout", course_id=course_id))

    try:
        course = db.get_course_by_id(course_id)
        if not course:
            flash("ไม่พบคอร์สเรียนที่ต้องการลงทะเบียน", "danger")
            return redirect(url_for("index"))

        price = float(course["price"]) if course else 0.0
        
        # db.enroll_course จะตรวจสอบทั้งวิชาบังคับก่อน และการลงทะเบียนซ้ำอย่างเคร่งครัด
        db.enroll_course(
            learner_id=learner_id,
            course_id=course_id,
            status="IN_PROGRESS",
            payment_method=payment_method,
            amount_paid=price
        )
        flash(f"ชำระเงินจำนวน ฿{price:,.2f} ผ่าน {payment_method} สำเร็จ! ลงทะเบียนคอร์ส '{course['title']}' เรียบร้อยแล้ว", "success")
        return redirect(url_for("enrollments"))
    except ValueError as ve:
        # แจ้งเตือนสาเหตุที่ลงทะเบียนไม่ได้ เช่น ไม่ผ่าน Prerequisite หรือเคยลงแล้ว
        flash(f"{ve}", "danger")
        return redirect(url_for("checkout", course_id=course_id))
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการชำระเงินหรือลงทะเบียน: {e}", "danger")
        return redirect(url_for("checkout", course_id=course_id))


# ==========================================================
# API สำหรับตรวจสอบคุณสมบัติวิชาบังคับก่อนแบบเรียลไทม์
# ==========================================================
@app.route("/api/check-prerequisite")
def api_check_prerequisite():
    learner_id = request.args.get("learner_id", type=int)
    course_id = request.args.get("course_id", type=int)

    if not learner_id or not course_id:
        return jsonify({"ok": False, "message": "กรุณาระบุ learner_id และ course_id"}), 400

    course = db.get_course_by_id(course_id)
    if not course:
        return jsonify({"ok": False, "message": "ไม่พบคอร์สเรียน"}), 404

    already, cur_status = db.is_already_enrolled(learner_id, course_id)
    satisfied, reason, prereq = db.check_prerequisite_satisfied(learner_id, course_id)

    can_enroll = (not already) and satisfied

    return jsonify({
        "ok": True,
        "can_enroll": can_enroll,
        "already_enrolled": already,
        "current_status": cur_status,
        "current_status_th": db.STATUS_THAI.get(cur_status, cur_status) if cur_status else None,
        "prereq_satisfied": satisfied,
        "prereq_required": bool(course.get("prerequisite_course_id")),
        "prereq_code": prereq.get("course_code") if prereq else None,
        "prereq_title": prereq.get("title") if prereq else None,
        "message": reason
    })


# ==========================================================
# หน้ารายงานการเงิน (Money Management)
# ==========================================================
@app.route("/money-management")
def money_management():
    try:
        summary = db.report_money_management_summary()
        by_course = db.report_money_by_course()
        by_method = db.report_money_by_payment_method()
        paid_learners = db.report_paid_learners_status()
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการดึงข้อมูลรายงานการเงิน: {e}", "danger")
        summary = {
            'total_transactions': 0,
            'total_paid_learners': 0,
            'total_revenue': 0.0,
            'active_studying_count': 0,
            'completed_count': 0,
            'newly_enrolled_count': 0
        }
        by_course = []
        by_method = []
        paid_learners = []

    return render_template(
        "money_management.html",
        summary=summary,
        by_course=by_course,
        by_method=by_method,
        paid_learners=paid_learners
    )


@app.route("/enrollments/status/<int:enrollment_id>", methods=["POST"])
def update_enrollment_status_route(enrollment_id):
    status = request.form.get("status")
    try:
        db.update_enrollment_status(enrollment_id, status)
        flash(f"อัปเดตสถานะการลงทะเบียน #{enrollment_id} เป็น '{status}' สำเร็จแล้ว", "success")
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการอัปเดตสถานะ: {e}", "danger")

    return redirect(url_for("enrollments"))


@app.route("/enrollments/delete/<int:enrollment_id>", methods=["POST"])
def delete_enrollment_route(enrollment_id):
    try:
        db.delete_enrollment(enrollment_id)
        flash(f"ยกเลิกการลงทะเบียน #{enrollment_id} เรียบร้อยแล้ว", "success")
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการยกเลิกการลงทะเบียน: {e}", "danger")

    return redirect(url_for("enrollments"))



# ==========================================================
# 3 รายงานบังคับ (Mandatory Reports)
# ==========================================================
@app.route("/reports")
def reports():
    try:
        popular = db.report_popular_courses()
        completion = db.report_course_completion_rate()
        prereq = db.report_courses_with_prerequisites()
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการประมวลผลรายงานจากฐานข้อมูล: {e}", "danger")
        popular = []
        completion = []
        prereq = []

    return render_template(
        "reports.html",
        popular_courses=popular,
        completion_rates=completion,
        prerequisite_courses=prereq
    )


if __name__ == "__main__":
    print("==========================================================")
    print(" กำลังเริ่มต้นเซิร์ฟเวอร์ระบบลงทะเบียนคอร์สออนไลน์...")
    print(" เปิดเบราว์เซอร์ไปที่: http://127.0.0.1:5000")
    print("==========================================================")
    # ใช้ host="0.0.0.0" เพื่อให้เครื่องอื่นในวง Wi-Fi เดียวกันสามารถเปิดเว็บได้
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port, debug=True)
