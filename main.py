import os
import re
from datetime import datetime

# ✅ MySQL fix for Railway/Linux
import pymysql
pymysql.install_as_MySQLdb()

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dotenv import load_dotenv
import PyPDF2
import docx
import markdown

from PIL import Image
try:
    import pytesseract
except Exception:
    pytesseract = None  # Railway-safe fallback

from openai import OpenAI
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "railway-secret-key")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)



def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def extract_text_from_docx(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_txt(txt_file):
    return txt_file.read().decode("utf-8")

def extract_text_from_image(img_file):
    image = Image.open(img_file)
    return pytesseract.image_to_string(image)

# @app.route("/base", methods=["GET", "POST"])
# def base():
#     response: str = ""
#     if request.method == 'POST':
#         user_input = request.form["user_input"]
#         completion = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "system", "content": "You are helpfull assistant"},
#                 {"role": "user", "content": user_input}
#                     ]
#         )
#         response = completion.choices[0].message.content
#         return render_template("base.html")
#################################DB Connectivity ##############################################app.config['MYSQL_HOST'] = os.getenv("MYSQL_HOST")app.config["MYSQL_HOST"] = os.getenv("MYSQL_HOST")
def get_db_connection():
    return pymysql.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),  # railway
        port=int(os.getenv("MYSQLPORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

import os
import pymysql
from dotenv import load_dotenv

load_dotenv()  # needed for local development ONLY

def get_db_connection():
    return pymysql.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        port=int(os.getenv("MYSQLPORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )
@app.route("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        return "✅ DB Connected Successfully"
    except Exception as e:
        return str(e)


@app.route('/',methods=['GET','POST'])
def index():
    response: str = ""
    if request.method == 'POST':
        print(request.form)
        user_input = request.form.get("user_input")  # ✅ avoids KeyError
        if user_input:  # only run if user actually typed something
            completion = client.chat.completions.create(
                model="gpt-4o-mini",  # cheaper, lighter model
                messages=[
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": user_input}
                ]
            )

            response = completion.choices[0].message.content

    return render_template('index.html',response=response)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/departments')
def departments():
    return render_template('departments.html')

@app.route('/doctors')
def doctors():
    return render_template('doctor/doctors.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

#--------------------Doctor Details----------------------------------------------------------#

@app.route('/doctor-register', methods=['GET', 'POST'])
def doctor_register():
    if request.method == 'POST':
        # Get form data
        fullname = request.form['fullname']
        email = request.form['email']
        phone = request.form['phone']
        specialization = request.form['specialization']
        qualification = request.form['qualification']
        experience = request.form['experience']
        password = generate_password_hash(request.form['password'])
        license_number = request.form['license']
        # ✅ Normalize specialization (this is the new part)
        specialization_raw = specialization.strip().title()

        specialization_map = {
            'General Physician': 'General Physician',
            'Physician': 'General Physician',
            'General Medicine': 'General Physician',

            'Cardiologist': 'Cardiology',
            'Cardiology': 'Cardiology',
            'Heart Specialist': 'Cardiology',

            'Dermatologist': 'Dermatology',
            'Dermatology': 'Dermatology',
            'Skin Specialist': 'Dermatology',

            'Neurologist': 'Neurology',
            'Neurology': 'Neurology',
            'Brain Specialist': 'Neurology',

            'Orthopedics': 'Orthopedic',
            'Orthopedist': 'Orthopedics',
            'Orthopaedic': 'Orthopedics',
            'Orthopaedics': 'Orthopedics',
            'Ortho': 'Orthopedics',
            'Bone Specialist': 'Orthopedics',
            'Orthopedics': 'Orthopedics',

            'Pediatrician': 'Pediatrics',
            'Pediatrics': 'Pediatrics',
            'Child Specialist': 'Pediatrics',

            'Gynecologist': 'Gynecology',
            'Gynaecologist': 'Gynecology',
            'Obstetrician': 'Obstetrics',
            'Gynecology': 'Gynecology',
            'Obstetrics': 'Obstetrics',

            'Pulmonologist': 'Pulmonology',
            'Pulmonology': 'Pulmonology',
            'Respiratory': 'Pulmonology',
            'Lungs Specialist': 'Pulmonology',
            'Respiratory Infection': 'Pulmonology',

            'Urologist': 'Urology',
            'Urology': 'Urology',
            'Nephrologist': 'Nephrology',
            'Nephrology': 'Nephrology',
            'Kidney Specialist': 'Nephrology',

            'Gastroenterologist': 'Gastroenterology',
            'Gastroenterology': 'Gastroenterology',
            'Digestive System Specialist': 'Gastroenterology',

            'Endocrinologist': 'Endocrinology',
            'Endocrinology': 'Endocrinology',
            'Diabetes Specialist': 'Endocrinology',

            'Ophthalmologist': 'Ophthalmology',
            'Eye Specialist': 'Ophthalmology',
            'Ophthalmology': 'Ophthalmology',

            'Ent': 'ENT',
            'Otolaryngologist': 'ENT',
            'Ear Nose Throat': 'ENT',
            'ENT': 'ENT',

            'Oncologist': 'Oncology',
            'Oncology': 'Oncology',
            'Cancer Specialist': 'Oncology',

            'Psychiatrist': 'Psychiatry',
            'Psychologist': 'Psychiatry',
            'Mental Health Specialist': 'Psychiatry',
            'Psychiatry': 'Psychiatry',

            'Hematologist': 'Hematology',
            'Hematology': 'Hematology',
            'Blood Specialist': 'Hematology',

            'Rheumatologist': 'Rheumatology',
            'Rheumatology': 'Rheumatology',
            'Arthritis Specialist': 'Rheumatology',

            'Infectious Disease': 'Infectious Disease',
            'Infectious Diseases': 'Infectious Disease',
            'Infection Specialist': 'Infectious Disease',

            'Allergist': 'Allergy & Immunology',
            'Immunologist': 'Allergy & Immunology',
            'Allergy': 'Allergy & Immunology',
            'Allergy & Immunology': 'Allergy & Immunology',

            'Radiologist': 'Radiology',
            'Pathologist': 'Pathology',
            'Anesthesiologist': 'Anesthesiology',
            'Anesthesia': 'Anesthesiology',

            'Surgeon': 'Surgery',
            'General Surgeon': 'Surgery',
            'Plastic Surgeon': 'Plastic Surgery',
            'Vascular Surgeon': 'Vascular Surgery',
            'Cardiothoracic Surgeon': 'Cardiothoracic Surgery',
            'Neurosurgeon': 'Neurosurgery',

            'Dentist': 'Dentistry',
            'Dental': 'Dentistry',

            'Sports Medicine Specialist': 'Sports Medicine',
            'Sports Medicine': 'Sports Medicine',

            'Critical Care': 'Critical Care',
            'Emergency Medicine': 'Emergency Medicine',
            'ICU Specialist': 'Critical Care'
        }

        specialization = specialization_map.get(specialization_raw, specialization_raw)
        # Handle file uploads
        profile_photo = request.files['profilePhoto']
        license_photo = request.files['licensePhoto']

        profile_filename = secure_filename(profile_photo.filename)
        license_filename = secure_filename(license_photo.filename)

        profile_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], profile_filename))
        license_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], license_filename))

        # Insert into DB
        conn = get_db_connection()
        cur = conn.cursor()
       try:
            cur.execute("""
                INSERT INTO doctors 
                (fullname, email, phone, specialization, qualification, experience, password, profile_photo, license_number, license_photo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (fullname, email, phone, specialization, qualification, experience, password, profile_filename,
                  license_number, license_filename))

            mysql.connection.commit()
            cur.close()
            flash("Doctor registered successfully!", "success")
            return redirect(url_for('success_doctor'))
        except Exception as e:
            mysql.connection.rollback()
            cur.close()
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('doctor_register'))

    return render_template('doctor/doctor-register.html')

@app.route('/success_doctor', methods=['GET', 'POST'])
def success_doctor():
    return render_template('doctor/success_doctor.html')

@app.route('/doctor-login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        print("1")
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM doctors WHERE email = %s", (email,))
        doctor = cur.fetchone()
        cur.close()
        conn.close()

        print("2")

        if doctor is None or not check_password_hash(doctor['password'], password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for('doctor_login'))
        print("3")
        print("Doctor Email : ",doctor['email'])
        session['doctor_email'] = doctor['email']
        session['doc_id'] = doctor['doc_id']
        session['specialization'] = doctor['specialization']
        print("4")
        flash("Login successful!", "success")
        print("✅ Session after login:", dict(session))
        return redirect(url_for('doctor_dashboard'))

    return render_template('doctor/doctor-login.html')

@app.route('/doctor-dashboard', methods=['POST', 'GET'])
def doctor_dashboard():
    if 'doctor_email' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('doctor_login'))

    # 🔹 Fetch logged-in doctor details
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM doctors WHERE email = %s", (session['doctor_email'],))
    doctor = cur.fetchone()
    cur.close()

    # 🔹 Fetch only pending patients related to this doctor (specialization or assigned)
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT sa.*, p.fullname, p.gender, p.age
        FROM symptoms_application sa
        JOIN patients p ON sa.patient_id = p.id
        WHERE ((sa.disease_category = %s) OR (sa.doc_id = %s))
          AND LOWER(sa.status) = 'pending'
        ORDER BY sa.created_at DESC
    """, (doctor['specialization'], doctor['doc_id']))
    pending_patients = cur.fetchall()
    cur.close()

    # ✅ Render only pending patients to the dashboard
    return render_template(
        'doctor/doctor-dashboard.html',
        doctor=doctor,
        pending_patients=pending_patients
    )


