"""
1. Website system (year → contest → problem info) 

2. Data storage system (Make a JSON or database for everything)

3. File upload + textbox input system

4. Grading engine (test case runner + checker)

5. Submission history system (store all attempts) and make a log in system to keep all your work

6. Time limit enforcement (stop infinite loops), also stops if it runs too long

7. Multi-year support (2024-2025, 2025-2026, etc.)

8. Contest structure system (standardized hierarchy)

9. Runtime + performance analytics page

10. TODO Debug mode (run and compare outputs locally)

11. Error handling system (syntax/runtime/input errors)

12. TODO Solve all the problems to check whether the solutions and everything is correct.

13. Make sure the website is safe so that no hackers would try to hack it

14. TODO Make sure everything is professional looking, good UI/UX

15. Make sure there are sample input and test input, the sample input should be shown, but the test input should not
"""

# import all tools
from flask import Flask, render_template, request, session, redirect, url_for, flash
from functools import wraps
import subprocess # makes sure the code would run safely
import sys # gets current python ath
import json # analyzes contest data files
import os # manages all the files and directories
import time # gets time to check how long your code ran to stop it if its too slow
import tempfile
import shutil

import database

# creates the file
app = Flask(__name__)
app.secret_key = os.urandom(32).hex()

database.init_db()


# -----------------------
# DATA SCANNER
# -----------------------
"""Scans the data/ folder, and gets a sorted list of all the folders for the years, e.g. 2024-2025"""
def get_available_years():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    years = sorted(
        e for e in os.listdir(data_dir)
        if os.path.isdir(os.path.join(data_dir, e)) and not e.startswith(".")
    )
    return years


"""Looks inside a specific folder to find the divisions e.g. junior, intermediate, senior"""
def get_divisions_for_year(year):
    year_dir = os.path.join(os.path.dirname(__file__), "data", year)
    if not os.path.isdir(year_dir):
        return []
    return sorted(
        e for e in os.listdir(year_dir)
        if os.path.isdir(os.path.join(year_dir, e))
    )


"""Gets the contests inside the divisions"""
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
"""Makes sure you have to log in in order to access the website for security measures"""
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
""" This is the home, where you arrive at after logging in"""
@app.route("/")
def home():
    years = get_available_years()
    return render_template("index.html", user=session.get("user_email"), years=years)


# -----------------------
# SIGNUP
# -----------------------
"""Handles GET and POST, for signing up, including the sign up page and submitting the signup form"""
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
"""Gets the GET and POST so that you can log in"""
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
"""Just logging out"""
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# -----------------------
# SEASON PAGE
# -----------------------
"""Creates an URL for every season"""
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

