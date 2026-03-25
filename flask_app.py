import os
import re
import ast
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# Initialize OpenAI client
# Expects OPENAI_API_KEY in environment variables
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

VALID_UNITS = {"1", "2", "3", "4"}
VALID_MODES = {
    "breakdown": "Break down the assignment into smaller parts",
    "first-line": "Give me the first line of code",
    "check-errors": "Check my code for errors",
}


def extract_first_nonempty_line(text):
    if not text:
        return ""

    cleaned = text.strip()
    if "```" in cleaned:
        parts = cleaned.split("```")
        if len(parts) > 1:
            block = parts[1]
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if lines and lines[0].lower() in {"python", "py"}:
                lines = lines[1:]
            if lines:
                return lines[0]

    for line in cleaned.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped

    return cleaned


def is_invalid_first_line(line):
    if not line:
        return True
    stripped = line.strip()
    if not stripped:
        return True
    if "\n" in stripped or ";" in stripped:
        return True
    return False


def extract_step_quoted_text(step_text):
    if not step_text:
        return ""
    # Match plain quoted strings.
    patterns = [
        r'"([^"]+)"',
        r"'([^']+)'",
    ]
    for pattern in patterns:
        match = re.search(pattern, step_text)
        if match:
            return match.group(1)
    return ""


def to_python_double_quoted(text):
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def first_line_from_step(first_step, raw_question):
    step = (first_step or "").strip()
    step_l = step.lower()

    # If the first step says to print a specific line, translate directly.
    if "print" in step_l:
        quoted = extract_step_quoted_text(step)
        if quoted:
            return f"print({to_python_double_quoted(quoted)})"

    # If the first step is about getting input, use beginner-safe prompted input.
    if any(token in step_l for token in ["input", "ask", "enter"]):
        return beginner_first_line_fallback(raw_question)

    return ""


def beginner_first_line_fallback(raw_question):
    q = (raw_question or "").lower()
    if "whole number" in q or "integer" in q:
        return 'number = int(input("Give me a whole number: "))'
    if any(token in q for token in ["number", "int", "age", "score", "grade", "amount", "count"]):
        return 'number = int(input("Give me a number: "))'
    return 'text = input("Type your answer: ")'


def enforce_check_errors_voice_and_format(text):
    answer = (text or "").strip()

    replacements = [
        (r"\b[Tt]he student is\b", "You are"),
        (r"\b[Tt]he student\b", "You"),
        (r"\b[Ss]tudent code\b", "Your code"),
        (r"\b[Tt]heir\b", "your"),
        (r"\b[Tt]hem\b", "you"),
        (r"\b[Tt]hey\b", "you"),
    ]
    for pattern, repl in replacements:
        answer = re.sub(pattern, repl, answer)

    # Remove accidental wrapping quotes around the whole response.
    if len(answer) >= 2 and answer[0] == '"' and answer[-1] == '"':
        answer = answer[1:-1].strip()

    # Ensure required headings exist.
    lower = answer.lower()
    if "issue:" not in lower and "advice:" not in lower:
        answer = f"Issue:\n1. {answer}\n\nAdvice:\n1. Review the issue above and make the fix step by step."
    elif "issue:" in lower and "advice:" not in lower:
        answer = f"{answer}\n\nAdvice:\n1. Use the issue above to guide your next fix."
    elif "issue:" not in lower and "advice:" in lower:
        answer = f"Issue:\n1. Check your code against the assignment requirements.\n\n{answer}"

    return answer


def append_numbered_item(section_text, item_text):
    numbers = re.findall(r"(?m)^\s*(\d+)\.\s", section_text)
    next_number = int(numbers[-1]) + 1 if numbers else 1
    if not section_text.endswith("\n"):
        section_text += "\n"
    return section_text + f"{next_number}. {item_text}\n"


def detect_python_syntax_errors(code_text):
    if not code_text:
        return []

    try:
        ast.parse(code_text)
        return []
    except SyntaxError as err:
        line_no = err.lineno or 1
        offset = err.offset or 1
        message = err.msg or "Invalid syntax"
        lines = code_text.splitlines()
        bad_line = lines[line_no - 1].strip() if 0 < line_no <= len(lines) else ""
        return [{
            "line": line_no,
            "col": offset,
            "message": message,
            "bad_line": bad_line,
        }]
    except Exception:
        # Non-syntax parser issues are ignored here; this checker is syntax-only.
        return []


