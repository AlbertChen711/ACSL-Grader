import json
import os
import re
import sys


# -----------------------------
# CLEAN NUMBERING (1. 2. 3. ...)
# -----------------------------
def clean_numbering(text):
    # removes "1. ", "2. ", etc.
    text = re.sub(r"\n?\s*\d+\.\s*", "\n", text)
    return text.strip()


# -----------------------------
# EXTRACT SECTION BETWEEN LABELS
# -----------------------------
def extract_section(text, start_key, end_key):
    pattern = re.compile(
        rf"{start_key}(.*?){end_key}",
        re.DOTALL | re.IGNORECASE
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


# -----------------------------
# PARSE CASES FROM INPUT/OUTPUT BLOCKS
# -----------------------------
def parse_pairs(input_text, output_text):
    input_text = clean_numbering(input_text)
    output_text = clean_numbering(output_text)

    # Detect separator: blank lines (\n\n) between cases, or single \n
    input_sep = "\n\n" if "\n\n" in input_text else "\n"
    output_sep = "\n\n" if "\n\n" in output_text else "\n"

    inputs = [x.strip() for x in input_text.split(input_sep) if x.strip()]
    outputs = [x.strip() for x in output_text.split(output_sep) if x.strip()]

    cases = []

    for i in range(min(len(inputs), len(outputs))):
        cases.append({
            "input": inputs[i],
            "output": outputs[i]
        })

    return cases


# -----------------------------
# MAIN ACSL PARSER
# -----------------------------
def parse_acsl(text):
    text = text.replace("\r", "\n")

    sample_input = extract_section(text, "SAMPLE INPUT:", "SAMPLE OUTPUT:")
    sample_output = extract_section(text, "SAMPLE OUTPUT:", "TEST INPUT:")
    test_input = extract_section(text, "TEST INPUT:", "TEST OUTPUT:")  
    test_output = extract_section(text, "TEST OUTPUT:", "$")

    sample_cases = parse_pairs(sample_input, sample_output)
    hidden_cases = parse_pairs(test_input, test_output)

    return sample_cases, hidden_cases


# -----------------------------
# USER INPUT
# -----------------------------
year = input("Year (e.g. 2025-2026): ")
division = input("Division (junior/intermediate/senior): ")
contest = input("Contest filename (e.g. contest_1): ")
problem_name = input("Problem name: ")
time_limit = float(input("Time limit (seconds): "))


print("\nPaste FULL ACSL problem text, then press CTRL+Z (Windows) or CTRL+D (Mac/Linux):\n")

pasted_text = sys.stdin.read()


# -----------------------------
# PARSE
# -----------------------------
sample_cases, hidden_cases = parse_acsl(pasted_text)


# -----------------------------
# BUILD JSON
# -----------------------------
problem = {
    "problem_name": problem_name,
    "description": "",
    "time_limit": time_limit,
    "sample_cases": sample_cases,
    "hidden_cases": hidden_cases
}


# -----------------------------
# SAVE FILE
# -----------------------------
output_dir = os.path.join("data", year, division)
os.makedirs(output_dir, exist_ok=True)

output_file = os.path.join(output_dir, f"{contest}.json")

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(problem, f, indent=4)


# -----------------------------
# DONE
# -----------------------------
print(f"\n✅ Finished!")
print(f"Sample cases: {len(sample_cases)}")
print(f"Hidden cases: {len(hidden_cases)}")
print(f"Saved to: {output_file}")