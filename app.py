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

# OpenAI configuration - Updated for latest API
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

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
        topic = data.get('topic', 'Personalized Learning Session')
        
        # Enhanced AI content generation with better prompts
        try:
            if client.api_key:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system", 
                            "content": f"""You are an expert AI tutor specializing in {learner.learning_goals}. 
                            Create engaging, personalized learning content for a {learner.experience_level} level learner. 
                            Use a friendly, encouraging tone and include practical examples. 
                            Structure your response with clear sections and actionable steps."""
                        },
                        {
                            "role": "user", 
                            "content": f"""Create a comprehensive learning session about {topic} for {learner.username}. 
                            
                            Please include:
                            1) 🎯 Learning Objectives (what they'll achieve)
                            2) 📚 Key Concepts (core ideas explained simply)
                            3) 💡 Real-World Examples (practical applications)
                            4) 🛠️ Hands-On Activity (something they can do right now)
                            5) ✅ Quick Check (way to verify understanding)
                            
                            Make it engaging and appropriate for {learner.experience_level} level in {learner.learning_goals}."""
                        }
                    ],
                    max_tokens=1000,
                    temperature=0.7
                )
                ai_content = response.choices[0].message.content
            else:
                ai_content = f"""🎯 **Welcome to Your Personalized Learning Session!**

**Topic:** {topic}
**Tailored for:** {learner.experience_level} level in {learner.learning_goals}

📚 **What You'll Learn:**
This session is specifically designed for your current skill level and learning goals.

💡 **Key Focus Areas:**
- Core concepts in {learner.learning_goals}
- Practical applications you can use immediately
- Step-by-step guidance for {learner.experience_level} learners

🛠️ **Next Steps:**
Ready to dive deeper? Use the 'Generate Practice Content' button to get personalized exercises!

*Note: Connect your OpenAI API key for fully personalized AI-generated content.*"""
        except Exception as ai_error:
            logger.warning(f"OpenAI API error: {ai_error}")
            ai_content = f"""🎯 **Learning Session: {topic}**

Welcome {learner.username}! This session is designed for your {learner.experience_level} level in {learner.learning_goals}.

📚 **Session Overview:**
Let's explore {topic} with content tailored specifically for you.

💡 **Learning Path:**
We'll build on your current knowledge and help you advance to the next level.

🛠️ **Ready to Practice?**
Click 'Generate Practice Content' for personalized exercises!"""
        
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
            'message': '🎉 Learning session created successfully!'
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
        
        # Enhanced AI content generation with much better prompts
        try:
            if client.api_key:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system", 
                            "content": f"""You are an expert AI tutor creating practice content for {learner.username}, 
                            a {learner.experience_level} learner studying {learner.learning_goals}. 
                            Create engaging, challenging, and practical exercises that build real skills. 
                            Use emojis and clear formatting to make content visually appealing."""
                        },
                        {
                            "role": "user", 
                            "content": f"""Generate 3 diverse, engaging practice exercises for {learner.learning_goals} at {learner.experience_level} level.

                            For each exercise, include:
                            - 🎯 Clear objective
                            - 📋 Step-by-step instructions  
                            - ⏱️ Estimated time to complete
                            - 🏆 Success criteria
                            
                            Exercise types to include:
                            1) 🛠️ **Hands-On Project** - Something they can build/create
                            2) 🧩 **Problem-Solving Challenge** - A real-world scenario to solve
                            3) 🎮 **Interactive Learning Game** - A fun way to practice skills
                            
                            Make each exercise specific, actionable, and directly relevant to {learner.learning_goals}.
                            Tailor the difficulty and complexity for {learner.experience_level} level."""
                        }
                    ],
                    max_tokens=800,
                    temperature=0.8
                )
                ai_content = response.choices[0].message.content
            else:
                ai_content = f"""🎯 **Personalized Practice Content for {learner.username}**

**Tailored for:** {learner.experience_level} level in {learner.learning_goals}

## 🛠️ **Exercise 1: Hands-On Project**
⏱️ *Time: 30-45 minutes*

Create a practical project that applies {learner.learning_goals} concepts. Start with the fundamentals and build something you can use in real life.

🏆 **Success Criteria:** Complete a working example that demonstrates your understanding.

## 🧩 **Exercise 2: Problem-Solving Challenge**  
⏱️ *Time: 20-30 minutes*

Analyze a real-world scenario related to {learner.learning_goals}. Break down the problem, identify key components, and propose a solution.

🏆 **Success Criteria:** Present a clear solution with reasoning.

## 🎮 **Exercise 3: Interactive Learning Game**
⏱️ *Time: 15-25 minutes*

Engage with {learner.learning_goals} concepts through an interactive challenge. Test your knowledge while having fun!

🏆 **Success Criteria:** Complete the challenge and identify areas for improvement.

---
💡 **Pro Tip:** Each exercise builds on the previous one. Complete them in order for the best learning experience!

*Connect your OpenAI API key for fully personalized, detailed exercises!*"""
        
        except Exception as ai_error:
            logger.warning(f"OpenAI API error: {ai_error}")
            ai_content = f"""✨ **Personalized Practice Content Generated for {learner.username}!**

🎯 **Tailored for your {learner.experience_level} level in {learner.learning_goals}**

## 📚 **Practice Exercises:**

### 1. 🛠️ **Concept Application**
Apply the key principles we've discussed to solve a real-world scenario in {learner.learning_goals}.

### 2. 🧠 **Critical Thinking Challenge**  
Analyze the relationship between different concepts and explain how they connect in practical applications.

### 3. 🎯 **Practical Project**
Create a small project that demonstrates your understanding of {learner.learning_goals} at the {learner.experience_level} level.

---
💡 **Each exercise is designed to match your current skill level and learning goals!**

🚀 **Ready to level up?** Complete these exercises and track your progress."""
        
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
            'message': '🎉 Personalized practice content generated successfully!'
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
