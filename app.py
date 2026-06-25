"""
1. Website system (year → contest → problem info) 

2. Data storage system (Make a JSON or database for everything)

3. File upload + textbox input system

4. Grading engine (test case runner + checker)

5. Submission history system (store all attempts) and make a log in system to keep all your work

6. Time limit enforcement (stop infinite loops), also stops if it runs too long

7. TODO Multi-year support (2024-2025, 2025-2026, etc.)

8. TODO Contest structure system (standardized hierarchy)

9. TODO Runtime + performance analytics page

10. TODO Debug mode (run and compare outputs locally)

11. Error handling system (syntax/runtime/input errors)

12. TODO Solve all the problems to check whether the solutions and everything is correct.

13. TODO Make sure the website is safe so that no hackers would try to hack it

14. TODO Make sure everything is professional looking, good UI/UX

15. Make sure there are sample input and test input, the sample input should be shown, but the test input should not
"""

from flask import Flask, render_template, request, session, redirect, url_for, flash
from functools import wraps
import subprocess
import sys
import json
import os

import database

app = Flask(__name__)
app.secret_key = os.urandom(32).hex()

database.init_db()


# -----------------------
# DATA SCANNER
# -----------------------
def get_available_years():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    years = sorted(
        e for e in os.listdir(data_dir)
        if os.path.isdir(os.path.join(data_dir, e)) and not e.startswith(".")
    )
    return years


def get_divisions_for_year(year):
    year_dir = os.path.join(os.path.dirname(__file__), "data", year)
    if not os.path.isdir(year_dir):
        return []
    return sorted(
        e for e in os.listdir(year_dir)
        if os.path.isdir(os.path.join(year_dir, e))
    )


def get_contests_for_year_division(year, division):
    div_dir = os.path.join(os.path.dirname(__file__), "data", year, division)
    if not os.path.isdir(div_dir):
        return []
    return sorted(
        e.replace(".json", "")
        for e in os.listdir(div_dir)
        if e.endswith(".json")
    )


# -----------------------
# LOGIN REQUIRED DECORATOR
# -----------------------
def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped


# -----------------------
# HOME
# -----------------------
@app.route("/")
def home():
    years = get_available_years()
    return render_template("index.html", user=session.get("user_email"), years=years)


# -----------------------
# SIGNUP
# -----------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not email or not password:
            flash("Email and password are required.")
            return render_template("signup.html")

        if password != confirm:
            flash("Passwords do not match.")
            return render_template("signup.html")

        if database.create_user(email, password):
            flash("Account created! Please log in.")
            return redirect(url_for("login"))
        else:
            flash("An account with that email already exists.")
            return render_template("signup.html")

    return render_template("signup.html")


# -----------------------
# LOGIN
# -----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = database.verify_user(email, password)
        if user:
            session["user_id"] = user["id"]
            session["user_email"] = user["email"]
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password.")
            return render_template("login.html")

    return render_template("login.html")


# -----------------------
# LOGOUT
# -----------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# -----------------------
# SEASON PAGE
# -----------------------
@app.route("/<year>")
@login_required
def season(year):
    divisions = get_divisions_for_year(year)
    contests_by_division = {}
    for div in divisions:
        contests_by_division[div] = get_contests_for_year_division(year, div)
    return render_template(
        "season.html",
        user=session.get("user_email"),
        year=year,
        divisions=divisions,
        contests_by_division=contests_by_division
    )


# -----------------------
# CONTEST RUNNER
# -----------------------
@app.route("/<year>/<division>/<contest>", methods=["GET", "POST"])
@login_required
def contest(year, division, contest):
    code = ""
    results = []

    file_path = f"data/{year}/{division}/{contest}.json"

    if not os.path.exists(file_path):
        return render_template("error.html", message=f"Contest file not found: {file_path}")

    with open(file_path, "r") as f:
        problem_data = json.load(f)

    problem_name = problem_data.get("problem_name", contest)
    description = problem_data.get("description", None)
    sample_cases = problem_data.get("sample_cases", [])
    hidden_cases = problem_data.get("hidden_cases", [])

    def run_cases(cases, hidden=False):
        for i, tc in enumerate(cases):
            try:
                result = subprocess.run(
                    [sys.executable, "student.py"],
                    input=tc["input"] + "\n",
                    capture_output=True,
                    text=True,
                    timeout=problem_data.get("time_limit", 2)
                )

                expected = tc["output"].strip()
                actual = result.stdout.strip()

                if len(result.stdout) > 10000:
                    results.append({
                        "test": i + 1,
                        "input": "HIDDEN" if hidden else tc["input"].strip(),
                        "expected": expected,
                        "actual": "OUTPUT LIMIT EXCEEDED",
                        "status": "FAIL"
                    })
                    continue

                if result.stderr:
                    error_line = result.stderr.splitlines()[-1]
                    status = "SYNTAX ERROR" if "SyntaxError" in error_line else "RUNTIME ERROR"
                    results.append({
                        "test": i + 1,
                        "input": "HIDDEN" if hidden else tc["input"].strip(),
                        "expected": expected,
                        "actual": error_line,
                        "status": status
                    })
                    continue

                results.append({
                    "test": i + 1,
                    "input": "HIDDEN" if hidden else tc["input"].strip(),
                    "expected": expected,
                    "actual": actual,
                    "status": "PASS" if actual == expected else "FAIL"
                })

            except subprocess.TimeoutExpired:
                results.append({
                    "test": i + 1,
                    "input": "HIDDEN" if hidden else tc["input"].strip(),
                    "expected": tc["output"].strip(),
                    "actual": "TIME LIMIT EXCEEDED",
                    "status": "TLE"
                })

    if request.method == "POST":
        file = request.files.get("code_file")
        if file and file.filename:
            code = file.read().decode("utf-8")

        if not code:
            code = request.form.get("code", "")

        try:
            with open("student.py", "w") as f:
                f.write(code)
        except Exception as e:
            results.append({
                "test": 0,
                "input": "",
                "expected": "",
                "actual": str(e),
                "status": "SERVER ERROR"
            })
            return render_template(
                "contest.html",
                year=year,
                division=division,
                contest=contest,
                problem_name=problem_name,
                description=description,
                results=results,
                code=code,
                user=session.get("user_email"),
                past_result=None
            )

        run_cases(sample_cases, hidden=False)
        run_cases(hidden_cases, hidden=True)

        passed = sum(1 for r in results if r["status"] == "PASS")
        total = len(results)

        database.save_submission(
            session["user_id"],
            year,
            division,
            contest,
            passed,
            total,
            code
        )

    past_result = database.get_contest_result(
        session["user_id"],
        year,
        division,
        contest
    )

    return render_template(
        "contest.html",
        year=year,
        division=division,
        contest=contest,
        problem_name=problem_name,
        description=description,
        results=results,
        code=code,
        user=session.get("user_email"),
        past_result=past_result
    )


# -----------------------
# RUN SERVER
# -----------------------
if __name__ == "__main__":
    app.run(debug=False)