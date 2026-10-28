
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os

app = Flask(__name__)
app.secret_key = "hostel-project-key"
def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

STUDENTS_FILE = "students.json"
ROOMS_FILE = "rooms.json"


def load_data(filename, default):
    if not os.path.exists(filename):
        with open(filename, "w") as file:
            json.dump(default, file, indent=4)

    with open(filename, "r") as file:
        return json.load(file)


def save_data(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)


def get_students():
    return load_data(STUDENTS_FILE, [])


def get_rooms():
    default_rooms = [
        {"room_number": number, "occupied": False}
        for number in range(101, 121)
    ]
    return load_data(ROOMS_FILE, default_rooms)


@app.route("/")
def home():
    students = get_students()
    rooms = get_rooms()

    total_rooms = len(rooms)
    occupied_rooms = sum(1 for room in rooms if room["occupied"])
    vacant_rooms = total_rooms - occupied_rooms

    return render_template(
        "index.html",
        total_students=len(students),
        total_rooms=total_rooms,
        occupied_rooms=occupied_rooms,
        vacant_rooms=vacant_rooms
    )


@app.route("/admission", methods=["GET", "POST"])
def admission():
    students = get_students()
    rooms = get_rooms()

    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        name = request.form.get("name", "").strip()
        age_text = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        phone = request.form.get("phone", "").strip()
        course = request.form.get("course", "").strip()
        college = request.form.get("college", "").strip()
        address = request.form.get("address", "").strip()
        room_text = request.form.get("room_number", "").strip()

        if not all([
            student_id, name, age_text, gender, phone,
            course, college, address, room_text
        ]):
            flash("Please fill in all fields.", "error")
            return redirect(url_for("admission"))

        if any(s["id"].lower() == student_id.lower() for s in students):
            flash("This Student ID already exists.", "error")
            return redirect(url_for("admission"))

        if not age_text.isdigit() or not 15 <= int(age_text) <= 60:
            flash("Age must be between 15 and 60.", "error")
            return redirect(url_for("admission"))

        if not phone.isdigit() or len(phone) != 10:
            flash("Phone number must contain 10 digits.", "error")
            return redirect(url_for("admission"))

        room = next(
            (r for r in rooms
             if str(r["room_number"]) == room_text),
            None
        )

        if room is None or room["occupied"]:
            flash("Please select a vacant room.", "error")
            return redirect(url_for("admission"))

        student = {
            "id": student_id,
            "name": name,
            "age": int(age_text),
            "gender": gender,
            "phone": phone,
            "course": course,
            "college": college,
            "address": address,
            "room_number": room["room_number"]
        }

        students.append(student)
        room["occupied"] = True

        save_data(STUDENTS_FILE, students)
        save_data(ROOMS_FILE, rooms)

        flash("Student admitted successfully!", "success")
        return redirect(url_for("home"))

    vacant_rooms = [r for r in rooms if not r["occupied"]]

    return render_template(
        "admission.html",
        vacant_rooms=vacant_rooms
    )


@app.route("/students")
def view_students():
    students = get_students()
    query = request.args.get("q", "").strip().lower()

    if query:
        students = [
            student for student in students
            if query in str(student.get("id", "")).lower()
            or query in str(student.get("name", "")).lower()
        ]

    return render_template(
        "students.html",
        students=students,
        query=query
    )
@app.route("/edit/<student_id>", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    students = get_students()

    student = next(
        (s for s in students if str(s.get("id")) == str(student_id)),
        None
    )

    if student is None:
        flash("Student record not found.", "error")
        return redirect(url_for("view_students"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        age_text = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        phone = request.form.get("phone", "").strip()
        course = request.form.get("course", "").strip()
        college = request.form.get("college", "").strip()
        address = request.form.get("address", "").strip()

        if not all([name, age_text, gender, phone, course, college, address]):
            flash("Please fill in all fields.", "error")
            return redirect(url_for("edit_student", student_id=student_id))

        if not age_text.isdigit() or not 15 <= int(age_text) <= 60:
            flash("Age must be between 15 and 60.", "error")
            return redirect(url_for("edit_student", student_id=student_id))

        if not phone.isdigit() or len(phone) != 10:
            flash("Phone number must contain exactly 10 digits.", "error")
            return redirect(url_for("edit_student", student_id=student_id))

        student.update({
            "name": name,
            "age": int(age_text),
            "gender": gender,
            "phone": phone,
            "course": course,
            "college": college,
            "address": address
        })

        save_data(STUDENTS_FILE, students)

        flash("Student details updated successfully!", "success")
        return redirect(url_for("view_students"))

    return render_template("edit_student.html", student=student)


@app.route("/delete/<student_id>", methods=["POST"])
def delete_student(student_id):
    students = get_students()
    rooms = get_rooms()

    student = next(
        (s for s in students if s["id"] == student_id),
        None
    )

    if student is None:
        flash("Student record not found.", "error")
        return redirect(url_for("view_students"))

    confirmed = request.form.get("confirm") == "yes"

    if not confirmed:
        flash("Deletion was not confirmed.", "error")
        return redirect(url_for("view_students"))

    room_number = student["room_number"]

    students = [
        s for s in students
        if s["id"] != student_id
    ]

    for room in rooms:
        if room["room_number"] == room_number:
            room["occupied"] = False
            break

    save_data(STUDENTS_FILE, students)
    save_data(ROOMS_FILE, rooms)

    flash(
        f"Student deleted successfully. Room {room_number} is vacant again.",
        "success"
    )

    return redirect(url_for("view_students"))

@app.route("/rooms")
def room_management():
    rooms = get_rooms()
    return render_template("rooms.html", rooms=rooms)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == "admin" and password == "hostel123":
            session["admin_logged_in"] = True
            return redirect(url_for("home"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.", "success")
    return redirect(url_for("login"))



if __name__ == "__main__":
    app.run(debug=True)

