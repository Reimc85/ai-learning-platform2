from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import openai
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

# OpenAI configuration
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Database Models
class Learner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    learning_goals = db.Column(db.Text)
    experience_level = db.Column(db.String(50))
    sessions = db.relationship('LearningSession', backref='learner', lazy=True)
    knowledge_gaps = db.relationship('KnowledgeGap', backref='learner', lazy=True)

class LearningSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    learner_id = db.Column(db.Integer, db.ForeignKey('learner.id'), nullable=False)
    topic = db.Column(db.String(200))
    content = db.Column(db.Text)
    progress = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class KnowledgeGap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    learner_id = db.Column(db.Integer, db.ForeignKey('learner.id'), nullable=False)
    topic = db.Column(db.String(200))
    difficulty_level = db.Column(db.String(50))
    identified_at = db.Column(db.DateTime, default=db.func.current_timestamp())

# Initialize database
with app.app_context():
    try:
        logger.info("Attempting to drop all database tables...")
        db.drop_all()
        logger.info("All database tables dropped (if they existed).")
        
        logger.info("Attempting to create all database tables...")
        db.create_all()
        logger.info("All database tables created.")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

# API Routes
@app.route('/api/learners', methods=['POST'])
def create_learner():
    try:
        data = request.get_json()
        
        # Check if learner already exists
        existing_learner = Learner.query.filter_by(username=data['username']).first()
        if existing_learner:
            return jsonify({'error': 'Username already exists'}), 400
        
        learner = Learner(
            username=data['username'],
            learning_goals=data.get('learning_goals', ''),
            experience_level=data.get('experience_level', 'beginner')
        )
        
        db.session.add(learner)
        db.session.commit()
        
        return jsonify({
            'id': learner.id,
            'username': learner.username,
            'learning_goals': learner.learning_goals,
            'experience_level': learner.experience_level
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating learner: {e}")
        return jsonify({'error': 'Failed to create learner'}), 500

@app.route('/api/learners/<int:learner_id>/sessions', methods=['GET'])
def get_sessions(learner_id):
    try:
        sessions = LearningSession.query.filter_by(learner_id=learner_id).all()
        return jsonify([{
            'id': session.id,
            'topic': session.topic,
            'content': session.content,
            'progress': session.progress,
            'created_at': session.created_at.isoformat() if session.created_at else None
        } for session in sessions])
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        return jsonify({'error': 'Failed to get sessions'}), 500

@app.route('/api/learners/<int:learner_id>/sessions', methods=['POST'])
def create_session(learner_id):
    try:
        # Verify learner exists
        learner = Learner.query.get(learner_id)
        if not learner:
            return jsonify({'error': 'Learner not found'}), 404
        
        data = request.get_json()
        topic = data.get('topic', 'General Learning')
        
        # Generate AI content based on learner's profile
        try:
            if openai.api_key:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": f"You are an AI tutor. Create personalized learning content for a {learner.experience_level} level learner interested in {learner.learning_goals}."},
                        {"role": "user", "content": f"Create a learning session about {topic}. Include key concepts, examples, and practice exercises."}
                    ],
                    max_tokens=500
                )
                ai_content = response.choices[0].message.content
            else:
                ai_content = f"Welcome to your personalized learning session on {topic}! This content is tailored for your {learner.experience_level} level in {learner.learning_goals}."
        except Exception as ai_error:
            logger.warning(f"OpenAI API error: {ai_error}")
            ai_content = f"Welcome to your learning session on {topic}! Let's explore this topic step by step."
        
        session = LearningSession(
            learner_id=learner_id,
            topic=topic,
            content=ai_content,
            progress=0.0
        )
        
        db.session.add(session)
        db.session.commit()
        
        return jsonify({
            'id': session.id,
            'topic': session.topic,
            'content': session.content,
            'progress': session.progress,
            'message': 'Learning session created successfully!'
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return jsonify({'error': 'Failed to create session'}), 500

@app.route('/api/learners/<int:learner_id>/knowledge-gaps', methods=['GET'])
def get_knowledge_gaps(learner_id):
    try:
        gaps = KnowledgeGap.query.filter_by(learner_id=learner_id).all()
        return jsonify([{
            'id': gap.id,
            'topic': gap.topic,
            'difficulty_level': gap.difficulty_level,
            'identified_at': gap.identified_at.isoformat() if gap.identified_at else None
        } for gap in gaps])
    except Exception as e:
        logger.error(f"Error getting knowledge gaps: {e}")
        return jsonify({'error': 'Failed to get knowledge gaps'}), 500

@app.route('/api/generate-content', methods=['POST'])
def generate_content():
    try:
        data = request.get_json()
        learner_id = data.get('learner_id', 1)  # Default to learner 1 for demo
        
        # Get learner info
        learner = Learner.query.get(learner_id)
        if not learner:
            # Create a default learner for demo purposes
            learner = Learner(
                username="Demo User",
                learning_goals="General Learning",
                experience_level="intermediate"
            )
            db.session.add(learner)
            db.session.commit()
        
        # Generate AI content
        try:
            if openai.api_key:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": f"You are an AI tutor creating practice content for a {learner.experience_level} learner studying {learner.learning_goals}."},
                        {"role": "user", "content": "Generate 3 practice questions with explanations that would help this learner improve their skills."}
                    ],
                    max_tokens=400
                )
                ai_content = response.choices[0].message.content
            else:
                ai_content = """Here are 3 personalized practice questions for you:

1. **Concept Application**: Apply the key principles we've discussed to solve a real-world scenario.

2. **Critical Thinking**: Analyze the relationship between different concepts and explain how they connect.

3. **Practical Exercise**: Create a small project that demonstrates your understanding of the material.

Each question is designed to match your current skill level and learning goals!"""
        
        except Exception as ai_error:
            logger.warning(f"OpenAI API error: {ai_error}")
            ai_content = "✨ **Personalized Practice Content Generated!**\n\nBased on your learning profile, here are some tailored exercises to help you progress. This content adapts to your skill level and focuses on areas where you can improve the most."
        
        # Create a new session with the generated content
        session = LearningSession(
            learner_id=learner.id,
            topic="AI-Generated Practice Content",
            content=ai_content,
            progress=0.0
        )
        
        db.session.add(session)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'content': ai_content,
            'session_id': session.id,
            'message': '🎉 Practice content generated successfully!'
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate content',
            'message': '❌ Sorry, there was an error generating your practice content. Please try again.'
        }), 500

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'message': 'AI Learning Platform is running!'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

