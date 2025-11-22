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
    system_prompt = "You are a helpful assistant."
    if level == '1':
        system_prompt = "You are a helpful assistant for a 1st grade student. Use simple words and short sentences."
    elif level == '2':
        system_prompt = "You are a helpful assistant for a 5th grade student. Explain things clearly but without being too childish."
    elif level == '3':
        system_prompt = "You are a helpful assistant for a high school student. Be detailed and academic."
    elif level == '4':
        system_prompt = "You are a helpful assistant for a college student or expert. Provide in-depth, technical explanations."
    elif level == 'Other':
        system_prompt = "You are a helpful assistant. Adapt to the user's tone."
    elif level == 'Coach':
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

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ]
        )
        answer = response.choices[0].message.content
        return jsonify({
            'answer': answer,
            'debug_info': {
                'system_prompt': system_prompt,
                'user_prompt': question
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
