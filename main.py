import os
import re
from datetime import datetime

# ✅ MySQL fix for Railway/Linux
import pymysql
pymysql.install_as_MySQLdb()

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

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


# =========================================================
# ENV + APP CONFIG
# =========================================================
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "railway-secret-key")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# DATABASE CONNECTION (SINGLE SOURCE – FIXED)
# =========================================================
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


# =========================================================
# FILE TEXT EXTRACTION HELPERS
# =========================================================
def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    return "\n".join([para.text for para in doc.paragraphs])


def extract_text_from_txt(txt_file):
    return txt_file.read().decode("utf-8")


def extract_text_from_image(image_path):
    if pytesseract:
        image = Image.open(image_path)
        return pytesseract.image_to_string(image)
    return ""


# =========================================================
# BASIC PAGES
# =========================================================
@app.route("/", methods=["GET", "POST"])
def index():
    response = ""
    if request.method == "POST":
        user_input = request.form.get("user_input")
        if user_input:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": user_input}
                ]
            )
            response = completion.choices[0].message.content

    return render_template("index.html", response=response)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/services")
def services():
    return render_template("services.html")


@app.route("/departments")
def departments():
    return render_template("departments.html")


@app.route("/doctors")
def doctors():
    return render_template("doctor/doctors.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


# =========================================================
# DB TEST ROUTE (KEEP)
# =========================================================
@app.route("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        conn.close()
        return "✅ DB Connected Successfully"
    except Exception as e:
        return str(e)
# =========================================================
# DOCTOR REGISTRATION
# =========================================================
@app.route("/doctor-register", methods=["GET", "POST"])
def doctor_register():
    if request.method == "POST":
        fullname = request.form["fullname"]
        email = request.form["email"]
        phone = request.form["phone"]
        specialization = request.form["specialization"]
        qualification = request.form["qualification"]
        experience = request.form["experience"]
        password = generate_password_hash(request.form["password"])
        license_number = request.form["license"]

        specialization_raw = specialization.strip().title()

        specialization_map = {
            "General Physician": "General Physician",
            "Physician": "General Physician",
            "General Medicine": "General Physician",
            "Cardiologist": "Cardiology",
            "Cardiology": "Cardiology",
            "Dermatologist": "Dermatology",
            "Dermatology": "Dermatology",
            "Neurologist": "Neurology",
            "Neurology": "Neurology",
            "Orthopedics": "Orthopedics",
            "Orthopedic": "Orthopedics",
            "Pediatrician": "Pediatrics",
            "Pediatrics": "Pediatrics",
            "Gynecologist": "Gynecology",
            "Gynecology": "Gynecology",
            "Pulmonologist": "Pulmonology",
            "Pulmonology": "Pulmonology",
            "Urologist": "Urology",
            "Urology": "Urology",
            "Gastroenterologist": "Gastroenterology",
            "Gastroenterology": "Gastroenterology",
            "Endocrinologist": "Endocrinology",
            "Endocrinology": "Endocrinology",
            "Ophthalmologist": "Ophthalmology",
            "Ophthalmology": "Ophthalmology",
            "ENT": "ENT",
            "Psychiatrist": "Psychiatry",
            "Psychiatry": "Psychiatry",
        }

        specialization = specialization_map.get(
            specialization_raw, specialization_raw
        )

        profile_photo = request.files["profilePhoto"]
        license_photo = request.files["licensePhoto"]

        profile_filename = secure_filename(profile_photo.filename)
        license_filename = secure_filename(license_photo.filename)

        profile_photo.save(
            os.path.join(app.config["UPLOAD_FOLDER"], profile_filename)
        )
        license_photo.save(
            os.path.join(app.config["UPLOAD_FOLDER"], license_filename)
        )

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO doctors
                (fullname, email, phone, specialization, qualification,
                 experience, password, profile_photo, license_number, license_photo)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    fullname,
                    email,
                    phone,
                    specialization,
                    qualification,
                    experience,
                    password,
                    profile_filename,
                    license_number,
                    license_filename,
                ),
            )
            conn.commit()
            flash("Doctor registered successfully!", "success")
            return redirect(url_for("success_doctor"))
        except Exception as e:
            conn.rollback()
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("doctor_register"))
        finally:
            cur.close()
            conn.close()

    return render_template("doctor/doctor-register.html")


@app.route("/success_doctor")
def success_doctor():
    return render_template("doctor/success_doctor.html")


