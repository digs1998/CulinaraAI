# backend/main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from contextlib import asynccontextmanager
from rag_engine import RecipeRAGEngine, get_mcp_tools
import uvicorn
import sys
from pathlib import Path
import os
from chromadb import Client
from chromadb.config import Settings
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ----------------- RAG Engine Initialization -----------------

rag_engine: Optional[RecipeRAGEngine] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_engine
    print("🚀 Initializing CulinaraAI RAG Engine with ChromaDB...")

    # Setup ChromaDB client
    chroma_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")
    chroma_client = Client(Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory=chroma_dir
    ))

    # Get or create recipe collection
    collection = chroma_client.get_or_create_collection("recipes")

    # Initialize RAG engine with Chroma collection
    rag_engine = RecipeRAGEngine(chroma_collection=collection)
    rag_engine.setup_mcp_orchestrator()

    print("✅ RAG Engine + MCP Orchestrator ready!")
    yield

# ----------------- FastAPI Setup -----------------

app = FastAPI(title="CulinaraAI API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Request/Response Models -----------------

class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class RecipeSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    filters: Optional[Dict] = None
    min_score: Optional[float] = 0.0


class RecipeResponse(BaseModel):
    id: str
    title: str
    category: Optional[str]
    rating: Optional[float]
    total_time: Optional[str]
    url: str
    score: float


class ChatResponse(BaseModel):
    message: str
    recipes: List[RecipeResponse]
    sources: List[Dict]


# ----------------- API Endpoints -----------------

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "healthy",
        "service": "Feastron API",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "chat": "POST /api/chat",
            "search": "POST /api/search",
            "stats": "GET /api/stats"
        }
    }


@app.get("/api/stats")
async def get_stats():
    """Get recipe database statistics"""
    try:
        stats = rag_engine.get_statistics()
        return stats
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error in /api/stats: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


@app.post("/api/search")
async def search_recipes(request: RecipeSearchRequest):
    """Search recipes using ChromaDB embeddings"""
    try:
        results = rag_engine.search_chroma(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            min_score=request.min_score
        )

        recipes = []
        for result in results:
            meta = result['metadata']
            recipes.append({
                "id": result['id'],
                "title": meta['title'],
                "category": meta.get('category'),
                "rating": meta.get('rating'),
                "total_time": meta.get('total_time'),
                "url": meta.get('url'),
                "score": result['score']
            })

        return {"results": recipes}

    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error in /api/search: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatMessage):
    """Main chat endpoint - Uses RAG with LLM fallback"""
    try:
        answer = rag_engine.answer_question(
            question=request.message,
            top_k=3,
            similarity_threshold=0.65
        )

        if answer.get('generated', False):
            return {
                "message": f"🤔 {answer['response']}\n\n{answer.get('message', '')}",
                "recipes": [],
                "sources": answer.get('sources', [])
            }

        results = answer['sources']
        if not results:
            return {
                "message": "I couldn't find any recipes matching your request.",
                "recipes": [],
                "sources": []
            }

        recipes = []
        for result in results:
            meta = result['metadata']
            recipes.append({
                "id": result['id'],
                "title": meta['title'],
                "category": meta.get('category'),
                "rating": meta.get('rating'),
                "total_time": meta.get('total_time'),
                "url": meta.get('url'),
                "score": result['score']
            })

        top_recipe = results[0]['metadata']
        response_message = f"I found some great options! Top match: **{top_recipe['title']}** "
        if top_recipe.get('category'):
            response_message += f"from the {top_recipe['category']} category "
        if top_recipe.get('total_time'):
            response_message += f"(takes {top_recipe['total_time']}) "
        if top_recipe.get('rating'):
            response_message += f"with a {top_recipe['rating']}/5 rating"
        response_message += ". Check out the recipes below!"

        return {
            "message": response_message,
            "recipes": recipes,
            "sources": results
        }

    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error in /api/chat: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/api/recipe/{recipe_id}")
async def get_recipe(recipe_id: str):
    """Get full recipe details"""
    try:
        details = rag_engine.get_recipe_details(recipe_id)
        if not details:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return details
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error in /api/recipe/{recipe_id}: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/api/similar/{recipe_id}")
async def get_similar_recipes(recipe_id: str, top_k: int = 5):
    """Get similar recipes"""
    try:
        similar = rag_engine.get_similar_recipes(recipe_id, top_k=top_k)
        return {"similar_recipes": similar}
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"Error in /api/similar/{recipe_id}: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


# ----------------- Run Server -----------------

if __name__ == "__main__":
    workspace_root = Path(__file__).parent.parent
    if str(workspace_root) not in sys.path:
        sys.path.insert(0, str(workspace_root))

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
