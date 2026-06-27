import subprocess
import tempfile
import os

print("RUNNING THIS FILE:", __file__)
def run_code(code, input_data, time_limit=2):
    # ==============
    # BAD PATTERNS (FOR SAFETY)
    # ==============

    BAD_PATTERNS = [
        "import os",
        "import subprocess",
        "import socket",
        "import shutil",
        "__import__",
        "open(",
    ]
    for bad in BAD_PATTERNS:
        if bad in code:
            return {
                "stdout": "",
                "stderr": f"Blocked unsafe code: {bad}",
                "returncode" : -2
            }
    with tempfile.TemporaryDirectory() as tmp:

        code_path = os.path.join(tmp, "main.py")

        with open(code_path, "w") as f:
            f.write(code)

        try:
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-i",
                    "--network", "none",
                    "--memory", "128m",
                    "--cpus", "0.5",
                    "--pids-limit", "64",
                    "--read-only",

                    "-v", f"{tmp}:/app:rw",
                    "-e", "PYTHONUNBUFFERED=1",
                    "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",

                    "safe-python",              # 👈 IMAGE MUST BE HERE

                    "python3",
                    "/app/main.py",
                ],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=time_limit,
            )
            #=============
            # OUTPUT LIMIT
            # ============
            if len(result.stdout) > 100000:
                return {
                    "stdout": "",
                    "stderr": "Output too large",
                    "returncode": -3
                }

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Time Limit Exceeded",
                "returncode": -1,
            }