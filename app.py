import os
import cv2
import sqlite3
from flask import Flask, render_template, request, url_for
from datetime import datetime

# إنشاء تطبيق Flask وتحديد مجلد الملفات الثابتة
app = Flask(__name__, static_folder='static')

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

            return render_template('attendance.html', image_path=image_path, student_name=student_name)
        else:
            return "Error: Could not capture image."

    return render_template('attendance_form.html')

@app.route('/attendance-list')
def attendance_list():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT student_name, image_path, timestamp FROM attendance ORDER BY timestamp DESC")
    records = cursor.fetchall()
    conn.close()

    return render_template('attendance_list.html', records=records)

if __name__ == "__main__":
    import os

if __name__ == "__main__":
    if os.name == "nt":  # Windows
        from waitress import serve
        print("Running with Waitress on Windows...")
        serve(app, host="0.0.0.0", port=5000)
    else:  # Linux (للنشر على Render أو الخادم)
        print("Running with Gunicorn on Linux...")
        from gunicorn.app.wsgiapp import run
        run()

