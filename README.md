# STEM Help

A Flask-based web application designed to act as a Computer Science coach for students. It uses the OpenAI API to provide tailored assistance based on the student's grade level and the specific unit they are working on.

## Features

-   **Level-Based Assistance**: Tailors responses for different education levels:
    -   Grade 1
    -   Grade 5
    -   High School
    -   College/Expert
-   **Unit-Specific Constraints**: Enforces knowledge constraints based on the selected curriculum unit (1-4) to ensure students aren't given solutions using concepts they haven't learned yet.
-   **Coaching Mode**: A dedicated "Submit for Coaching" button that strictly forbids providing full solutions. Instead, it offers hints and conceptual pointers to guide the student.
-   **Prompt Logging**: Logs the exact system and user prompts sent to the OpenAI API in the browser console for transparency and debugging.
-   **Responsive Design**: A clean, dark-themed interface matching the school's branding.

## Prerequisites

-   Python 3.x
-   OpenAI API Key

## Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd STEMHELP
    ```

2.  Install the required dependencies:
    ```bash
    pip install flask openai
    ```

## Configuration

Set your OpenAI API key as an environment variable:

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="your-api-key-here"
```

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=your-api-key-here
```

**Mac/Linux:**
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Usage

1.  Start the Flask application:
    ```bash
    python app.py
    ```

2.  Open your web browser and navigate to:
    `http://127.0.0.1:5000`

3.  **Select a Unit** (1-4 or Other) from the buttons on the right.
4.  Type your question in the large input field.
5.  Click a **Level button** (1-4) for a direct answer adapted to that level, or click **Submit for Coaching** to get a hint without the full solution.

## Project Structure

-   `app.py`: Main Flask application containing backend logic and prompt engineering.
-   `templates/index.html`: Frontend HTML template with JavaScript for API interaction.
-   `static/css/style.css`: Custom styling for the dark theme.
-   `static/img/`: Contains image assets (banner, logos).
