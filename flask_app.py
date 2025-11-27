import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# Initialize OpenAI client
# Expects OPENAI_API_KEY in environment variables
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question')
    level = data.get('level')
    unit = data.get('unit')

    if not question:
        return jsonify({'error': 'No question provided'}), 400

    if not client.api_key:
        return jsonify({'error': 'OpenAI API key not configured'}), 500

    # Determine base system prompt
    system_prompt = (
        "You are a Computer Science coach for High School Freshmen. "
        "You MUST NOT give the student the full solution or write the code for them. "
        "Instead, provide a single, subtle hint or a conceptual pointer to help them figure it out themselves. "
        "If they ask for code, refuse and explain the concept instead. "
        "Your goal is to guide them, not do the work for them.\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "1. **Explain the 'Why':** Always explain the reasoning behind your suggestions. Don't just say 'do this', explain why it works.\n"
        "2. **Avoid Repetition:** Do not simply restate the student's question or your previous answer. Provide new insight or a different angle if they are stuck.\n"
        "3. **Be Accurate:** Ensure your syntax advice is 100% correct for Python. Do not flag valid syntax (like quotes) as incorrect.\n"
        "4. **Strict Scope:** Do NOT suggest functions, methods, or concepts that the student has not learned yet (see the Allowed Concepts list below). This is vital to avoid confusion."
    )
    question = "Right now the student is struggling with this: " + question

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

    # Add formatting instruction
    system_prompt += "\n\nTry to answer with numbered steps that explain the logic clearly."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    retry_occurred = False
    max_retries = 3
    
    try:
        for attempt in range(max_retries):
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            answer = response.choices[0].message.content

            # Check for code blocks
            if "```" in answer:
                retry_occurred = True
                # Add the assistant's bad response and a correction instruction to history
                messages.append({"role": "assistant", "content": answer})
                messages.append({"role": "user", "content": "You provided code. Please provide a hint WITHOUT code."})
                # Loop continues to next attempt
            else:
                # No code found, break and return
                break
        
        # If loop finishes, we return the last answer (whether it has code or not, to avoid infinite loops)
        return jsonify({
            'answer': answer,
            'retry_occurred': retry_occurred,
            'debug_info': {
                'system_prompt': system_prompt,
                'user_prompt': question
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