@app.route('/session-debug')
def session_debug():
    print("🔍 Current session keys:", session.keys())
    return str(dict(session))




@app.route("/view-doctor/<int:submission_id>", methods=['GET', 'POST'])
def view_doctor(submission_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT sa.*, p.fullname, p.age, p.gender, p.phone, p.profile_image
        FROM symptoms_application sa
        JOIN patients p ON sa.patient_id = p.id
        WHERE sa.aid = %s
    """, (submission_id,))
    submission = cur.fetchone()
    cur.close()

    if not submission:
        return "Submission not found!"

    # ✅ Convert AI response to formatted HTML if available
    if submission.get('ai_response'):
        submission['ai_response_html'] = markdown.markdown(submission['ai_response'])
    else:
        submission['ai_response_html'] = None

    # ✅ Convert AI-recommended medicines to HTML (if available)
    if submission.get('ai_medicines'):
        submission['ai_medicines_html'] = markdown.markdown(submission['ai_medicines'])
    else:
        submission['ai_medicines_html'] = None

    return render_template("doctor/view-doctor.html", submission=submission, patient=submission)


@app.route('/submit-response', methods=['POST'])
def submit_response():
    if 'doc_id' not in session:
        flash("Session expired. Please log in again.", "danger")
        return redirect(url_for('doctor_login'))

    submission_id = request.form.get('submission_id')
    ai_response = request.form.get('ai_response', '').strip()
    doctor_response = request.form.get('doctor_response', '').strip()

    print("📩 Received submission_id:", submission_id)
    print("📩 Doctor Response:", doctor_response)
    print("📩 AI Response:", ai_response)

    if not submission_id or not doctor_response:
        flash("Invalid data. Please enter your response.", "danger")
        return redirect(url_for('check_symptoms'))

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            UPDATE symptoms_application
            SET ai_response = %s, doc_id = %s, status = 'replied'
            WHERE aid = %s
        """, (ai_response, session['doc_id'], submission_id))
        print("✅ Rows updated:", cur.rowcount)
        mysql.connection.commit()

        cur.execute("""
            INSERT INTO doctor_response (submission_id, doc_id, doctor_response)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE doctor_response = VALUES(doctor_response)
        """, (submission_id, session['doc_id'], doctor_response))
        mysql.connection.commit()

        flash("Doctor response submitted successfully!", "success")
    except Exception as e:
        mysql.connection.rollback()
        print("❌ Error:", str(e))
        flash(f"Error saving response: {str(e)}", "danger")
    finally:
        cur.close()

    return redirect(url_for('check_symptoms'))