def enforce_known_code_issues(answer, code_text):
    if not code_text:
        return answer

    has_capital_print = re.search(r"(^|[^A-Za-z_])Print\s*\(", code_text) is not None
    if not has_capital_print:
        return answer

    parts = re.split(r"(?im)^Advice:\s*$", answer, maxsplit=1)
    if len(parts) != 2:
        answer = enforce_check_errors_voice_and_format(answer)
        parts = re.split(r"(?im)^Advice:\s*$", answer, maxsplit=1)
        if len(parts) != 2:
            return (
                "Issue:\n"
                "1. You used `Print(...)` with an uppercase `P`. Python is case-sensitive.\n\n"
                "Advice:\n"
                "1. Change `Print(...)` to `print(...)` with a lowercase `p`."
            )

    issue_part, advice_part = parts[0], parts[1]
    issue_part = append_numbered_item(
        issue_part,
        "You used `Print(...)` with an uppercase `P`. Python is case-sensitive, so that call will fail.",
    )
    advice_part = append_numbered_item(
        advice_part,
        "Change `Print(...)` to `print(...)` with a lowercase `p`.",
    )
    return issue_part.rstrip() + "\n\nAdvice:\n" + advice_part.lstrip()


def enforce_syntax_error_issues(answer, code_text):
    syntax_errors = detect_python_syntax_errors(code_text)
    if not syntax_errors:
        return answer

    parts = re.split(r"(?im)^Advice:\s*$", answer, maxsplit=1)
    if len(parts) != 2:
        answer = enforce_check_errors_voice_and_format(answer)
        parts = re.split(r"(?im)^Advice:\s*$", answer, maxsplit=1)
        if len(parts) != 2:
            first = syntax_errors[0]
            return (
                "Issue:\n"
                f"1. You have a syntax error on line {first['line']} (column {first['col']}): {first['message']}.\n\n"
                "Advice:\n"
                "1. Fix the punctuation/formatting on that line and run your code again."
            )

    issue_part, advice_part = parts[0], parts[1]
    for err in syntax_errors:
        if err["bad_line"]:
            issue_text = (
                f"You have a syntax error on line {err['line']} (column {err['col']}): {err['message']}. "
                f"Problem line: `{err['bad_line']}`."
            )
        else:
            issue_text = f"You have a syntax error on line {err['line']} (column {err['col']}): {err['message']}."
        advice_text = (
            f"Fix the syntax on line {err['line']} first, then run your code again to check for any remaining errors."
        )
        issue_part = append_numbered_item(issue_part, issue_text)
        advice_part = append_numbered_item(advice_part, advice_text)

    return issue_part.rstrip() + "\n\nAdvice:\n" + advice_part.lstrip()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/help/<mode>')
def help_page(mode):
    unit = request.args.get('unit')
    if mode not in VALID_MODES or unit not in VALID_UNITS:
        return render_template('index.html')

    return render_template(
        'help_mode.html',
        mode=mode,
        mode_title=VALID_MODES[mode],
        unit=unit,
    )


