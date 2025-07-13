from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from openai import OpenAI
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='frontend/build', static_url_path='')
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///learning_platform.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# OpenAI client
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# Database Models
class Learner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    learning_goals = db.Column(db.Text)
    experience_level = db.Column(db.String(50))
    learning_style = db.Column(db.String(50))
    sessions = db.relationship('LearningSession', backref='learner', lazy=True)

class LearningSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    learner_id = db.Column(db.Integer, db.ForeignKey('learner.id'), nullable=False)
    topic = db.Column(db.String(200))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

# Initialize database
with app.app_context():
    db.create_all()

# API Routes
@app.route('/api/learners', methods=['POST'])
def create_learner():
    data = request.get_json()
    existing = Learner.query.filter_by(username=data['username']).first()
    if existing:
        return jsonify({'error': 'Username already exists'}), 400

    learner = Learner(
        username=data['username'],
        learning_goals=data.get('learning_goals', ''),
        experience_level=data.get('experience_level', 'beginner'),
        learning_style=data.get('learning_style', 'combination')
    )
    db.session.add(learner)
    db.session.commit()

    return jsonify({'id': learner.id}), 201

@app.route('/api/learners/<int:learner_id>/sessions', methods=['POST'])
def generate_learning_session(learner_id):
    learner = Learner.query.get(learner_id)
    if not learner:
        return jsonify({'error': 'Learner not found'}), 404

    data = request.get_json()
    topic = data.get('topic', 'Introduction to Programming')

    prompt = f"""
You are an expert AI-powered software engineering instructor and curriculum developer. Your task is to generate a **complete, structured, beginner-friendly training module** for someone who wants to learn **{learner.learning_goals}**. The learner has **{learner.experience_level}** experience and prefers a **{learner.learning_style}** learning style.

Assume the learner:
- Is starting from scratch
- Is using a **Windows PC**
- Will use **Visual Studio Code** as their development environment
- Has no prior programming or setup knowledge
- Will complete the course in self-paced, modular steps on a web-based learning platform

Structure the training module in the following SECTIONS. Use **clear markdown formatting** and keep explanations extremely detailed and descriptive. Use a **conversational, friendly tone**, avoid jargon, and **explain every step as if teaching a beginner**.

---

### 🔠 1. Vocabulary (20+ terms)
For each key programming term:
- Define it clearly in plain English
- Provide **detailed, beginner-safe explanation**
- Include a complete code example (in {learner.learning_goals}) with:
  - Inline comments explaining every line
  - Real-world use case in a sentence
- Terms to cover must include: variable, function, loop, condition, list/array, string, integer, boolean, class/object, syntax, IDE, comment, error, and more

---

### 💡 2. Common Uses of {learner.learning_goals}
List 5–8 **practical applications** of this language. For each one:
- Describe the use case in plain English
- Explain any technical terms used (e.g., “web framework”, “data pipeline”, etc.)
- Include real-world context (e.g., “Used by Instagram to build their backend”)
- Suggest relevant tools or libraries, with explanations (e.g., “Flask is a lightweight web framework that lets you build websites using Python”)
- Add a **video resource** (YouTube preferred) matched to {learner.learning_style}

---

### 🛠️ 3. Language Overview + Setup (Beginner-Safe)
Create a full walkthrough for setting up {learner.learning_goals} on Windows using **Visual Studio Code**.

For each step:
- Give precise, numbered instructions
- Include a plain-English explanation of WHY the step is necessary
- Tell the user what they should expect to see on screen
- Recommend **YouTube video tutorials** suited to {learner.learning_style} that demonstrate the setup visually

Must include:
1. Installing the language runtime (e.g., Python, Java JDK)
2. Installing Visual Studio Code
3. Installing the required language extensions in VS Code
4. Creating the first project folder
5. Creating the first source code file
6. Writing and running a “Hello World” program

---

### 💻 4. Real-World Code Examples (Copy-Paste Ready + Teaching Instructions)
Provide 2–3 fully runnable examples that:
- Solve beginner-appropriate problems
- Are **realistic** and immediately useful
- Come with **detailed inline code comments** explaining every single line
- Use consistent indentation, naming, and clarity
- Include instructions such as:
  - Open VS Code
  - Create a new file named `example_name.py`
  - Copy and paste the code
  - How to run it in the terminal or using “Run Python File in Terminal”
  - What output to expect
  - What common errors could occur and how to fix them

---

### 🧪 5. Section Quizzes (Auto-Scored + Separated Answer Key)
After each section above (Vocabulary, Common Uses, Setup, Real Examples), provide:
- A short **quiz with 3–5 questions**
- Use a mix of formats:
  - Multiple Choice
  - True/False
  - Code Analysis (“What does this do?”)
- Each question must be **tagged** with the concept it tests (e.g., `[Variables]`, `[Loops]`)
- **Important**: Show **only the questions first**, followed by a clearly separated section titled `Answer Key`
- After each answer in the key, include:
  - Correct answer
  - Short explanation of why it’s correct
  - Concept tag again (to support tracking weaknesses)
- Include **scoring instructions** at the top of each quiz:
  > "Score yourself: +1 for each correct answer. Keep track of incorrect answers and their tags — these will be used later to recommend personalized next steps."

---

### 🧠 6. Final Exam (10 Questions)
- Create 10 diverse questions covering **all content from the module**
- Use a mix of formats: MCQ, True/False, code output, small debugging task
- Tag each question with a concept (e.g., `[Syntax]`, `[Functions]`)
- Present all questions in one block
- Below that, add an `Answer Key` section with:
  - Correct answer
  - Explanation
  - Associated tag
- **Scoring Instructions**:
  > “Tally your score out of 10. Record the tags from any questions you missed. These tags will be used to determine your areas of improvement.”

---

### 📈 DO NOT Generate the Next Topics Section
This comes only **after** the final exam is completed and analyzed. The AI system will use incorrect answers and their concept tags to identify weak areas and recommend specific topics matched to the user's learning style.

---

### 🎓 Format & Style Reminders
- Use markdown headings and bolding for clear readability
- Use beginner-friendly, conversational tone (no jargon, no assumptions)
- Always explain *why* something is being done
- Include visuals (e.g., screenshots or video links) when helpful
- Comment every line of code
- Tag every quiz/exam question for concept tracking


"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful AI tutor."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        content = response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return jsonify({'error': 'Failed to generate session'}), 500

    session = LearningSession(
        learner_id=learner.id,
        topic=topic,
        content=content
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({
        'id': session.id,
        'topic': session.topic,
        'content': session.content
    }), 201

@app.route('/api/learners/<int:learner_id>/sessions', methods=['GET'])
def get_sessions(learner_id):
    sessions = LearningSession.query.filter_by(learner_id=learner_id).all()
    return jsonify([{
        'id': s.id,
        'topic': s.topic,
        'content': s.content,
        'created_at': s.created_at.isoformat()
    } for s in sessions])

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
