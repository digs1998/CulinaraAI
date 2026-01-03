# CulinaraAI - Your AI-Powered Culinary Companion

<div align="center">

**The most advanced AI recipe discovery platform powered by cutting-edge RAG technology, multi-LLM orchestration, and intelligent web scraping.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-00a393?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61dafb?style=for-the-badge&logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178c6?style=for-the-badge&logo=typescript)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?style=for-the-badge&logo=docker)](https://www.docker.com/)

[Features](#-features) • [Tech Stack](#-tech-stack) • [Quick Start](#-quick-start) • [Docker](#-docker-deployment) • [Architecture](#-architecture)

</div>

---

## What Makes CulinaraAI Special?

CulinaraAI isn't just another recipe app—it's a **next-generation AI culinary assistant** that combines:

- **Dual-Pipeline RAG Architecture** - Searches Supabase vector database first, falls back to intelligent web scraping
- **Multi-LLM Orchestration** - Uses Groq (Llama 3.3 70B) and Google Gemini for optimal performance
- **Advanced Web Scraping** - Powered by Crawl4AI and MCP (Model Context Protocol) for real-time recipe extraction
- **Beautiful, Immersive UI** - Animated welcome screen, smooth transitions, and intuitive design
- **Blazing Fast** - Supabase PostgreSQL + pgvector for semantic similarity search
- **Educational Facts** - LLM-generated "Did you know?" culinary trivia for every search
- **Hot Reload Development** - Live updates for both frontend and backend during development

---

## Features

### Core Capabilities

- **Smart Recipe Search**: Natural language queries like "healthy pasta recipes" or "vegan desserts."
- **Dual-Source Intelligence**:
  - Primary: Supabase PostgreSQL + pgvector with embedded recipes
  - Fallback: Real-time web scraping from top recipe sites
- **LLM-Powered Summaries**: Friendly, conversational recipe introductions
- **Dynamic Facts Generation**: Learn interesting trivia about ingredients with every search
- **Similarity Scoring**: Advanced semantic search with pgvector similarity
- **Recipe Context**: Full ingredients, instructions, prep/cook time, servings, and more

### Advanced Features

- **Multi-LLM Fallback Chain**: Groq → Gemini → Graceful degradation
- **MCP Integration**: Model Context Protocol for structured recipe scraping
- **Chunked Ingestion**: Smart recipe chunking for better vector embeddings
- **CORS Support**: Secure cross-origin requests
- **RESTful API**: Clean, well-documented endpoints
- **Docker Support**: One-command deployment with hot reload
- **Responsive Design**: Works beautifully on desktop, tablet, and mobile

### User Experience

- Animated floating food emojis
- Gradient text and modern design
- Quick-start recipe suggestions
- Mobile-responsive interface
- Smooth loading states
- Conversational AI responses

---

## Tech Stack

### Backend Powerhouse
- **FastAPI** - Lightning-fast async Python web framework
- **Supabase** - PostgreSQL database with pgvector extension
- **pgvector** - Vector similarity search in PostgreSQL
- **Groq API** - Ultra-fast LLM inference (Llama 3.3 70B)
- **Google Gemini** - Advanced LLM for summaries and facts
- **Crawl4AI** - Intelligent web crawler for recipe extraction
- **Model Context Protocol (MCP)** - Structured scraping protocol
- **Uvicorn** - ASGI server for production deployment

### Frontend Excellence
- **React 18** - Modern UI framework with hooks
- **TypeScript** - Type-safe development
- **Vite** - Next-gen frontend tooling with HMR
- **CSS-in-JS** - Inline styles for component isolation

### Data & Embeddings
- **Google Generative AI** - Text embeddings (embedding-001)
- **JSONL Processing** - Efficient recipe data ingestion
- **Semantic Chunking** - Smart recipe splitting for better embeddings

### DevOps & Tooling
- **Docker** - Containerized deployment
- **Docker Compose** - Multi-container orchestration
- **Python 3.11+** - Modern Python features
- **Node.js 20+** - Latest LTS runtime
- **Git** - Version control

---

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Node.js 20 or higher (LTS recommended)
- Supabase account and project (for database)
- API Keys:
  - [Supabase URL and Key](https://supabase.com/)
  - [Google Gemini API Key](https://ai.google.dev/)
  - [Groq API Key](https://console.groq.com/)

### Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/CulinaraAI.git
cd CulinaraAI
```

#### 2. Set Up Environment Variables
```bash
# Create .env file in the root directory
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
SUPABASE_URL='your-supabase-project-url'
SUPABASE_KEY='your-supabase-anon-key'
GEMINI_API_KEY='your-gemini-api-key-here'
GROQ_API_KEY='your-groq-api-key-here'

PORT=8000
ALLOWED_ORIGINS='http://localhost:5173,http://localhost:3000'
VITE_API_URL=http://localhost:8000
ENVIRONMENT='development'
```

### Running Locally (Development)

#### Terminal 1: Backend (FastAPI + MCP Server)
```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
python main.py
```

Backend running at: **http://localhost:8000**
API Documentation: **http://localhost:8000/docs**

#### Terminal 2: Frontend (React + Vite)
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend running at: **http://localhost:5173**

---

## Docker Deployment

### One-Command Setup

```bash
# Build and run everything
docker-compose up --build

# Or run in background (detached mode)
docker-compose up -d --build
```

### What You Get

- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **Hot Reload**: Code changes auto-refresh
- **Isolated Network**: Containers communicate securely
- **Auto-Restart**: Services recover from crashes

### Docker Commands

```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after changes
docker-compose up --build

# Shell access
docker exec -it culinara-backend bash
docker exec -it culinara-frontend sh
```

📖 **All Docker commands and troubleshooting info are included above!**

---

## 🗄️ Data Management

### How Recipe Data is Stored

CulinaraAI uses **Supabase PostgreSQL with pgvector** for persistent, scalable storage:

#### **Supabase Database Architecture**
- **PostgreSQL**: Reliable, ACID-compliant relational database
- **pgvector Extension**: Efficient vector similarity search
- **Embeddings**: Google Generative AI text embeddings (768 dimensions)
- **Cloud-Native**: Data persists across deployments
- **Scalable**: No re-ingestion needed on redeploys

#### **Data Sources**
- Recipe websites (via web scraping with GitHub Actions)
- Real-time web scraping fallback
- API integrations (future)

### Database Setup

The database is managed in Supabase with:
- `recipes` table for recipe data
- `search_recipes()` RPC function for vector similarity search
- `get_database_stats()` RPC function for statistics
- Automatic embedding generation via scraper scripts

**For data ingestion, see the GitHub Actions workflows or run scraper scripts manually.**

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         User Query                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   MCP Orchestrator                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Step 1: RAG Database Search (Supabase + pgvector) │    │
│  │  • Semantic similarity search                       │    │
│  │  • Vector distance calculation                      │    │
│  │  • Threshold filtering (>0.35 similarity)          │    │
│  └─────────────────────────┬───────────────────────────┘    │
│                            │                                 │
│                            ▼                                 │
│                   ┌────────────────┐                        │
│                   │  Results Found? │                        │
│                   └────┬───────┬───┘                        │
│                       YES      NO                            │
│                        │       │                             │
│  ┌─────────────────────┘       └──────────────────────┐    │
│  │                                                      │    │
│  ▼                                                      ▼    │
│  Step 2A: Use DB Results              Step 2B: Web Search   │
│  • Get full recipe context             • MCP web search     │
│  • LLM summarization (Groq/Gemini)     • Scrape with MCP    │
│  • Generate facts                      • LLM summarization  │
│                                         • Generate facts     │
│  └───────────────┬───────────────────────────┬─────────────┘
│                  │                           │
│                  └──────────┬────────────────┘
│                             │
│                             ▼
│                  ┌──────────────────────┐
│                  │   Combine Results     │
│                  │   • Primary source    │
│                  │   • LLM summary       │
│                  │   • Fun facts         │
│                  │   • Recipe cards      │
│                  └──────────┬────────────┘
└─────────────────────────────┼─────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  User Response    │
                    │  • Summary text   │
                    │  • Recipe cards   │
                    │  • Did you know?  │
                    └──────────────────┘
```

### Key Components

1. **Frontend (React)**
   - User interface with animations
   - API communication
   - Recipe display

2. **MCP Orchestrator**
   - Query routing logic
   - Multi-source coordination
   - LLM orchestration

3. **RAG Engine**
   - Vector database search
   - Semantic similarity
   - Context retrieval

4. **Web Search Pipeline**
   - MCP tools for search
   - Recipe scraping
   - Real-time extraction

5. **LLM Services**
   - Groq (primary, fast)
   - Gemini (fallback, reliable)
   - Summary generation
   - Facts generation

---

## Project Structure

```
CulinaraAI/
├── backend/
│   ├── main.py                      # FastAPI entry point
│   ├── rag_engine.py                # RAG search engine
│   ├── services/
│   │   ├── mcp_orchestrator.py      # Multi-source orchestrator
│   │   └── recipe_scraper_pipeline.py  # MCP web scraping
│   ├── data/
│   │   ├── run_ingestion.py         # Data ingestion pipeline
│   │   └── scrape/
│   │       ├── foodScrapper.py      # Web crawler (Crawl4AI)
│   │       └── generateEmbeddings.py # Embedding generation
│   ├── rag_engine_supabase.py      # Supabase RAG engine
│   ├── requirements.txt             # Python dependencies
│   ├── Dockerfile                   # Backend container
│   └── .dockerignore                # Docker ignore rules
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx    # Main chat UI
│   │   │   ├── recipesResults.tsx   # Recipe cards
│   │   │   └── Onboarding.tsx       # User onboarding
│   │   ├── services/
│   │   │   └── api.ts               # API client
│   │   └── types/
│   │       └── index.ts             # TypeScript types
│   ├── package.json                 # Node.js dependencies
│   ├── Dockerfile                   # Frontend container
│   └── .dockerignore                # Docker ignore rules
├── docker-compose.yml               # Multi-container setup
├── .env                             # Environment variables
├── DOCKER_README.md                 # Docker guide
└── README.md                        # This file
```

---

## API Endpoints

### Main Endpoints

```http
POST /chat
Content-Type: application/json

{
  "message": "healthy pasta recipes"
}
```

**Response:**
```json
{
  "response": "I found 3 delicious pasta recipes...",
  "recipes": [...],
  "facts": ["Did you know that pasta..."],
  "has_database_results": true,
  "has_web_results": false
}
```

### Health Check
```http
GET /health
```

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Example Queries

Try these to see CulinaraAI in action:

- "quick and easy dinner ideas."
- "vegan desserts under 30 minutes."
- "healthy breakfast recipes."
- "pasta recipes with chicken."
- "gluten-free meal prep."
- "traditional Italian dishes."
- "spicy Asian stir-fry."

---

## Development

### Backend Development
```bash
# Install dev dependencies
pip install -r requirements.txt

# Run with auto-reload
python main.py

# Run tests (if available)
pytest
```

### Frontend Development
```bash
# Install dependencies
npm install

# Run dev server with HMR
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Supabase project URL | ✅ Yes |
| `SUPABASE_KEY` | Supabase anon/service key | ✅ Yes |
| `GEMINI_API_KEY` | Google Gemini API key | ✅ Yes |
| `GROQ_API_KEY` | Groq LLM API key | ✅ Yes |
| `PORT` | Backend port (default: 8000) | ❌ No |
| `ALLOWED_ORIGINS` | CORS allowed origins | ❌ No |
| `VITE_API_URL` | Frontend API URL | ❌ No |
| `ENVIRONMENT` | dev/production | ❌ No |

---

## Deployment

### Railway (Full-Stack Single Service)

The project includes a **multi-stage Dockerfile** that builds both frontend and backend into a single container on port 8080:

1. **Set up Supabase** - Create a project and set up the database schema
2. **Push to GitHub**
3. **Connect to Railway** - Import your repo
4. **Add Environment Variables**:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `GEMINI_API_KEY`
   - `GROQ_API_KEY`
   - `ENVIRONMENT=production`
5. **Deploy** - Railway auto-detects the Dockerfile and builds everything

The backend automatically serves the frontend's static files.

### Docker (Local Development)
```bash
docker-compose up --build
```

### Separate Deployments (Alternative)

**Backend (Railway):**
1. Deploy `backend/` folder only
2. Port 8080 (automatic)
3. Set environment variables:
   - `SUPABASE_URL` - Your Supabase project URL
   - `SUPABASE_KEY` - Your Supabase anon key
   - All API keys (GEMINI_API_KEY, GROQ_API_KEY)
4. No volume needed - data persists in Supabase!

**Frontend (Vercel/Netlify):**
1. Deploy `frontend/` folder
2. Build command: `npm run build`
3. **REQUIRED**: Set `VITE_API_URL` environment variable to your Railway backend URL
   - Example: `https://your-app.up.railway.app`
4. Redeploy after setting the environment variable

📖 **Having deployment issues?** See [DEPLOYMENT_FIX.md](DEPLOYMENT_FIX.md) for detailed troubleshooting.

---

## 🤝 Contributing

We welcome contributions! Here's how:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

MIT License - feel free to use this project for learning and commercial purposes.

---

## Acknowledgments

- **Groq** - For blazing-fast LLM inference
- **Google Gemini** - For powerful AI capabilities
- **Crawl4AI** - For intelligent web scraping
- **Supabase** - For PostgreSQL database and pgvector
- **FastAPI** - For the amazing web framework
- **React Team** - For the UI library

---

## 📧 Contact

Questions? Suggestions? Reach out!

- GitHub Issues: [Create an issue](https://github.com/yourusername/CulinaraAI/issues)
- Email: digvijayyadav48@gmail.com

---

<div align="center">

**Made with ❤️**

⭐ **Star this repo if you found it helpful!** ⭐

</div>