@app.route('/prescription/<int:symptom_id>')
def view_prescription(symptom_id):
    if 'patient_email' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('patient_login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT 
            sa.aid AS symptom_id,
            sa.symptoms,
            sa.status,
            sa.created_at,
            d.fullname AS doctor_name,
            dr.doctor_response AS prescription_text,
            dr.created_at AS prescription_date
        FROM symptoms_application sa
        LEFT JOIN doctor_response dr ON sa.aid = dr.submission_id
        LEFT JOIN doctors d ON dr.doc_id = d.doc_id
        WHERE sa.aid = %s
    """, (symptom_id,))
    data = cur.fetchone()
    cur.close()

    if not data:
        flash("No details found for this symptom.", "warning")
        return redirect(url_for('prescription_list'))

    return render_template('prescription.html', data=data)

@app.route('/medical-records', methods=['GET', 'POST'])
def medical_records():
    if 'patient_email' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('patient_login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch patient details
    cur.execute("SELECT * FROM patients WHERE email = %s", (session['patient_email'],))
    patient = cur.fetchone()

    if not patient:
        flash("Patient record not found!", "error")
        return redirect(url_for('patient_login'))

    # Handle file upload
    if request.method == 'POST':
        title = request.form.get('title')
        file = request.files.get('file')

        if file and file.filename:
            filename = file.filename
            filepath = os.path.join('static/uploads', filename)
            file.save(filepath)

            # Insert uploaded record into symptoms_application table
            cur.execute("""
                INSERT INTO symptoms_application (patient_id, symptoms, filename, status)
                VALUES (%s, %s, %s, %s)
            """, (patient['id'], title, filename, 'Uploaded'))
            mysql.connection.commit()
            flash('File uploaded successfully!', 'success')
            return redirect(url_for('medical_records'))

    # Fetch uploaded records from symptoms_application table
    cur.execute("""
        SELECT aid, symptoms, filename, ai_response, created_at, status
        FROM symptoms_application
        WHERE patient_id = %s
        ORDER BY created_at DESC
    """, (patient['id'],))
    uploaded_files = cur.fetchall()

    cur.close()

    return render_template('patient/medical-records.html',patient=patient,uploaded_files=uploaded_files)


@app.route('/prescription-list')
def prescription_list():
    if 'patient_email' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('patient_login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT id FROM patients WHERE email = %s", (session['patient_email'],))
    patient = cur.fetchone()
    if not patient:
        cur.close()
        flash("Patient not found.", "error")
        return redirect(url_for('patient_login'))

    cur.execute("""
        SELECT 
            sa.aid AS symptom_id,
            sa.symptoms,
            COALESCE(dr.doctor_response, 'Pending') AS prescription_text,
            COALESCE(dr.created_at, sa.created_at) AS prescription_date,
            COALESCE(d.fullname, 'Awaiting Doctor') AS doctor_name
        FROM symptoms_application sa
        LEFT JOIN doctor_response dr ON dr.submission_id = sa.aid
        LEFT JOIN doctors d ON dr.doc_id = d.doc_id
        WHERE sa.patient_id = %s
        ORDER BY sa.created_at DESC
    """, (patient['id'],))

    prescriptions = cur.fetchall()
    cur.close()

    return render_template('prescription_list.html', prescriptions=prescriptions)


@app.route('/prescription')
def prescription_page():
    if 'patient_email' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('patient_login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get logged-in patient's ID
    cur.execute("SELECT id FROM patients WHERE email = %s", (session['patient_email'],))
    patient = cur.fetchone()

    if not patient:
        cur.close()
        flash("Patient not found.", "error")
        return redirect(url_for('patient_login'))

    # Fetch all prescriptions for this patient
    cur.execute("""
        SELECT 
            dr.created_at AS date,
            d.fullname AS doctor_name,
            sa.symptoms,
            dr.doctor_response AS prescription
        FROM doctor_response dr
        JOIN doctors d ON d.doc_id = dr.doc_id
        JOIN symptoms_application sa ON sa.aid = dr.submission_id
        WHERE sa.patient_id = %s
        ORDER BY dr.created_at DESC
    """, (patient['id'],))

    prescriptions = cur.fetchall()
    cur.close()

    # Render the template you're actually using
    return render_template('prescription.html', prescriptions=prescriptions)


@app.route('/patient-dashboard', methods=['GET','POST'])
def patient_dashboard_page():
    if 'patient_email' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('patient_login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # ✅ Get logged-in patient details
    cur.execute("SELECT * FROM patients WHERE email = %s", (session['patient_email'],))
    patient = cur.fetchone()
    if not patient:
        cur.close()
        flash("Patient not found.", "error")
        return redirect(url_for('patient_login'))

    patient_id = patient['id']

    # ✅ Fetch symptoms submissions for this patient
    cur.execute("""
        SELECT 
            sa.aid,
            sa.symptoms,
            sa.created_at,
            sa.status,
            d.fullname AS doctor_name
        FROM symptoms_application sa
        LEFT JOIN doctor_response dr ON sa.aid = dr.submission_id
        LEFT JOIN doctors d ON dr.doc_id = d.doc_id
        WHERE sa.patient_id = %s
        ORDER BY sa.created_at DESC
    """, (patient_id,))
    submissions = cur.fetchall()

    # ✅ Fetch prescriptions for this patient
    cur.execute("""
        SELECT 
            dr.doc_id,
            dr.created_at AS date,
            d.fullname AS doctor_name,
            dr.doctor_response AS prescription
        FROM doctor_response dr
        JOIN doctors d ON d.doc_id = dr.doc_id
        WHERE dr.submission_id IN (
            SELECT aid FROM symptoms_application WHERE patient_id = %s
        )
        ORDER BY dr.created_at DESC
    """, (patient_id,))
    prescriptions = cur.fetchall()

    cur.close()

    return render_template(
        'patient/patient-dashboard.html',
        patient=patient,
        submissions=submissions,
        prescriptions=prescriptions
    )

@app.context_processor
def inject_doctor():
    doctor = None
    if 'doctor_email' in session:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM doctors WHERE email = %s", (session['doctor_email'],))
        doctor = cur.fetchone()
        cur.close()
    return dict(doctor=doctor)

@app.route('/check-symptoms')
def check_symptoms():
    """
    Shows symptom submissions relevant to the logged-in doctor's specialization,
    along with the actual doctor reply text and status.
    """
    if 'doctor_email' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('doctor_login'))

    # 1️⃣ Get logged-in doctor's specialization and ID
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT specialization, doc_id FROM doctors WHERE email = %s", (session['doctor_email'],))
    doctor = cur.fetchone()
    cur.close()

    if not doctor:
        flash("Doctor record not found.", "danger")
        return redirect(url_for('doctor_login'))

    # 2️⃣ Fetch submissions + doctor reply
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT 
            sa.aid, sa.patient_id, sa.symptoms, sa.filename, sa.ai_response, sa.created_at,
            p.fullname, p.email, p.phone,
            dr.doctor_response, dr.created_at AS doctor_reply_date
        FROM symptoms_application sa
        JOIN patients p ON sa.patient_id = p.id
        LEFT JOIN doctor_response dr ON sa.aid = dr.submission_id
        WHERE sa.disease_category = %s OR sa.doc_id = %s
        ORDER BY sa.created_at DESC
    """, (doctor['specialization'], doctor['doc_id']))
    submissions = cur.fetchall()
    cur.close()

    # 3️⃣ Format responses + auto set status
    for s in submissions:
        s['ai_response_html'] = markdown.markdown(s['ai_response']) if s['ai_response'] else None

        # Auto assign status
        if s['doctor_response']:
            s['status'] = "✅ Replied"
        else:
            s['status'] = "⏳ Awaiting Reply"

    # 4️⃣ Render
    return render_template('doctor/check-symptoms.html', submissions=submissions)


