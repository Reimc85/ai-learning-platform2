import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import './App.css';

// Image imports
import AiHead from './icons/AI-Head.png';
import AiScreen from './icons/AI-Screen.png';
import Goals from './icons/goals.png';
import Intelligent from './icons/intelligent.png';
import Progress from './icons/progress.png';

// API configuration
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000';

const api = {
  createLearner: async (learnerData) => {
    const response = await fetch(`${API_BASE_URL}/api/learners`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(learnerData),
    });
    return response.json();
  },

  createSession: async (learnerId, sessionData) => {
    const response = await fetch(`${API_BASE_URL}/api/learners/${learnerId}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sessionData),
    });
    return response.json();
  },

  getSessions: async (learnerId) => {
    const response = await fetch(`${API_BASE_URL}/api/learners/${learnerId}/sessions`);
    return response.json();
  },

  generateContent: async (learnerId) => {
    const response = await fetch(`${API_BASE_URL}/api/generate-content`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ learner_id: learnerId }),
    });
    return response.json();
  }
};

// Onboarding Component
function OnboardingFlow() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    username: '',
    learningGoals: '',
    experience: 'beginner',
    learningStyle: 'combination'
  });
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleNext = async () => {
    if (step < 4) {
      setStep(step + 1);
    } else {
      setLoading(true);
      try {
        const result = await api.createLearner({
          username: formData.username,
          learning_goals: formData.learningGoals,
          experience_level: formData.experience,
          learning_style: formData.learningStyle
        });

        if (result.id) {
          localStorage.setItem('learnerId', result.id);
          navigate('/dashboard', {
            state: {
              success: true,
              username: formData.username
            }
          });
        } else {
          alert('Error creating learner profile. Please try again.');
        }
      } catch (error) {
        console.error('Error:', error);
        alert('Error creating learner profile. Please try again.');
      } finally {
        setLoading(false);
      }
    }
  };

  const handleBack = () => {
    if (step > 1) setStep(step - 1);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Welcome to AI Learning Platform</h1>
        <p>Let's personalize your learning experience</p>
      </header>

      <div className="onboarding">
        <h2>Step {step} of 4</h2>

        {step === 1 && (
          <div>
            <h3>What's your name?</h3>
            <div className="form-group">
              <label>Username:</label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => handleInputChange('username', e.target.value)}
                placeholder="Enter your username"
              />
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <h3>Which programming language would you like to learn?</h3>
            <div className="form-group">
              <label>Learning Goal (Programming Language):</label>
              <select
                value={formData.learningGoals}
                onChange={(e) => handleInputChange('learningGoals', e.target.value)}
              >
                <option value="">Select a language</option>
                <option value="Python">Python</option>
                <option value="JavaScript">JavaScript</option>
                <option value="Java">Java</option>
                <option value="C#">C#</option>
                <option value="C++">C++</option>
              </select>
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <h3>What's your experience level?</h3>
            <div className="form-group">
              <label>Experience Level:</label>
              <select
                value={formData.experience}
                onChange={(e) => handleInputChange('experience', e.target.value)}
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>
          </div>
        )}

        {step === 4 && (
          <div>
            <h3>How do you prefer to learn?</h3>
            <div className="form-group">
              <label>Learning Style:</label>
              <select
                value={formData.learningStyle}
                onChange={(e) => handleInputChange('learningStyle', e.target.value)}
              >
                <option value="combination">Combination</option>
                <option value="visual">Visual</option>
                <option value="audio">Audio</option>
                <option value="hands-on">Hands-On</option>
              </select>
            </div>
          </div>
        )}

        <div>
          {step > 1 && (
            <button onClick={handleBack} disabled={loading}>
              Back
            </button>
          )}
          <button
            onClick={handleNext}
            disabled={loading || (step === 1 && !formData.username) || (step === 2 && !formData.learningGoals)}
          >
            {loading ? 'Creating Profile...' : (step === 4 ? 'Complete Setup' : 'Next')}
          </button>
        </div>
      </div>
    </div>
  );
}

function Dashboard() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState('');
  const [welcomeMessage, setWelcomeMessage] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  const learnerId = localStorage.getItem('learnerId') || '1';

  useEffect(() => {
    if (location.state?.success && location.state.username) {
      setWelcomeMessage(`✅ Welcome, ${location.state.username}! Your learning journey has started.`);
      const timeout = setTimeout(() => setWelcomeMessage(''), 5000);
      return () => clearTimeout(timeout);
    }
  }, [location.state]);

  const handleStartSession = async () => {
    setLoading(true);
    setResult('');
    try {
      const sessionResult = await api.createSession(learnerId, { topic: 'Personalized Learning Session' });
      if (sessionResult.id) {
        loadSessions();
      } else {
        setResult(`❌ Error: ${sessionResult.error || 'Failed to create session'}`);
      }
    } catch (error) {
      console.error('Error:', error);
      setResult('❌ Error: Failed to connect to the server. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateContent = async () => {
    setLoading(true);
    setResult('');
    try {
      const contentResult = await api.generateContent(learnerId);
      if (!contentResult.success) {
        setResult(`❌ ${contentResult.message || 'Failed to generate content'}`);
      }
      loadSessions();
    } catch (error) {
      console.error('Error:', error);
      setResult('❌ Error: Failed to connect to the server. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const loadSessions = async () => {
    try {
      const sessionsData = await api.getSessions(learnerId);
      setSessions(Array.isArray(sessionsData) ? sessionsData : []);
    } catch (error) {
      console.error('Error loading sessions:', error);
    }
  };

  useEffect(() => {
    loadSessions();
  }, [learnerId]);

  return (
    <div className="App">
      <header className="App-header">
        <h1>AI Learning Platform</h1>
        <p>Your Personalized Learning Dashboard</p>
      </header>

      {welcomeMessage && <div className="success-banner">{welcomeMessage}</div>}

      <div className="dashboard">
        <div className="dashboard-section">
          <h2>Quick Actions</h2>
          <button onClick={handleStartSession} disabled={loading}>
            {loading ? 'Loading...' : 'Start Session'}
          </button>
          <button onClick={handleGenerateContent} disabled={loading}>
            {loading ? 'Loading...' : 'Generate Practice Content'}
          </button>
          <button onClick={() => navigate('/onboarding')}>
            Update Profile
          </button>
        </div>

        {result && result.includes('❌') && (
          <div className="result error">{result}</div>
        )}

        <div className="dashboard-section">
          <h2>Your Learning Sessions</h2>
          {sessions.length > 0 ? (
            <ul className="session-list">
              {sessions.map((session) => (
                <li key={session.id} className="session-item">
                  <h3>{session.topic}</h3>
                  <p>Progress: {session.progress || 0}%</p>
                  <p>Created: {new Date(session.created_at).toLocaleDateString()}</p>
                  <ReactMarkdown className="session-content">
                    {session.content}
                  </ReactMarkdown>
                </li>
              ))}
            </ul>
          ) : (
            <p>No learning sessions yet. Start your first session above!</p>
          )}
        </div>
      </div>
    </div>
  );
}

function Home() {
  const navigate = useNavigate();

  return (
    <div className="App">
      <header className="App-header">
        <h1>Personalized AI Learning Platform</h1>
        <p>Delivering personalized education by leveraging AI to dynamically generate content and adapt learning paths</p>
      </header>

      <div>
        <h2>Welcome to the Future of Learning</h2>
        <p style={{ textAlign: 'center', fontSize: '1.2rem' }}>
          <br />
          Juggling work, family, and personal growth? <br /><br />
          This platform is built for you. Learn smarter, not harder — with AI-driven lessons that fit your schedule, cut through the noise, and focus only on what you need. <br /><br />
          Upgrade your skills on your time, whether it’s 9 PM after the kids are asleep or early Sunday morning before the world wakes up. <br /><br />
          Start your journey today — your future self will thank you.
        </p>

        <button onClick={() => navigate('/onboarding')}>Start Learning Now</button>

        <div style={{ marginTop: '40px' }}>
          <h3>Key Features:</h3>
          {[{ img: AiHead, label: "AI-Powered Personalization" },
            { img: AiScreen, label: "Adaptive Learning Content" },
            { img: Goals, label: "Goal-Oriented Learning Paths" },
            { img: Intelligent, label: "Intelligent Content Generation" },
            { img: Progress, label: "Progress Tracking" }].map(({ img, label }) => (
              <div style={{ textAlign: 'center', margin: '40px 0' }} key={label}>
                <img src={img} alt={label} style={{ width: '320px', height: '320px' }} />
                <p style={{ fontSize: '1.3rem', marginTop: '10px' }}>{label}</p>
              </div>
            ))
          }

          <button onClick={() => navigate('/onboarding')}>Get Started Now</button>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/onboarding" element={<OnboardingFlow />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </Router>
  );
}

export default App;
