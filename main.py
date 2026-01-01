import os
import re
from datetime import datetime

import pymysql
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from openai import OpenAI
import markdown

load_dotenv()

# ================== APP ==================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "railway-secret-key")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================== DB ==================
def get_db_connection():
    return pymysql.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),  # railway
        port=int(os.getenv("MYSQLPORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

# ================== ROUTES ==================

@app.route("/")
def index():
    return render_template("index.html")

# ---------- DOCTOR REGISTER ----------
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

        profile_photo = request.files["profilePhoto"]
        license_photo = request.files["licensePhoto"]

        profile_filename = secure_filename(profile_photo.filename)
        license_filename = secure_filename(license_photo.filename)

        profile_photo.save(os.path.join(app.config["UPLOAD_FOLDER"], profile_filename))
        license_photo.save(os.path.join(app.config["UPLOAD_FOLDER"], license_filename))

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO doctors
                (fullname,email,phone,specialization,qualification,experience,password,profile_photo,license_photo)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                fullname, email, phone, specialization,
                qualification, experience, password,
                profile_filename, license_filename
            ))
            conn.commit()
            flash("Doctor registered successfully", "success")
            return redirect(url_for("doctor_login"))
        except Exception as e:
            conn.rollback()
            flash(str(e), "danger")
        finally:
            cur.close()
            conn.close()

    return render_template("doctor/doctor-register.html")

# ---------- DOCTOR LOGIN ----------
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

        if not doctor or not check_password_hash(doctor["password"], password):
            flash("Invalid email or password", "danger")
            return redirect(url_for("doctor_login"))

        session["doctor_email"] = doctor["email"]
        session["doc_id"] = doctor["doc_id"]
        session["specialization"] = doctor["specialization"]

        return redirect(url_for("doctor_dashboard"))

    return render_template("doctor/doctor-login.html")

# ---------- DOCTOR DASHBOARD ----------
@app.route("/doctor-dashboard")
def doctor_dashboard():
    if "doctor_email" not in session:
        return redirect(url_for("doctor_login"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM doctors WHERE email=%s", (session["doctor_email"],))
    doctor = cur.fetchone()

    cur.execute("""
        SELECT sa.*, p.fullname, p.gender, p.age
        FROM symptoms_application sa
        JOIN patients p ON sa.patient_id = p.id
        WHERE sa.disease_category=%s AND sa.status='pending'
    """, (doctor["specialization"],))
    patients = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("doctor/doctor-dashboard.html", doctor=doctor, patients=patients)

# ---------- PATIENT REGISTER ----------
@app.route("/patient-register", methods=["GET", "POST"])
def patient_register():
    if request.method == "POST":
        fullname = request.form["fullname"]
        email = request.form["email"]
        phone = request.form["phone"]
        gender = request.form["gender"]
        age = request.form["age"]
        address = request.form["address"]
        medical_history = request.form["medicalHistory"]
        password = generate_password_hash(request.form["password"])

        profile_image = request.files["profileImage"]
        filename = secure_filename(profile_image.filename)
        profile_image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO patients
                (fullname,email,phone,gender,age,address,medical_history,password,profile_image)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                fullname,email,phone,gender,age,
                address,medical_history,password,filename
            ))
            conn.commit()
            flash("Patient registered successfully", "success")
            return redirect(url_for("patient_login"))
        except Exception as e:
            conn.rollback()
            flash(str(e), "danger")
        finally:
            cur.close()
            conn.close()

    return render_template("patient/patient-register.html")

# ---------- PATIENT LOGIN ----------
@app.route("/patient-login", methods=["GET", "POST"])
def patient_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM patients WHERE email=%s", (email,))
        patient = cur.fetchone()
        cur.close()
        conn.close()

        if not patient or not check_password_hash(patient["password"], password):
            flash("Invalid login", "danger")
            return redirect(url_for("patient_login"))

        session["patient_email"] = patient["email"]
        return redirect(url_for("patient_dashboard"))

    return render_template("patient/patient-login.html")

# ---------- PATIENT DASHBOARD ----------
@app.route("/patient-dashboard")
def patient_dashboard():
    if "patient_email" not in session:
        return redirect(url_for("patient_login"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM patients WHERE email=%s", (session["patient_email"],))
    patient = cur.fetchone()

    cur.execute("""
        SELECT * FROM symptoms_application
        WHERE patient_id=%s
        ORDER BY created_at DESC
    """, (patient["id"],))
    submissions = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "patient/patient-dashboard.html",
        patient=patient,
        submissions=submissions
    )

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ================== RUN ==================
if __name__ == "__main__":
    app.run(debug=True)