# =========================================================
# DOCTOR LOGIN
# =========================================================
@app.route("/doctor-login", methods=["GET", "POST"])
def doctor_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM doctors WHERE email=%s", (email,))
        doctor = cur.fetchone()
        cur.close()
        conn.close()

        if not doctor or not check_password_hash(
            doctor["password"], password
        ):
            flash("Invalid email or password", "danger")
            return redirect(url_for("doctor_login"))

        session["doctor_email"] = doctor["email"]
        session["doc_id"] = doctor["doc_id"]
        session["specialization"] = doctor["specialization"]

        flash("Login successful!", "success")
        return redirect(url_for("doctor_dashboard"))

    return render_template("doctor/doctor-login.html")


# =========================================================
# DOCTOR DASHBOARD
# =========================================================
@app.route("/doctor-dashboard")
def doctor_dashboard():
    if "doctor_email" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("doctor_login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM doctors WHERE email=%s",
        (session["doctor_email"],),
    )
    doctor = cur.fetchone()

    cur.execute(
        """
        SELECT sa.*, p.fullname, p.gender, p.age
        FROM symptoms_application sa
        JOIN patients p ON sa.patient_id = p.id
        WHERE ((sa.disease_category=%s) OR (sa.doc_id=%s))
          AND LOWER(sa.status)='pending'
        ORDER BY sa.created_at DESC
        """,
        (doctor["specialization"], doctor["doc_id"]),
    )
    pending_patients = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "doctor/doctor-dashboard.html",
        doctor=doctor,
        pending_patients=pending_patients,
    )
# =========================================================
# SESSION DEBUG (KEEP)
# =========================================================
@app.route("/session-debug")
def session_debug():
    return str(dict(session))


