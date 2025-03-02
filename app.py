import os
import cv2
import sqlite3
from flask import Flask, render_template, request
from datetime import datetime
from flask_mail import Mail, Message
from dotenv import load_dotenv

# تحميل بيانات .env
load_dotenv()

# إعدادات التطبيق
app = Flask(__name__, static_folder='static')

# إعدادات البريد الإلكتروني باستخدام Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.zoho.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # تحميل بيانات البريد من .env
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # تحميل بيانات البريد من .env
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')  # تعيين الإيميل كـ مرسل افتراضي
mail = Mail(app)

# مسار المجلد لحفظ الصور
IMAGE_FOLDER = "static/images"
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# اسم قاعدة البيانات
DB_FILE = "attendance.db"

# إنشاء قاعدة البيانات والجداول إذا لم تكن موجودة
def create_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            image_path TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_interactions (
            interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            activity_type TEXT,
            interaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            interaction_type TEXT,
            score INTEGER,
            FOREIGN KEY (student_id) REFERENCES attendance (id)
        )
    ''')

    conn.commit()
    conn.close()

# استدعاء الدالة لإنشاء قاعدة البيانات عند تشغيل التطبيق
create_database()

@app.route('/')
def home():
    return render_template('index.html')  # يعرض الصفحة الرئيسية

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if request.method == 'POST':
        student_name = request.form['student_name']

        # فتح الكاميرا والتقاط صورة
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return "Error: Could not open camera."

        ret, frame = cap.read()  
        cap.release()  # إغلاق الكاميرا بعد الالتقاط

        if ret:
            # تحسين جودة الصورة
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame = cv2.equalizeHist(frame)

            # إنشاء اسم فريد للصورة
            image_filename = f"{student_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            image_path = os.path.join(IMAGE_FOLDER, image_filename)

            # حفظ الصورة في المجلد
            cv2.imwrite(image_path, frame)

            # حفظ بيانات الحضور في قاعدة البيانات
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO attendance (student_name, image_path) VALUES (?, ?)",
                           (student_name, image_path))
            conn.commit()
            conn.close()

            # إرسال إشعار عبر البريد الإلكتروني (اختياري)
            send_email_notification(student_name, image_path)

            return render_template('attendance.html', image_path=image_path, student_name=student_name)
        else:
            return "Error: Could not capture image."

    return render_template('attendance_form.html')

# إرسال إشعار بالبريد الإلكتروني
def send_email_notification(student_name, image_path):
    msg = Message(f"Attendance Recorded for {student_name}",
                  sender=os.getenv('MAIL_USERNAME'),  # المرسل
                  recipients=['mga.4004497@gmail.com'])  # المستلم (ولي الأمر أو المعلم)
    msg.body = f"Attendance has been recorded for {student_name}. You can view the image at: {image_path}"
    mail.send(msg)

@app.route('/attendance-list')
def attendance_list():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT student_name, image_path, timestamp FROM attendance ORDER BY timestamp DESC")
    records = cursor.fetchall()
    conn.close()

    return render_template('attendance_list.html', records=records)

# إنشاء تقرير المعلم
@app.route('/teacher-report')
def teacher_report():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # استعلام SQL للحصول على تقرير الأداء للطلاب
    cursor.execute('''
        SELECT student_name, 
               COUNT(interaction_id) AS num_activities, 
               AVG(score) AS avg_score, 
               GROUP_CONCAT(DISTINCT activity_type) AS activity_types
        FROM student_interactions
        JOIN attendance ON attendance.id = student_interactions.student_id
        GROUP BY student_name
    ''')

    # جلب البيانات من الاستعلام
    report = cursor.fetchall()
    conn.close()

    # عرض التقرير في صفحة المعلم
    return render_template('teacher_report.html', report=report)

if __name__ == "__main__":
    import os

    if os.name == "nt":  # Windows
        from waitress import serve
        print("Running with Waitress on Windows...")
        serve(app, host="0.0.0.0", port=5000)
    else:  # Linux (للنشر على Render أو الخادم)
        print("Running with Gunicorn on Linux...")
        from gunicorn.app.wsgiapp import run
        run()