@app.route('/doctor-profile')
def doctor_profile():
    if 'doctor_email' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('doctor_login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM doctors WHERE email = %s", (session['doctor_email'],))
    doctor = cur.fetchone()
    cur.close()

    return render_template('doctor/doctor-profile.html', doctor=doctor)

@app.route('/update-doctor-profile', methods=['POST'])
def update_doctor_profile():
    if 'doctor_email' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('doctor_login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    fullname = request.form['fullname']
    phone = request.form['phone']
    specialization = request.form['specialization']
    experience = request.form['experience']

    # Handle optional profile photo upload
    profile_photo = None
    if 'profile_photo' in request.files:
        file = request.files['profile_photo']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.static_folder, 'uploads', filename)
            file.save(filepath)
            profile_photo = filename

    if profile_photo:
        cur.execute("""
            UPDATE doctors
            SET fullname=%s, phone=%s, specialization=%s, experience=%s,profile_photo=%s
            WHERE email=%s
        """, (fullname, phone, specialization, experience,profile_photo, session['doctor_email']))
    else:
        cur.execute("""
            UPDATE doctors
            SET fullname=%s, phone=%s, specialization=%s, experience=%s 
            WHERE email=%s
        """, (fullname, phone, specialization, experience, session['doctor_email']))

    mysql.connection.commit()
    cur.close()

    flash("Profile updated successfully!", "success")
    return redirect(url_for('doctor_profile'))


@app.route('/patient-profile')
def patient_profile():
    if 'patient_email' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('patient_login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM patients WHERE email = %s", (session['patient_email'],))
    patient = cur.fetchone()
    cur.close()

    if not patient:
        flash("Patient not found!", "danger")
        return redirect(url_for('patient_dashboard_page'))

    return render_template('patient/patient-profile.html', patient=patient)

@app.route('/update-patient-profile', methods=['POST'])
def update_patient_profile():
    if 'patient_email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})

    email = session['patient_email']
    fullname = request.form['fullname']
    phone = request.form['phone']
    gender = request.form['gender']
    age = request.form['age']
    address = request.form['address']
    medical_history = request.form['medical_history']

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE patients
        SET fullname=%s, phone=%s, gender=%s, age=%s, address=%s, medical_history=%s
        WHERE email=%s
    """, (fullname, phone, gender, age, address, medical_history, email))
    mysql.connection.commit()
    cur.close()

    return jsonify({'success': True})

@app.route('/report', methods=['GET'])
def report():
    """Doctor report page with filters by name, surname, or date"""
    if 'doctor_email' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('doctor_login'))

    #  Fetch doctor info
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT specialization, doc_id FROM doctors WHERE email = %s", (session['doctor_email'],))
    doctor = cur.fetchone()
    cur.close()

    if not doctor:
        flash("Doctor not found.", "danger")
        return redirect(url_for('doctor_login'))

    #  Read filters from the URL
    search = request.args.get('search', '').strip()
    date_filter = request.args.get('date', '').strip()

    # ✅ Build base query
    query = """
        SELECT 
            sa.aid,
            sa.symptoms,
            sa.filename,
            sa.created_at,
            p.fullname,
            p.email,
            p.phone,
            dr.doctor_response,
            dr.created_at AS doctor_reply_date,
            sa.ai_response
        FROM symptoms_application sa
        JOIN patients p ON sa.patient_id = p.id
        LEFT JOIN doctor_response dr ON sa.aid = dr.submission_id
        WHERE (sa.disease_category = %s OR sa.doc_id = %s)
    """
    params = [doctor['specialization'], doctor['doc_id']]

    # ✅ Apply search filter (by patient name or surname)
    if search:
        query += " AND (p.fullname LIKE %s)"
        params.append(f"%{search}%")

    # ✅ Apply date filter
    if date_filter:
        query += " AND DATE(sa.created_at) = %s"
        params.append(date_filter)

    query += " ORDER BY sa.created_at DESC"

    # ✅ Execute query
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute(query, params)
    submissions = cur.fetchall()
    cur.close()

    # ✅ Convert AI response to HTML
    for s in submissions:
        s['ai_response_html'] = markdown.markdown(s['ai_response']) if s['ai_response'] else None

    return render_template('doctor/report.html', submissions=submissions, search=search, date_filter=date_filter)


@app.route('/doctor-logout')
def doctor_logout():
    return render_template('doctor/doctor-logout.html')

#--------------------Patient Details----------------------------------------------------------#
@app.route('/patient-register',methods=['GET', 'POST'])
def patient_register():
    if request.method == 'POST':
        # Get form data
        fullname = request.form['fullname']
        email = request.form['email']
        phone = request.form['phone']
        gender = request.form['gender']
        age = request.form['age']
        address = request.form['address']
        medical_history = request.form['medicalHistory']
        password = generate_password_hash(request.form['password'])

        # Handle file upload (Profile Image)
        profile_image = request.files['profileImage']
        profile_filename = secure_filename(profile_image.filename)

        if profile_filename != "":
            profile_image.save(os.path.join(app.config['UPLOAD_FOLDER'], profile_filename))
        else:
            profile_filename = None  # If no file uploaded

        # Insert patient details into DB
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                   INSERT INTO patients 
                   (fullname, email, phone, gender, age, address, medical_history, password, profile_image)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               """, (fullname, email, phone, gender, age, address, medical_history, password, profile_filename))

            mysql.connection.commit()
            cur.close()
            flash("Patient registered successfully!", "success")
            return redirect(url_for('success_patient'))

        except Exception as e:
            mysql.connection.rollback()
            cur.close()
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('patient_register'))
    return render_template('patient/patient-register.html')

