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
    system_prompt = "You are a Computer Science coach for High School Freshmen. You MUST NOT give the student the full solution or write the code for them. Instead, provide a single, subtle hint or a conceptual pointer to help them figure it out themselves. If they ask for code, refuse and explain the concept instead. Your goal is to guide them, not do the work for them."
    question = "Right now the student is struggling with this: " + question

    # Apply Unit-specific constraints
    constraints = ""
    if unit == '1':
        constraints = "\nLIMIT YOUR ANSWERS. The student ONLY knows these concepts: print(), input(), int(), float(), str(), variables, basic arithmetic (+ - * /), comments (#)."
    elif unit == '2':
        constraints = "\nLIMIT YOUR ANSWERS. The student ONLY knows these concepts: print(), input(), int(), float(), str(), variables, basic arithmetic (+ - * /), comments (#), math.sqrt(), math.pow(), math.fabs(), round(), abs(), import math, //, %, **."
    elif unit == '3':
        constraints = "\nLIMIT YOUR ANSWERS. The student ONLY knows these concepts: print(), input(), int(), float(), str(), variables, basic arithmetic (+ - * /), comments (#), math.sqrt(), math.pow(), math.fabs(), round(), abs(), import math, //, %, **, comparison operators (== != < <= > >=), logical operators (and or not), if, elif, else, nested conditionals."
    elif unit == '4':
        constraints = "\nLIMIT YOUR ANSWERS. The student ONLY knows these concepts: print(), input(), int(), float(), str(), variables, basic arithmetic (+ - * /), comments (#), math.sqrt(), math.pow(), math.fabs(), round(), abs(), import math, //, %, **, comparison operators (== != < <= > >=), logical operators (and or not), if, elif, else, nested conditionals, for, while, range(), counters, accumulators, sentinel loops, loop control structures."
    
    if constraints:
        system_prompt += constraints

    # Add formatting instruction
    system_prompt += "\nTry to answer with numbered steps that students can follow step-by-step to complete the assignment."

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