"""It is the route that serves the coding problem and grades user-submitted code"""
# -----------------------
# CONTEST RUNNER
# -----------------------
@app.route("/<year>/<division>/<contest>", methods=["GET", "POST"])
@login_required
def contest(year, division, contest):
    code = ""
    results = []

    file_path = f"data/{year}/{division}/{contest}.json"
    # Makes sure the file actually exists, or would go to an error page
    if not os.path.exists(file_path):
        return render_template("error.html", message=f"Contest file not found: {file_path}")

    with open(file_path, "r") as f:
        problem_data = json.load(f)
    # gets the problem based on how what the user wants
    problem_name = problem_data.get("problem_name", contest)
    description = problem_data.get("description", None)
    sample_cases = problem_data.get("sample_cases", [])
    hidden_cases = problem_data.get("hidden_cases", [])

    # Actuall function that runs the code
    def run_cases(cases, hidden=False, sandbox_dir=None, container_id=None):
        for i, tc in enumerate(cases):
            start = time.perf_counter()
            try:
                result = subprocess.run(
                    ["docker", "exec", "-i", container_id,
                     "python", "/sandbox/student.py"],
                    input=tc["input"] + "\n",
                    capture_output=True,
                    text=True,
                    timeout=float(problem_data.get("time_limit", 2))
                )
                print("STDERR",result.stderr)
                print("STDOUT:",result.stdout)
                runtime_ms = round((time.perf_counter() - start) * 1000, 2)
            # checks if the code takes too long to run
            except subprocess.TimeoutExpired:
                runtime_ms = round((time.perf_counter() - start) * 1000, 2)
                results.append({
                    "test": i + 1,
                    "test_index": i,
                    "input": "HIDDEN" if hidden else tc["input"].strip(),
                    "expected": "HIDDEN" if hidden else tc["output"].strip(),
                    "actual": "TIME LIMIT EXCEEDED",
                    "status": "TLE",
                    "runtime_ms": runtime_ms
                })
                continue

            expected = tc["output"].strip()
            actual = result.stdout.strip()
            # checks if the code is too long
            if len(result.stdout) > 10000:
                results.append({
                    "test": i + 1,
                    "test_index": i,
                    "input": "HIDDEN" if hidden else tc["input"].strip(),
                    "expected": "HIDDEN" if hidden else expected,
                    "actual": "OUTPUT LIMIT EXCEEDED",
                    "status": "FAIL",
                    "runtime_ms": runtime_ms
                })
                continue

            if result.stderr:
                error_line = result.stderr.splitlines()[-1]
                status = "SYNTAX ERROR" if "SyntaxError" in error_line else "RUNTIME ERROR"
                results.append({
                    "test": i + 1,
                    "test_index": i,
                    "input": "HIDDEN" if hidden else tc["input"].strip(),
                    "expected": "HIDDEN" if hidden else expected,
                    "actual": error_line,
                    "status": status,
                    "runtime_ms": runtime_ms
                })
                continue

            results.append({
                "test": i + 1,
                "test_index": i,
                "input": "HIDDEN" if hidden else tc["input"].strip(),
                "expected": "HIDDEN" if hidden else expected,
                "actual": actual,
                "status": "PASS" if actual == expected else "FAIL",
                "runtime_ms": runtime_ms
            })
    
    if request.method == "POST":
        file = request.files.get("code_file")
        if file and file.filename:
            code = file.read().decode("utf-8")

        if not code:
            code = request.form.get("code", "")

        sandbox_dir = None
        try:
            sandbox_dir = tempfile.mkdtemp()
            student_path = os.path.join(sandbox_dir, "student.py")
            with open(student_path, "w") as f:
                f.write(code)
        except Exception as e:
            if sandbox_dir:
                shutil.rmtree(sandbox_dir, ignore_errors=True)
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

        container_id = None
        try:
            docker_path = sandbox_dir.replace("\\", "/")
            result = subprocess.run(
                ["docker", "run", "-d", "--rm",
                 "--network", "none",
                 "--read-only",
                 "--memory", "256m",
                 "--cpus", "1",
                 "--pids-limit", "50",
                 "--cap-drop", "ALL",
                 "--security-opt", "no-new-privileges",
                 "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
                 "-e", "PYTHONUNBUFFERED=1",
                 "-v", f"{docker_path}:/sandbox:ro",
                 "acsl-sandbox",
                 "sleep", "infinity"],
                capture_output=True,
                text=True
            )
            container_id = result.stdout.strip()
            run_cases(sample_cases, hidden=False, sandbox_dir=sandbox_dir, container_id=container_id)
            run_cases(hidden_cases, hidden=True, sandbox_dir=sandbox_dir, container_id=container_id)
        finally:
            if container_id:
                subprocess.run(["docker", "kill", container_id], capture_output=True)
            shutil.rmtree(sandbox_dir, ignore_errors=True)

        passed = sum(1 for r in results if r["status"] == "PASS")
        total = len(results)
        #checks their current history
        submission_id = database.save_submission(
            session["user_id"],
            year,
            division,
            contest,
            passed,
            total,
            code
        )
        database.save_submission_results(submission_id, results)
    # checks the past results
    past_result = database.get_contest_result(
        session["user_id"],
        year,
        division,
        contest
    )
    # sends back all the information
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
# ANALYTICS
# -----------------------
@app.route("/analytics")
@login_required
def analytics():
    year = request.args.get("year")
    division = request.args.get("division")
    contest = request.args.get("contest")

    history = database.get_submission_history(
        session["user_id"], year, division, contest
    )

    selected_detail = None
    detail_id = request.args.get("detail")
    if detail_id:
        selected_detail = database.get_submission_detail(detail_id)

    worst_cases = None
    if year and division and contest:
        worst_cases = database.get_worst_performing_cases(
            session["user_id"], year, division, contest
        )

    return render_template(
        "analytics.html",
        user=session.get("user_email"),
        history=history,
        selected_detail=selected_detail,
        worst_cases=worst_cases,
        years=get_available_years(),
        year=year, division=division, contest=contest,
    )


# -----------------------
# RUN SERVER
# -----------------------
if __name__ == "__main__":
    app.run(debug=False)