@app.route('/success_patient')
def success_patient():
    return render_template('patient/success_patient.html')

@app.route('/patient-login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM patients WHERE email = %s", (email,))
        patient = cur.fetchone()
        cur.close()

        if patient is None or not check_password_hash(patient['password'], password):
            flash("Incorrect email or password.", "error")
            return redirect(url_for('patient_login'))

        # Successful login
        session['patient_email'] = patient['email']
        flash("Login successful!", "success")
        return redirect('patient-dashboard')

    return render_template('patient/patient-login.html')

@app.route('/patient-logout')
def patient_logout():
    return render_template('patient/patient-logout.html')


@app.route('/upload-symptoms', methods=['GET', 'POST'])
def upload_symptoms():
    if 'patient_email' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('patient_login'))

    response_text = ""
    ai_medicines = None
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # fetch logged-in patient ID
    cur.execute("SELECT id FROM patients WHERE email = %s", (session['patient_email'],))
    patient = cur.fetchone()
    if not patient:
        flash("Patient not found.", "error")
        return redirect(url_for('patient_login'))
    patient_id = patient['id']

    # -------- Handle Form Submission --------
    if request.method == 'POST':
        user_text = request.form.get("user_input_text", "").strip()
        uploaded_file = request.files.get("user_input_file")
        filename = None
        file_text = ""

        # handle file upload and extraction
        if uploaded_file and uploaded_file.filename:
            filename = secure_filename(uploaded_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(file_path)

            if filename.lower().endswith('.pdf'):
                file_text = extract_text_from_pdf(open(file_path, 'rb'))
            elif filename.lower().endswith('.docx'):
                file_text = extract_text_from_docx(file_path)
            elif filename.lower().endswith('.txt'):
                file_text = extract_text_from_txt(open(file_path, 'rb'))
            elif filename.lower().endswith(('.jpg', '.png')):
                file_text = extract_text_from_image(file_path)

        final_text = (user_text + "\n" + file_text).strip()

        # ✅ generate AI response (medical analysis)
        if final_text:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system",
                     "content": "You are a helpful medical assistant. Analyze the symptoms and provide a clear medical analysis of the possible causes."},
                    {"role": "user", "content": final_text}
                ]
            )
            response_text = completion.choices[0].message.content.strip()

            # ✅ Ask AI for recommended medicines
            meds_completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system",
                     "content": (
                         "You are a professional medical assistant. Based on the symptoms provided, "
                         "suggest ONLY 3 to 4 possible medicine names (over-the-counter or commonly prescribed) "
                         "that may help with the given symptoms. "
                         "Do NOT include explanations, dosages, or home remedies. "
                         "Respond strictly in numbered list format like:\n"
                         "1. Medicine Name\n2. Medicine Name\n3. Medicine Name\n4. Medicine Name\n"
                         "If no medicine can be recommended, reply exactly: 'No medicine recommendation available'."
                     )},
                    {"role": "user",
                     "content": f"Patient symptoms: {final_text}. Suggest possible medicines or home remedies."}

                ]
            )
            ai_medicines = meds_completion.choices[0].message.content.strip()
            if ai_medicines.lower() in ("none", "no", "no medicine", "no medicines"):
                ai_medicines = None
            print("AI Genereated Medicine:",ai_medicines)

            # ✅ Ask AI to return only the specialization
            specialization_prompt = f"Based on the symptoms: '{final_text}', which doctor specialization is most suitable? Return only one word, like 'Dermatology', 'Cardiology', etc."
            specialization_completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a medical assistant who identifies doctor specializations."},
                    {"role": "user", "content": specialization_prompt}
                ]
            )
            raw_specialization = specialization_completion.choices[0].message.content.strip()

            # ✅ Normalize specialization (remove punctuation and capitalize)
            predicted_specialization = ' '.join(
                word.capitalize() for word in re.findall(r'[a-zA-Z]+', raw_specialization))
        else:
            response_text = ""
            ai_medicines = None
            predicted_specialization = "General Medicine"

        # ✅ Insert into database with ai_medicines column
        cur.execute("""
            INSERT INTO symptoms_application 
            (patient_id, symptoms, filename, ai_response, ai_medicines, status, disease_category)
            VALUES (%s, %s, %s, %s, %s, 'pending', %s)
        """, (patient_id, user_text, filename, response_text, ai_medicines, predicted_specialization))
        mysql.connection.commit()

        flash("Symptoms submitted successfully!", "success")
        return redirect(url_for('upload_symptoms'))  # reload page to show updated table

    # -------- Fetch All Submissions --------
    cur.execute("""
        SELECT aid, patient_id, symptoms, filename, created_at, status
        FROM symptoms_application
        WHERE patient_id = %s
        ORDER BY created_at DESC
    """, (patient_id,))
    submissions = cur.fetchall()
    cur.close()

    return render_template('patient/upload-symptoms.html', response=response_text, submissions=submissions)

    # -------- Fetch All Submissions --------
    cur.execute("""
        SELECT aid, patient_id, symptoms,filename, created_at, status
        FROM symptoms_application
        WHERE patient_id = %s
        ORDER BY created_at DESC
    """, (patient_id,))
    submissions = cur.fetchall()
    cur.close()

    return render_template('patient/upload-symptoms.html', response=response_text, submissions=submissions)

