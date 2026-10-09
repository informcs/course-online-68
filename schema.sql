-- ==========================================================
-- ฐานข้อมูลระบบลงทะเบียนคอร์สออนไลน์ (Online Course System)
-- สำหรับการส่งงานและนำเสนอวิชา Database Systems
-- ==========================================================

CREATE DATABASE IF NOT EXISTS online_course_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE online_course_db;

-- ปิด Foreign Key Check ชั่วคราวเพื่อให้ Drop Table ได้อย่างราบรื่น
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS progress;
DROP TABLE IF EXISTS enrollment;
DROP TABLE IF EXISTS lesson;
DROP TABLE IF EXISTS course;
DROP TABLE IF EXISTS learner;
SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------------------------------------
-- 1. ตาราง learner (ข้อมูลผู้เรียน)
-- ----------------------------------------------------------
CREATE TABLE learner (
    learner_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL COMMENT 'ชื่อจริง',
    last_name VARCHAR(100) NOT NULL COMMENT 'นามสกุล',
    email VARCHAR(150) NOT NULL UNIQUE COMMENT 'อีเมล (ไม่ซ้ำกัน)',
    phone VARCHAR(20) NULL COMMENT 'เบอร์โทรศัพท์',
    registered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'วันที่สมัครสมาชิก'
) ENGINE=InnoDB COMMENT='ตารางเก็บข้อมูลผู้เรียน';

