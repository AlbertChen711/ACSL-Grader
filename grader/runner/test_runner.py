from run import run_code

student_code = """
name = input()
print("Hello", name)
"""

result = run_code(student_code, "Albert\n")

print(result)