@app.route('/success-symptoms-submit', methods=['GET', 'POST'])
def success_symptoms_submit():
    patient_id = session.get('patient_id') or session.get('patient_email')
    if not patient_id:
        flash("Session expired or patient not logged in.")
        return redirect(url_for('patient_login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch all symptoms submissions for this patient
    cur.execute("""
        SELECT 
            s.aid,
            s.symptoms,
            s.created_at,
            s.status
        FROM symptoms_application s
        WHERE s.patient_id = %s
        ORDER BY s.created_at DESC
    """, (patient_id,))
    submissions = cur.fetchall()

    # Fetch all prescriptions for this patient (joining doctor_response -> symptoms_application -> doctors)
    cur.execute("""
        SELECT 
            dr.doctor_response AS prescription,
            dr.created_at AS date,
            d.fullname AS doctor_name
        FROM doctor_response dr
        JOIN symptoms_application s ON dr.submission_id = s.aid
        JOIN doctors d ON dr.doc_id = d.doc_id
        WHERE s.patient_id = %s
        ORDER BY dr.created_at DESC
    """, (patient_id,))
    prescriptions = cur.fetchall()

    cur.close()

    return render_template(
        "doctor/success-symptoms-submit.html",
        submissions=submissions,
        prescriptions=prescriptions
    )



@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot-password.html')

@app.context_processor
def inject_patient():
    patient = None
    if 'patient_email' in session:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM patients WHERE email = %s", (session['patient_email'],))
        patient = cur.fetchone()
        cur.close()
    return dict(patient=patient)