# =========================================================
# VIEW DOCTOR SUBMISSION
# =========================================================
@app.route("/view-doctor/<int:submission_id>", methods=["GET", "POST"])
def view_doctor(submission_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT sa.*, p.fullname, p.age, p.gender, p.phone, p.profile_image
        FROM symptoms_application sa
        JOIN patients p ON sa.patient_id = p.id
        WHERE sa.aid=%s
        """,
        (submission_id,),
    )
    submission = cur.fetchone()
    cur.close()
    conn.close()

    if not submission:
        return "Submission not found!"

    submission["ai_response_html"] = (
        markdown.markdown(submission["ai_response"])
        if submission.get("ai_response")
        else None
    )

    submission["ai_medicines_html"] = (
        markdown.markdown(submission["ai_medicines"])
        if submission.get("ai_medicines")
        else None
    )

    return render_template(
        "doctor/view-doctor.html",
        submission=submission,
        patient=submission,
    )


# =========================================================
# SUBMIT DOCTOR RESPONSE
# =========================================================
@app.route("/submit-response", methods=["POST"])
def submit_response():
    if "doc_id" not in session:
        flash("Session expired. Please login again.", "danger")
        return redirect(url_for("doctor_login"))

    submission_id = request.form.get("submission_id")
    ai_response = request.form.get("ai_response", "").strip()
    doctor_response = request.form.get("doctor_response", "").strip()

    if not submission_id or not doctor_response:
        flash("Invalid data.", "danger")
        return redirect(url_for("check_symptoms"))

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            UPDATE symptoms_application
            SET ai_response=%s, doc_id=%s, status='replied'
            WHERE aid=%s
            """,
            (ai_response, session["doc_id"], submission_id),
        )

        cur.execute(
            """
            INSERT INTO doctor_response
            (submission_id, doc_id, doctor_response)
            VALUES (%s,%s,%s)
            ON DUPLICATE KEY UPDATE
            doctor_response=VALUES(doctor_response)
            """,
            (submission_id, session["doc_id"], doctor_response),
        )

        conn.commit()
        flash("Doctor response submitted successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("check_symptoms"))


# =========================================================
# PRESCRIPTION VIEW
# =========================================================
@app.route("/prescription/<int:symptom_id>")
def view_prescription(symptom_id):
    if "patient_email" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("patient_login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT 
            sa.aid AS symptom_id,
            sa.symptoms,
            sa.status,
            sa.created_at,
            d.fullname AS doctor_name,
            dr.doctor_response AS prescription_text,
            dr.created_at AS prescription_date
        FROM symptoms_application sa
        LEFT JOIN doctor_response dr ON sa.aid=dr.submission_id
        LEFT JOIN doctors d ON dr.doc_id=d.doc_id
        WHERE sa.aid=%s
        """,
        (symptom_id,),
    )
    data = cur.fetchone()
    cur.close()
    conn.close()

    if not data:
        flash("No prescription found.", "warning")
        return redirect(url_for("prescription_list"))

    return render_template("prescription.html", data=data)
# =========================================================
# MEDICAL RECORDS (PATIENT)
# =========================================================
@app.route("/medical-records", methods=["GET", "POST"])
def medical_records_page():
    if "patient_email" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("patient_login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM patients WHERE email=%s",
        (session["patient_email"],),
    )
    patient = cur.fetchone()

    if not patient:
        cur.close()
        conn.close()
        flash("Patient record not found!", "error")
        return redirect(url_for("patient_login"))

    if request.method == "POST":
        title = request.form.get("title")
        file = request.files.get("file")

        if file and file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            cur.execute(
                """
                INSERT INTO symptoms_application
                (patient_id, symptoms, filename, status)
                VALUES (%s,%s,%s,%s)
                """,
                (patient["id"], title, filename, "Uploaded"),
            )
            conn.commit()
            flash("File uploaded successfully!", "success")
            cur.close()
            conn.close()
            return redirect(url_for("medical_records"))

    cur.execute(
        """
        SELECT aid, symptoms, filename, ai_response, created_at, status
        FROM symptoms_application
        WHERE patient_id=%s
        ORDER BY created_at DESC
        """,
        (patient["id"],),
    )
    uploaded_files = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "patient/medical-records.html",
        patient=patient,
        uploaded_files=uploaded_files,
    )


# =========================================================
# PRESCRIPTION LIST
# =========================================================
@app.route("/prescription-list")
def prescription_list():
    if "patient_email" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("patient_login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM patients WHERE email=%s",
        (session["patient_email"],),
    )
    patient = cur.fetchone()

    if not patient:
        cur.close()
        conn.close()
        flash("Patient not found.", "error")
        return redirect(url_for("patient_login"))

    cur.execute(
        """
        SELECT 
            sa.aid AS symptom_id,
            sa.symptoms,
            COALESCE(dr.doctor_response, 'Pending') AS prescription_text,
            COALESCE(dr.created_at, sa.created_at) AS prescription_date,
            COALESCE(d.fullname, 'Awaiting Doctor') AS doctor_name
        FROM symptoms_application sa
        LEFT JOIN doctor_response dr ON dr.submission_id=sa.aid
        LEFT JOIN doctors d ON dr.doc_id=d.doc_id
        WHERE sa.patient_id=%s
        ORDER BY sa.created_at DESC
        """,
        (patient["id"],),
    )
    prescriptions = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "prescription_list.html",
        prescriptions=prescriptions,
    )


# =========================================================
# PATIENT DASHBOARD
# =========================================================
@app.route("/patient-dashboard", methods=["GET", "POST"])
def patient_dashboard_page():
    if "patient_email" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("patient_login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM patients WHERE email=%s",
        (session["patient_email"],),
    )
    patient = cur.fetchone()

    if not patient:
        cur.close()
        conn.close()
        flash("Patient not found.", "error")
        return redirect(url_for("patient_login"))

    patient_id = patient["id"]

    cur.execute(
        """
        SELECT 
            sa.aid,
            sa.symptoms,
            sa.created_at,
            sa.status,
            d.fullname AS doctor_name
        FROM symptoms_application sa
        LEFT JOIN doctor_response dr ON sa.aid=dr.submission_id
        LEFT JOIN doctors d ON dr.doc_id=d.doc_id
        WHERE sa.patient_id=%s
        ORDER BY sa.created_at DESC
        """,
        (patient_id,),
    )
    submissions = cur.fetchall()

    cur.execute(
        """
        SELECT 
            dr.doc_id,
            dr.created_at AS date,
            d.fullname AS doctor_name,
            dr.doctor_response AS prescription
        FROM doctor_response dr
        JOIN doctors d ON d.doc_id=dr.doc_id
        WHERE dr.submission_id IN (
            SELECT aid FROM symptoms_application WHERE patient_id=%s
        )
        ORDER BY dr.created_at DESC
        """,
        (patient_id,),
    )
    prescriptions = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "patient/patient-dashboard.html",
        patient=patient,
        submissions=submissions,
        prescriptions=prescriptions,
    )


# =========================================================
# CONTEXT PROCESSORS
# =========================================================
@app.context_processor
def inject_doctor():
    doctor = None
    if "doctor_email" in session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM doctors WHERE email=%s",
            (session["doctor_email"],),
        )
        doctor = cur.fetchone()
        cur.close()
        conn.close()
    return dict(doctor=doctor)
# =========================================================
# MEDICAL RECORDS (PATIENT)
# =========================================================
@app.route("/medical-records", methods=["GET", "POST"])
def medical_records():
    if "patient_email" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("patient_login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM patients WHERE email=%s",
        (session["patient_email"],),
    )
    patient = cur.fetchone()

    if not patient:
        cur.close()
        conn.close()
        flash("Patient record not found!", "error")
        return redirect(url_for("patient_login"))

    if request.method == "POST":
        title = request.form.get("title")
        file = request.files.get("file")

        if file and file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            cur.execute(
                """
                INSERT INTO symptoms_application
                (patient_id, symptoms, filename, status)
                VALUES (%s,%s,%s,%s)
                """,
                (patient["id"], title, filename, "Uploaded"),
            )
            conn.commit()
            flash("File uploaded successfully!", "success")
            cur.close()
            conn.close()
            return redirect(url_for("medical_records"))

    cur.execute(
        """
        SELECT aid, symptoms, filename, ai_response, created_at, status
        FROM symptoms_application
        WHERE patient_id=%s
        ORDER BY created_at DESC
        """,
        (patient["id"],),
    )
    uploaded_files = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "patient/medical-records.html",
        patient=patient,
        uploaded_files=uploaded_files,
    )


# =========================================================
# PRESCRIPTION LIST
# =========================================================
@app.route("/prescription-list")
def prescription_list():
    if "patient_email" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("patient_login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM patients WHERE email=%s",
        (session["patient_email"],),
    )
    patient = cur.fetchone()

    if not patient:
        cur.close()
        conn.close()
        flash("Patient not found.", "error")
        return redirect(url_for("patient_login"))

    cur.execute(
        """
        SELECT 
            sa.aid AS symptom_id,
            sa.symptoms,
            COALESCE(dr.doctor_response, 'Pending') AS prescription_text,
            COALESCE(dr.created_at, sa.created_at) AS prescription_date,
            COALESCE(d.fullname, 'Awaiting Doctor') AS doctor_name
        FROM symptoms_application sa
        LEFT JOIN doctor_response dr ON dr.submission_id=sa.aid
        LEFT JOIN doctors d ON dr.doc_id=d.doc_id
        WHERE sa.patient_id=%s
        ORDER BY sa.created_at DESC
        """,
        (patient["id"],),
    )
    prescriptions = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "prescription_list.html",
        prescriptions=prescriptions,
    )


# =========================================================
# PATIENT DASHBOARD
# =========================================================
@app.route("/patient-dashboard", methods=["GET", "POST"])
def patient_dashboard_page():
    if "patient_email" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("patient_login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM patients WHERE email=%s",
        (session["patient_email"],),
    )
    patient = cur.fetchone()

    if not patient:
        cur.close()
        conn.close()
        flash("Patient not found.", "error")
        return redirect(url_for("patient_login"))

    patient_id = patient["id"]

    cur.execute(
        """
        SELECT 
            sa.aid,
            sa.symptoms,
            sa.created_at,
            sa.status,
            d.fullname AS doctor_name
        FROM symptoms_application sa
        LEFT JOIN doctor_response dr ON sa.aid=dr.submission_id
        LEFT JOIN doctors d ON dr.doc_id=d.doc_id
        WHERE sa.patient_id=%s
        ORDER BY sa.created_at DESC
        """,
        (patient_id,),
    )
    submissions = cur.fetchall()

    cur.execute(
        """
        SELECT 
            dr.doc_id,
            dr.created_at AS date,
            d.fullname AS doctor_name,
            dr.doctor_response AS prescription
        FROM doctor_response dr
        JOIN doctors d ON d.doc_id=dr.doc_id
        WHERE dr.submission_id IN (
            SELECT aid FROM symptoms_application WHERE patient_id=%s
        )
        ORDER BY dr.created_at DESC
        """,
        (patient_id,),
    )
    prescriptions = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "patient/patient-dashboard.html",
        patient=patient,
        submissions=submissions,
        prescriptions=prescriptions,
    )


# =========================================================
# CONTEXT PROCESSORS
# =========================================================
@app.context_processor
def inject_doctor():
    doctor = None
    if "doctor_email" in session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM doctors WHERE email=%s",
            (session["doctor_email"],),
        )
        doctor = cur.fetchone()
        cur.close()
        conn.close()
    return dict(doctor=doctor)