@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    original_question = question
    first_step = (data.get('first_step') or '').strip()
    assignment_text = (data.get('assignment_text') or '').strip()
    code_text = (data.get('code_text') or '').strip()
    unit = data.get('unit')
    help_mode = data.get('help_mode')

    if unit not in VALID_UNITS:
        return jsonify({'error': 'Invalid or missing Unit. Please pick Unit 1-4.'}), 400

    if help_mode not in VALID_MODES:
        return jsonify({'error': 'Invalid help type selected.'}), 400

    if help_mode == 'check-errors':
        if not assignment_text:
            return jsonify({'error': 'No assignment provided.'}), 400
        if not code_text:
            return jsonify({'error': 'No code provided.'}), 400
        question = f"Assignment:\n{assignment_text}\n\nStudent code:\n{code_text}"
    elif not question:
        return jsonify({'error': 'No question provided'}), 400

    if not client.api_key:
        return jsonify({'error': 'OpenAI API key not configured'}), 500

    # Determine base system prompt
    system_prompt = (
        "You are a Computer Science coach for High School Freshmen. "
        "You MUST NOT give the student the full solution or write the full program for them. "
        "Explain reasoning clearly and keep advice within the allowed chapter scope.\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "1. Explain the why behind each suggestion.\n"
        "2. Keep advice concise, practical, and accurate for Python.\n"
        "3. Do not jump to concepts outside the allowed chapter concepts."
    )

    coached_question = "Right now the student is struggling with this: " + question

    # Apply Unit-specific constraints
    constraints = ""
    constraint_intro = "\n\nALLOWED CONCEPTS (Strictly limit your advice to these):"

    if unit == '1':
        constraints = f"{constraint_intro} print(), input(), int(), float(), str(), variables, basic arithmetic (+ - * /), comments (#)."
    elif unit == '2':
        constraints = f"{constraint_intro} print(), input(), int(), float(), str(), variables, basic arithmetic (+ - * /), comments (#), math.sqrt(), math.pow(), math.fabs(), round(), abs(), import math, //, %, **."
    elif unit == '3':
        constraints = f"{constraint_intro} print(), input(), int(), float(), str(), variables, basic arithmetic (+ - * /), comments (#), math.sqrt(), math.pow(), math.fabs(), round(), abs(), import math, //, %, **, comparison operators (== != < <= > >=), logical operators (and or not), if, elif, else, nested conditionals."
    elif unit == '4':
        constraints = f"{constraint_intro} print(), input(), int(), float(), str(), variables, basic arithmetic (+ - * /), comments (#), math.sqrt(), math.pow(), math.fabs(), round(), abs(), import math, //, %, **, comparison operators (== != < <= > >=), logical operators (and or not), if, elif, else, nested conditionals, for, while, range(), counters, accumulators, sentinel loops, loop control structures."

    if constraints:
        system_prompt += constraints

    # Apply help-mode behavior
    if help_mode == 'breakdown':
        system_prompt += (
            "\n\nHELP MODE: Break down the assignment into smaller parts. "
            "Return a short numbered checklist of steps. "
            "Do not provide runnable code."
        )
    elif help_mode == 'first-line':
        system_prompt += (
            "\n\nHELP MODE: Translate the first breakdown step into exactly one ultra-beginner first line of Python code and nothing else. "
            "The line must map directly to that first step, and do one simple action only. "
            "If the first step is about printing text/art, return one print() line with exact spacing from that text. "
            "If the first step is about getting input, use a clear prompt string in input(). "
            "No arithmetic, no chaining, no multiple steps, no explanation, and no markdown fences."
        )
    elif help_mode == 'check-errors':
        system_prompt += (
            "\n\nHELP MODE: Review the student's code for likely errors. "
            "Speak directly to the learner in second person (use 'you' and 'your'), never third person. "
            "Format your response with two headings exactly: 'Issue:' then 'Advice:'. "
            "Under each heading, use a numbered list. "
            "Point out issues and explain fixes conceptually. "
            "If showing code, keep it to tiny snippets only (at most one line per issue)."
        )

    user_content = coached_question
    if help_mode == 'first-line' and first_step:
        user_content = (
            "Assignment:\n"
            f"{original_question}\n\n"
            "First breakdown step to translate:\n"
            f"{first_step}\n\n"
            "Translate only that first breakdown step into one beginner Python line."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=messages
        )
        answer = response.choices[0].message.content or ""

        if help_mode == 'first-line':
            deterministic_line = first_line_from_step(first_step, original_question)
            if deterministic_line:
                answer = deterministic_line
            else:
                answer = extract_first_nonempty_line(answer)
            if is_invalid_first_line(answer):
                answer = beginner_first_line_fallback(first_step or original_question)
        elif help_mode == 'check-errors':
            answer = enforce_check_errors_voice_and_format(answer)
            answer = enforce_known_code_issues(answer, code_text)
            answer = enforce_syntax_error_issues(answer, code_text)

        return jsonify({
            'answer': answer,
            'debug_info': {
                'system_prompt': system_prompt,
                'user_prompt': user_content,
                'unit': unit,
                'help_mode': help_mode,
                'first_step': first_step,
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)

