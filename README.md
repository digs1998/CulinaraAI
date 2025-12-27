# 🍳 Culinara

Gordon Ramsay-inspired cooking chatbot with RAG (Retrieval-Augmented Generation)

## Features
- 👨‍🍳 Gordon Ramsay personality
- 📖 Personalized recipe recommendations
- 🎯 RAG-powered responses (no hallucinations)
- 🔍 Smart filtering (dietary, allergies, skill level)
- ⚡ Fast & responsive

## Tech Stack
- **Backend**: FastAPI, Python 3.11
- **Frontend**: React 18, TypeScript
- **LLM**: Google Gemini 2.5 Flash
- **Deployment**: Railway + Vercel

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Gemini API Key

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your GEMINI_API_KEY to .env
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
# Add your backend URL to .env
npm start
```

## Documentation
- [Deployment Guide](docs/DEPLOYMENT.md)
- [API Documentation](docs/API.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## License
MIT