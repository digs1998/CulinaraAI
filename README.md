# 🍳 CulinaraAI - Your AI-Powered Culinary Companion

<div align="center">

**The most advanced AI recipe discovery platform powered by cutting-edge RAG technology, multi-LLM orchestration, and intelligent web scraping.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-00a393?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61dafb?style=for-the-badge&logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178c6?style=for-the-badge&logo=typescript)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?style=for-the-badge&logo=docker)](https://www.docker.com/)

[Features](#-features) • [Tech Stack](#-tech-stack) • [Quick Start](#-quick-start) • [Docker](#-docker-deployment) • [Architecture](#-architecture)

</div>

---

## 🌟 What Makes CulinaraAI Special?

CulinaraAI isn't just another recipe app—it's a **next-generation AI culinary assistant** that combines:

- 🧠 **Dual-Pipeline RAG Architecture** - Searches local vector database first, falls back to intelligent web scraping
- 🤖 **Multi-LLM Orchestration** - Uses Groq (Llama 3.3 70B) and Google Gemini for optimal performance
- 🕷️ **Advanced Web Scraping** - Powered by Crawl4AI and MCP (Model Context Protocol) for real-time recipe extraction
- 🎨 **Beautiful, Immersive UI** - Animated welcome screen, smooth transitions, and intuitive design
- ⚡ **Blazing Fast** - ChromaDB vector search with semantic similarity matching
- 📚 **Educational Facts** - LLM-generated "Did you know?" culinary trivia for every search
- 🔄 **Hot Reload Development** - Live updates for both frontend and backend during development

---

## ✨ Features

### 🎯 Core Capabilities

- **Smart Recipe Search**: Natural language queries like "healthy pasta recipes" or "vegan desserts"
- **Dual-Source Intelligence**:
  - Primary: Vector database with 500k+ embedded recipes (ChromaDB + Pinecone)
  - Fallback: Real-time web scraping from top recipe sites
- **LLM-Powered Summaries**: Friendly, conversational recipe introductions
- **Dynamic Facts Generation**: Learn interesting trivia about ingredients with every search
- **Similarity Scoring**: Advanced semantic search with keyword boosting
- **Recipe Context**: Full ingredients, instructions, prep/cook time, servings, and more

### 🚀 Advanced Features

- **Multi-LLM Fallback Chain**: Groq → Gemini → Graceful degradation
- **MCP Integration**: Model Context Protocol for structured recipe scraping
- **Chunked Ingestion**: Smart recipe chunking for better vector embeddings
- **CORS Support**: Secure cross-origin requests
- **RESTful API**: Clean, well-documented endpoints
- **Docker Support**: One-command deployment with hot reload
- **Responsive Design**: Works beautifully on desktop, tablet, and mobile

### 🎨 User Experience

- ✨ Animated floating food emojis
- 🌈 Gradient text and modern design
- 🎯 Quick-start recipe suggestions
- 📱 Mobile-responsive interface
- 🔄 Smooth loading states
- 💬 Conversational AI responses

---

## 🏗️ Tech Stack

### Backend Powerhouse
- **FastAPI** - Lightning-fast async Python web framework
- **ChromaDB** - Vector database for semantic recipe search
- **Pinecone** - Cloud vector database for scalability
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

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Node.js 20 or higher (LTS recommended)
- API Keys:
  - [Google Gemini API Key](https://ai.google.dev/)
  - [Pinecone API Key](https://www.pinecone.io/)
  - [Groq API Key](https://console.groq.com/)

### 📦 Installation

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
GEMINI_API_KEY='your-gemini-api-key-here'
PINECONE_API_KEY='your-pinecone-api-key-here'
GROQ_API_KEY='your-groq-api-key-here'

PORT=8000
ALLOWED_ORIGINS='http://localhost:5173,http://localhost:3000'
VITE_API_URL=http://localhost:8000
ENVIRONMENT='development'
```

### 🖥️ Running Locally (Development)

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

✅ Backend running at: **http://localhost:8000**
📚 API Documentation: **http://localhost:8000/docs**

#### Terminal 2: Frontend (React + Vite)
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

✅ Frontend running at: **http://localhost:5173**

---

## 🐳 Docker Deployment

### One-Command Setup

```bash
# Build and run everything
docker-compose up --build

# Or run in background (detached mode)
docker-compose up -d --build
```

### What You Get

- ✅ **Backend**: http://localhost:8000
- ✅ **Frontend**: http://localhost:5173
- ✅ **API Docs**: http://localhost:8000/docs
- ✅ **Hot Reload**: Code changes auto-refresh
- ✅ **Isolated Network**: Containers communicate securely
- ✅ **Auto-Restart**: Services recover from crashes

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

📖 **All Docker commands and troubleshooting info is included above!**

---

## 🗄️ Data Collection & Ingestion

### How Recipe Data is Collected

CulinaraAI uses a **sophisticated multi-source data pipeline**:

#### 1. **Web Scraping with Crawl4AI**
- 🕷️ **Intelligent Crawler**: Uses Crawl4AI for JavaScript-rendered pages
- 🎯 **Targeted Extraction**: Focuses on recipe-specific sites
- 📝 **Structured Parsing**: Extracts ingredients, instructions, metadata
- 🔄 **Rate Limiting**: Respectful crawling with delays

#### 2. **Recipe Processing**
- 📄 **JSONL Format**: Recipes stored in JSON Lines for efficient processing
- ✂️ **Smart Chunking**: Splits large recipes into semantic chunks
- 🧮 **Embedding Generation**: Google Generative AI creates vector embeddings
- 💾 **Vector Storage**: ChromaDB (local) + Pinecone (cloud)

#### 3. **Data Sources**
- Recipe websites (via web scraping)
- User-contributed recipes
- API integrations (future)

### Running Data Ingestion

```bash
cd backend

# Option 1: Full ingestion pipeline
python data/run_ingestion.py

# Option 2: Web scraping only
python data/scrape/foodScrapper.py

# Option 3: Generate embeddings
python data/scrape/generateEmbeddings.py
```

**What happens:**
1. 📥 Scrapes recipe URLs from target sites
2. 🔍 Extracts recipe data (ingredients, instructions, facts)
3. ✂️ Chunks recipes into smaller semantic units
4. 🧮 Generates embeddings using Google AI
5. 💾 Stores in ChromaDB and Pinecone
6. ✅ Ready for semantic search!

---

## 🏛️ Architecture

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
│  │  Step 1: RAG Database Search (ChromaDB/Pinecone)   │    │
│  │  • Semantic similarity search                       │    │
│  │  • Keyword matching boost                           │    │
│  │  • Threshold filtering (>0.50 similarity)          │    │
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

## 📁 Project Structure

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
│   ├── chroma_db/                   # ChromaDB storage
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

## 🎯 API Endpoints

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

## 🧪 Example Queries

Try these to see CulinaraAI in action:

- "quick and easy dinner ideas"
- "vegan desserts under 30 minutes"
- "healthy breakfast recipes"
- "pasta recipes with chicken"
- "gluten-free meal prep"
- "traditional Italian dishes"
- "spicy Asian stir-fry"

---

## 🛠️ Development

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

## 🌐 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | ✅ Yes |
| `PINECONE_API_KEY` | Pinecone vector DB key | ✅ Yes |
| `GROQ_API_KEY` | Groq LLM API key | ✅ Yes |
| `PORT` | Backend port (default: 8000) | ❌ No |
| `ALLOWED_ORIGINS` | CORS allowed origins | ❌ No |
| `VITE_API_URL` | Frontend API URL | ❌ No |
| `ENVIRONMENT` | dev/production | ❌ No |

---

## 🚀 Deployment

### Railway (Full-Stack Single Service)

The project includes a **multi-stage Dockerfile** that builds both frontend and backend into a single container on port 8080:

1. **Push to GitHub**
2. **Connect to Railway** - Import your repo
3. **Add Environment Variables**:
   - `GEMINI_API_KEY`
   - `PINECONE_API_KEY`
   - `GROQ_API_KEY`
   - `ENVIRONMENT=production`
4. **Deploy** - Railway auto-detects the Dockerfile and builds everything

The backend serves the frontend static files automatically! ✨

### Docker (Local Development)
```bash
docker-compose up --build
```

### Separate Deployments (Alternative)

**Backend (Railway):**
- Deploy `backend/` folder only
- Port 8080 (automatic)

**Frontend (Vercel/Netlify):**
- Deploy `frontend/` folder
- Build command: `npm run build`
- Set `VITE_API_URL` to your Railway backend URL

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

## 🙌 Acknowledgments

- **Groq** - For blazing-fast LLM inference
- **Google Gemini** - For powerful AI capabilities
- **Crawl4AI** - For intelligent web scraping
- **ChromaDB** - For local vector storage
- **Pinecone** - For scalable vector search
- **FastAPI** - For the amazing web framework
- **React Team** - For the UI library

---

## 📧 Contact

Questions? Suggestions? Reach out!

- GitHub Issues: [Create an issue](https://github.com/yourusername/CulinaraAI/issues)
- Email: digvijayyadav48@gmail.com

---

<div align="center">

**Made with ❤️ and AI**

⭐ **Star this repo if you found it helpful!** ⭐

</div>