-- ----------------------------------------------------------
-- 2. ตาราง course (คอร์สเรียน พร้อม Self-Reference: Prerequisite)
-- ----------------------------------------------------------
CREATE TABLE course (
    course_id INT AUTO_INCREMENT PRIMARY KEY,
    course_code VARCHAR(20) NOT NULL UNIQUE COMMENT 'รหัสวิชา เช่น CS101',
    title VARCHAR(200) NOT NULL COMMENT 'ชื่อคอร์สเรียน',
    description TEXT NULL COMMENT 'รายละเอียดเนื้อหาคอร์ส',
    price DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT 'ราคาคอร์ส (บาท)',
    level ENUM('Beginner', 'Intermediate', 'Advanced') NOT NULL DEFAULT 'Beginner' COMMENT 'ระดับความยาก',
    prerequisite_course_id INT NULL COMMENT 'วิชาบังคับก่อน (Self-reference ชี้ไปที่ course_id ในตารางเดียวกัน)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'วันที่สร้างคอร์ส',
    CONSTRAINT fk_course_prerequisite 
        FOREIGN KEY (prerequisite_course_id) 
        REFERENCES course(course_id) 
        ON DELETE SET NULL 
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='ตารางเก็บข้อมูลคอร์สเรียนและวิชาบังคับก่อน';

-- ----------------------------------------------------------
-- 3. ตาราง lesson (บทเรียนย่อยในแต่ละคอร์ส)
-- ----------------------------------------------------------
CREATE TABLE lesson (
    lesson_id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL COMMENT 'รหัสคอร์สที่บทเรียนนี้สังกัดอยู่',
    title VARCHAR(200) NOT NULL COMMENT 'ชื่อบทเรียน',
    lesson_order INT NOT NULL COMMENT 'ลำดับที่ของบทเรียนในคอร์ส',
    duration_minutes INT NOT NULL DEFAULT 15 COMMENT 'ระยะเวลาโดยประมาณ (นาที)',
    video_url VARCHAR(255) NULL COMMENT 'ลิงก์วิดีโอหรือสื่อการเรียน',
    CONSTRAINT fk_lesson_course 
        FOREIGN KEY (course_id) 
        REFERENCES course(course_id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    CONSTRAINT uq_course_lesson_order UNIQUE (course_id, lesson_order)
) ENGINE=InnoDB COMMENT='ตารางเก็บบทเรียนย่อยของแต่ละคอร์ส';

-- ----------------------------------------------------------
-- 4. ตาราง enrollment (การลงทะเบียนเรียน: M:N ระหว่าง learner x course)
-- ----------------------------------------------------------
CREATE TABLE enrollment (
    enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
    learner_id INT NOT NULL COMMENT 'รหัสผู้เรียน',
    course_id INT NOT NULL COMMENT 'รหัสคอร์สเรียน',
    enrollment_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'วันที่และเวลาที่ลงทะเบียน',
    status ENUM('ENROLLED', 'IN_PROGRESS', 'COMPLETED', 'DROPPED') NOT NULL DEFAULT 'ENROLLED' COMMENT 'สถานะการเรียนในคอร์ส',
    completion_date DATETIME NULL COMMENT 'วันที่เรียนจบ (กรณีสถานะ COMPLETED)',
    payment_method VARCHAR(50) NOT NULL DEFAULT 'PromptPay' COMMENT 'ช่องทางการชำระเงิน',
    amount_paid DECIMAL(10, 2) NOT NULL DEFAULT 0.00 COMMENT 'จำนวนเงินที่ชำระ (บาท)',
    CONSTRAINT fk_enrollment_learner 
        FOREIGN KEY (learner_id) 
        REFERENCES learner(learner_id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    CONSTRAINT fk_enrollment_course 
        FOREIGN KEY (course_id) 
        REFERENCES course(course_id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    CONSTRAINT uq_learner_course UNIQUE (learner_id, course_id)
) ENGINE=InnoDB COMMENT='ตารางการลงทะเบียนเรียนของผู้เรียนในคอร์ส';

-- ----------------------------------------------------------
-- 5. ตาราง progress (ความคืบหน้าการเรียน: M:N ระหว่าง learner x lesson)
-- ----------------------------------------------------------
CREATE TABLE progress (
    progress_id INT AUTO_INCREMENT PRIMARY KEY,
    learner_id INT NOT NULL COMMENT 'รหัสผู้เรียน',
    lesson_id INT NOT NULL COMMENT 'รหัสบทเรียน',
    status ENUM('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED') NOT NULL DEFAULT 'NOT_STARTED' COMMENT 'สถานะการเรียนในบทเรียนนี้',
    last_accessed DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'เวลาที่เข้าดูล่าสุด',
    completed_at DATETIME NULL COMMENT 'เวลาที่เรียนบทนี้เสร็จสมบูรณ์',
    CONSTRAINT fk_progress_learner 
        FOREIGN KEY (learner_id) 
        REFERENCES learner(learner_id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    CONSTRAINT fk_progress_lesson 
        FOREIGN KEY (lesson_id) 
        REFERENCES lesson(lesson_id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    CONSTRAINT uq_learner_lesson UNIQUE (learner_id, lesson_id)
) ENGINE=InnoDB COMMENT='ตารางบันทึกความคืบหน้าการเรียนแต่ละบทเรียนของผู้เรียน';

-- ==========================================================
-- ข้อมูลตัวอย่างสมมติ (Mock Data) อย่างน้อยตารางละ 10 แถว
-- ==========================================================

-- 1. Insert ข้อมูลตัวอย่างตาราง learner (10 แถว)
INSERT INTO learner (learner_id, first_name, last_name, email, phone, registered_at) VALUES
(1, 'สมชาย', 'ใจดี', 'somchai.j@gmail.com', '0812345678', '2025-01-10 09:00:00'),
(2, 'สมศักดิ์', 'รักเรียน', 'somsak.r@gmail.com', '0823456789', '2025-01-11 10:30:00'),
(3, 'วิชัย', 'เก่งกาจ', 'wichai.k@hotmail.com', '0834567890', '2025-01-12 14:15:00'),
(4, 'กัญญา', 'มีสุข', 'kanya.m@outlook.com', '0845678901', '2025-01-15 11:00:00'),
(5, 'อนงค์', 'พากเพียร', 'anong.p@yahoo.com', '0856789012', '2025-01-18 16:45:00'),
(6, 'ณัฐพล', 'ทองคำ', 'natthaphon.t@gmail.com', '0867890123', '2025-01-20 08:20:00'),
(7, 'สุภาพร', 'สว่างไสว', 'supaporn.s@gmail.com', '0878901234', '2025-01-22 13:50:00'),
(8, 'ธนวัฒน์', 'รุ่งเรือง', 'thanawat.r@hotmail.com', '0889012345', '2025-01-25 15:10:00'),
(9, 'พัชรี', 'ศิริผล', 'patcharee.s@gmail.com', '0890123456', '2025-01-28 17:30:00'),
(10, 'กิตติศักดิ์', 'เจริญสุข', 'kittisak.c@gmail.com', '0801234567', '2025-02-01 10:00:00');

-- 2. Insert ข้อมูลตัวอย่างตาราง course (10 แถว พร้อมสายสัมพันธ์ Prerequisite Self-reference)
-- หมายเหตุ: คอร์สพื้นฐานจะไม่มี Prerequisite (NULL), คอร์สระดับกลาง/สูงจะระบุวิชาบังคับก่อน
INSERT INTO course (course_id, course_code, title, description, price, level, prerequisite_course_id, created_at) VALUES
(1, 'CS101', 'Python Programming พื้นฐาน', 'ปูพื้นฐานการเขียนโปรแกรมด้วยภาษา Python ตั้งแต่ตัวแปร เงื่อนไข จนถึงฟังก์ชัน', 990.00, 'Beginner', NULL, '2024-12-01 10:00:00'),
(2, 'CS102', 'Data Structures & Algorithms ด้วย Python', 'โครงสร้างข้อมูลและอัลกอริทึม การวิเคราะห์ Big O, List, Stack, Queue, Tree', 1590.00, 'Intermediate', 1, '2024-12-05 10:00:00'),
(3, 'CS103', 'Web Development ด้วย Flask และ MySQL', 'สร้างเว็บแอปพลิเคชัน Dynamic ด้วย Python Flask เชื่อมต่อฐานข้อมูลเชิงสัมพันธ์', 1490.00, 'Intermediate', 1, '2024-12-10 10:00:00'),
(4, 'CS104', 'Machine Learning สำหรับผู้เริ่มต้น', 'เรียนรู้แบบจำลองการทำนาย Regression, Classification ด้วย Scikit-Learn', 2290.00, 'Advanced', 2, '2024-12-15 10:00:00'),
(5, 'CS105', 'HTML5, CSS3 และ JavaScript พื้นฐาน', 'พื้นฐานการทำเว็บหน้าบ้าน ออกแบบเว็บรองรับมือถือด้วย Responsive Design', 890.00, 'Beginner', NULL, '2024-12-18 10:00:00'),
(6, 'CS106', 'Frontend Development ด้วย React.js', 'การสร้าง Single Page Application จัดการ State และ Component ด้วย React', 1890.00, 'Intermediate', 5, '2024-12-20 10:00:00'),
(7, 'CS107', 'Full Stack Modern Web Application', 'รวมพลัง React Frontend และ REST API Backend สู่ระบบพร้อมใช้งานจริง', 2990.00, 'Advanced', 6, '2024-12-25 10:00:00'),
(8, 'CS108', 'การออกแบบและบริหารฐานข้อมูล SQL เบื้องต้น', 'การออกแบบ ER Diagram, Normalization, DDL และการเขียนคำสั่ง DML', 1190.00, 'Beginner', NULL, '2025-01-02 10:00:00'),
(9, 'CS109', 'Data Analytics ด้วย SQL และ Pandas', 'การวิเคราะห์ข้อมูลและสร้างรายงานเชิงลึกสำหรับนักวิเคราะห์ข้อมูล', 1790.00, 'Intermediate', 8, '2025-01-05 10:00:00'),
(10, 'CS110', 'Deep Learning & Computer Vision', 'โครงข่ายประสาทเทียม CNN และการประมวลผลรูปภาพขั้นสูงด้วย PyTorch', 3490.00, 'Advanced', 4, '2025-01-10 10:00:00');

-- 3. Insert ข้อมูลตัวอย่างตาราง lesson (12 แถว)
INSERT INTO lesson (lesson_id, course_id, title, lesson_order, duration_minutes, video_url) VALUES
(1, 1, 'แนะนำภาษา Python และการติดตั้งโปรแกรม', 1, 15, 'https://cdn.course.local/cs101/lesson1.mp4'),
(2, 1, 'ตัวแปร ชนิดข้อมูล และตัวดำเนินการ', 2, 25, 'https://cdn.course.local/cs101/lesson2.mp4'),
(3, 1, 'การควบคุมทิศทาง: เงื่อนไขและการวนซ้ำ', 3, 30, 'https://cdn.course.local/cs101/lesson3.mp4'),
(4, 2, 'การวิเคราะห์ความซับซ้อน (Big O Notation)', 1, 20, 'https://cdn.course.local/cs102/lesson1.mp4'),
(5, 2, 'Array, Linked List และการประยุกต์ใช้งาน', 2, 35, 'https://cdn.course.local/cs102/lesson2.mp4'),
(6, 3, 'เริ่มต้นทำเว็บด้วย Flask Routing & Templates', 1, 30, 'https://cdn.course.local/cs103/lesson1.mp4'),
(7, 3, 'การเชื่อมต่อ MySQL ด้วย Connector และ CRUD', 2, 45, 'https://cdn.course.local/cs103/lesson2.mp4'),
(8, 4, 'ภาพรวมและแนวคิด Machine Learning', 1, 25, 'https://cdn.course.local/cs104/lesson1.mp4'),
(9, 5, 'โครงสร้าง HTML5 และ Semantic Tags', 1, 20, 'https://cdn.course.local/cs105/lesson1.mp4'),
(10, 5, 'จัดสไตล์หน้าเว็บด้วย Modern CSS', 2, 30, 'https://cdn.course.local/cs105/lesson2.mp4'),
(11, 8, 'พื้นฐานฐานข้อมูลเชิงสัมพันธ์และโมเดลข้อมูล', 1, 25, 'https://cdn.course.local/cs108/lesson1.mp4'),
(12, 8, 'คำสั่ง SELECT และการ JOIN ตาราง', 2, 40, 'https://cdn.course.local/cs108/lesson2.mp4');

-- 4. Insert ข้อมูลตัวอย่างตาราง enrollment (16 แถว)
-- หลากหลายสถานะ: COMPLETED, IN_PROGRESS, ENROLLED, DROPPED เพื่อนำไปคำนวณอัตราการเรียนจบ
INSERT INTO enrollment (enrollment_id, learner_id, course_id, enrollment_date, status, completion_date, payment_method, amount_paid) VALUES
(1, 1, 1, '2025-01-10 10:00:00', 'COMPLETED', '2025-01-20 18:00:00', 'PromptPay', 990.00),
(2, 1, 2, '2025-01-21 09:00:00', 'IN_PROGRESS', NULL, 'TrueMoney Wallet', 1590.00),
(3, 2, 1, '2025-01-12 11:30:00', 'COMPLETED', '2025-01-25 15:00:00', 'Mastercard', 990.00),
(4, 2, 3, '2025-01-26 14:00:00', 'COMPLETED', '2025-02-10 17:30:00', 'บัตรทรูมันนี่', 1490.00),
(5, 3, 1, '2025-01-15 08:00:00', 'COMPLETED', '2025-01-30 12:00:00', 'PromptPay', 990.00),
(6, 3, 2, '2025-02-01 10:00:00', 'COMPLETED', '2025-02-15 19:00:00', 'TrueMoney Wallet', 1590.00),
(7, 3, 4, '2025-02-16 13:00:00', 'IN_PROGRESS', NULL, 'Mastercard', 2290.00),
(8, 4, 1, '2025-01-16 13:00:00', 'DROPPED', NULL, 'PromptPay', 990.00),
(9, 4, 5, '2025-01-18 10:00:00', 'COMPLETED', '2025-01-28 16:00:00', 'บัตรทรูมันนี่', 890.00),
(10, 5, 5, '2025-01-19 14:00:00', 'IN_PROGRESS', NULL, 'PromptPay', 890.00),
(11, 5, 8, '2025-01-20 16:30:00', 'COMPLETED', '2025-02-05 11:00:00', 'TrueMoney Wallet', 1190.00),
(12, 6, 8, '2025-01-22 09:15:00', 'COMPLETED', '2025-02-08 14:20:00', 'Mastercard', 1190.00),
(13, 6, 9, '2025-02-09 10:00:00', 'IN_PROGRESS', NULL, 'PromptPay', 1790.00),
(14, 7, 1, '2025-01-25 10:00:00', 'ENROLLED', NULL, 'TrueMoney Wallet', 990.00),
(15, 8, 3, '2025-01-28 11:00:00', 'IN_PROGRESS', NULL, 'Mastercard', 1490.00),
(16, 9, 8, '2025-02-01 15:45:00', 'DROPPED', NULL, 'บัตรทรูมันนี่', 1190.00);

-- 5. Insert ข้อมูลตัวอย่างตาราง progress (14 แถว)
INSERT INTO progress (progress_id, learner_id, lesson_id, status, last_accessed, completed_at) VALUES
(1, 1, 1, 'COMPLETED', '2025-01-12 11:00:00', '2025-01-12 11:15:00'),
(2, 1, 2, 'COMPLETED', '2025-01-15 14:30:00', '2025-01-15 14:55:00'),
(3, 1, 3, 'COMPLETED', '2025-01-20 17:40:00', '2025-01-20 18:00:00'),
(4, 1, 4, 'COMPLETED', '2025-01-22 10:00:00', '2025-01-22 10:20:00'),
(5, 1, 5, 'IN_PROGRESS', '2025-01-25 16:00:00', NULL),
(6, 2, 1, 'COMPLETED', '2025-01-14 13:00:00', '2025-01-14 13:20:00'),
(7, 2, 2, 'COMPLETED', '2025-01-18 15:00:00', '2025-01-18 15:30:00'),
(8, 2, 3, 'COMPLETED', '2025-01-25 14:40:00', '2025-01-25 15:00:00'),
(9, 2, 6, 'COMPLETED', '2025-02-01 11:00:00', '2025-02-01 11:30:00'),
(10, 2, 7, 'COMPLETED', '2025-02-10 17:00:00', '2025-02-10 17:30:00'),
(11, 4, 9, 'COMPLETED', '2025-01-20 11:00:00', '2025-01-20 11:20:00'),
(12, 4, 10, 'COMPLETED', '2025-01-28 15:40:00', '2025-01-28 16:00:00'),
(13, 5, 11, 'COMPLETED', '2025-01-25 16:00:00', '2025-01-25 16:30:00'),
(14, 5, 12, 'COMPLETED', '2025-02-05 10:30:00', '2025-02-05 11:00:00');