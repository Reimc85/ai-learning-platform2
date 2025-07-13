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
You are a senior software engineering tutor and AI educator. Your job is to create a highly detailed, user-friendly training program for someone who wants to learn {learner.learning_goals} and has {learner.experience_level} experience. Their preferred learning style is {learner.learning_style}.

Design a complete, beginner-accessible session broken into clear sections. Include practical steps, interactive tests, and real code examples compatible with Visual Studio Code on Windows. Assume the user has zero setup completed and minimal technical background.

Topic: {topic}

The program must be broken into the following sections:

1. Vocabulary
2. Common Uses
3. Language Overview + Setup
4. Real-World Code Examples
5. Section-by-Section Quizzes (with answer keys)
6. Final Challenge
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
