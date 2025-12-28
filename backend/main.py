# backend/main.py

import sys
import os
import logging
from pathlib import Path
from typing import Optional, Dict, List
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# --------------------------------------------------
# Ensure project root is on PYTHONPATH
# --------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# --------------------------------------------------
# Local imports
# --------------------------------------------------
from backend.rag_engine import RecipeRAGEngine
from services.mcp_orchestrator import MCPOrchestrator
from services.recipe_scraper_pipeline import scrape_recipe_via_mcp

# --------------------------------------------------
# Logging
# --------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CulinaraAI")

# --------------------------------------------------
# FastAPI App
# --------------------------------------------------
app = FastAPI(
    title="CulinaraAI API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Global Engines
# --------------------------------------------------
rag_engine: Optional[RecipeRAGEngine] = None
mcp_orchestrator: Optional[MCPOrchestrator] = None

# --------------------------------------------------
# Startup
# --------------------------------------------------
@app.on_event("startup")
async def startup():
    global rag_engine, mcp_orchestrator

    logger.info("🚀 Initializing CulinaraAI RAG Engine")

    try:
        from chromadb import PersistentClient

        # Try multiple possible paths where ChromaDB might exist
        possible_paths = [
            Path(__file__).parent / "chroma_db",
            Path(__file__).parent / "data" / "chroma_db",
            Path(__file__).parent.parent / "backend" / "chroma_db",
        ]
        
        chroma_dir = None
        for path in possible_paths:
            if path.exists() and (path / "chroma.sqlite3").exists():
                chroma_dir = path
                logger.info(f"📁 Found ChromaDB at: {chroma_dir}")
                break
        
        if not chroma_dir:
            # Default to first option and create it
            chroma_dir = possible_paths[0]
            chroma_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 Creating new ChromaDB at: {chroma_dir}")
        
        # Use PersistentClient for reliability
        chroma_client = PersistentClient(path=str(chroma_dir))

        collection = chroma_client.get_or_create_collection("recipes")
        
        recipe_count = collection.count()
        logger.info(f"📊 Collection has {recipe_count} recipes")
        
        if recipe_count == 0:
            logger.warning("⚠️  ChromaDB collection is empty! Run ingestion script first.")
        
        rag_engine = RecipeRAGEngine(chroma_collection=collection)

        logger.info("✅ RAG Engine ready with ChromaDB")

        # Initialize MCP Orchestrator
        from services.mcp_tools import MCPRecipeTools
        mcp_tools = MCPRecipeTools()
        mcp_orchestrator = MCPOrchestrator(rag_engine=rag_engine, mcp_tools=mcp_tools)
        logger.info("✅ MCP Orchestrator ready")

    except Exception as e:
        logger.exception("❌ Startup failed")
        raise RuntimeError(e)

# --------------------------------------------------
# Schemas
# --------------------------------------------------
class ChatRequest(BaseModel):
    query: Optional[str] = None
    message: Optional[str] = None

class RecipeResult(BaseModel):
    title: str
    ingredients: List[str]
    instructions: List[str]
    facts: Dict
    source: str
    score: float

class ChatResponse(BaseModel):
    response: str
    recipes: List[RecipeResult]

# --------------------------------------------------
# MCP Pipeline
# --------------------------------------------------
def mcp_process_query(query: str) -> Dict:
    if not mcp_orchestrator:
        raise RuntimeError("MCP Orchestrator not initialized")

    logger.info("=" * 60)
    logger.info(f"🎯 MCP Orchestrator Processing: '{query}'")
    logger.info("=" * 60)

    # Step 1: Process query via MCP orchestrator
    orchestrator_result = mcp_orchestrator.process_query(query)

    recipes_list = []

    # Step 2: If RAG DB had results, include them
    if orchestrator_result.get("has_database_results"):
        logger.info("📚 Using database results")
        for r in orchestrator_result.get("rag_results", {}).get("results", []):
            meta = r.get("metadata", {})
            # Convert similarity score to percentage (0.0-1.0 to 0-100%)
            score_percentage = round(float(r.get("score", 0.0)) * 100, 1)
            recipes_list.append({
                "title": meta.get("title", "Recipe"),
                "ingredients": meta.get("ingredients", []),
                "instructions": meta.get("instructions", []),
                "facts": meta.get("facts", {}),
                "source": meta.get("url", "database"),
                "score": score_percentage
            })
        logger.info(f"✅ Added {len(recipes_list)} recipes from database")

    # Step 3: If no RAG DB results, scrape URLs from web search
    elif orchestrator_result.get("has_web_results"):
        logger.info("🌐 Using web search results")
        web_results = orchestrator_result.get("web_results", {})
        search_result = web_results.get("search_result", {})
        urls = [r.get("url") for r in search_result.get("results", []) if r.get("url")]
        
        logger.info(f"🔍 Attempting to scrape {len(urls)} URLs from web search...")
        for idx, url in enumerate(urls[:5], 1):  # Limit to top 5 URLs
            try:
                logger.info(f"  [{idx}/{min(5, len(urls))}] Scraping: {url[:60]}...")
                recipe = scrape_recipe_via_mcp(url)
                
                # Filter out failed scrapes
                if recipe.get("title") == "Could not fetch recipe":
                    logger.warning(f"  ⚠️ Skipping failed scrape: {url[:60]}")
                    continue
                
                # Web results get 95% match (they're from search, so relevant)
                recipes_list.append({
                    "title": recipe.get("title", "Recipe"),
                    "ingredients": recipe.get("ingredients", []),
                    "instructions": recipe.get("instructions", []),
                    "facts": recipe.get("facts", {}),
                    "source": recipe.get("source", url),
                    "score": 95.0  # High score for web results since they matched search
                })
                logger.info(f"  ✅ Successfully scraped: {recipe.get('title', 'Unknown')[:50]}")
            except Exception as e:
                logger.warning(f"  ⚠️ Failed to scrape {url[:60]}: {str(e)[:100]}")
        
        logger.info(f"✅ Total successfully scraped recipes: {len(recipes_list)}")

    return {
        "response": orchestrator_result.get("message", "I couldn't find relevant recipes."),
        "recipes": recipes_list
    }

# --------------------------------------------------
# Routes
# --------------------------------------------------
@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not rag_engine or not mcp_orchestrator:
        raise HTTPException(status_code=500, detail="Engines not initialized")

    query = req.query or req.message
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        result = mcp_process_query(query.strip())
        
        # Ensure recipes have proper structure and valid scores
        validated_recipes = []
        for recipe in result.get("recipes", []):
            # Skip invalid recipes
            if not recipe.get("title") or recipe.get("title") == "Could not fetch recipe":
                continue
                
            score = recipe.get("score", 95.0)
            # Ensure score is a valid number between 0-100
            if not isinstance(score, (int, float)) or score < 0:
                score = 95.0
            
            validated_recipes.append({
                "title": recipe.get("title", "Unknown Recipe"),
                "ingredients": recipe.get("ingredients", []),
                "instructions": recipe.get("instructions", []),
                "facts": recipe.get("facts", {}),
                "source": recipe.get("source", "unknown"),
                "score": round(float(score), 1)  # Round to 1 decimal place
            })
        
        return {
            "response": result.get("response", ""),
            "recipes": validated_recipes
        }
    except Exception as e:
        logger.exception("❌ MCP pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------
# Local Run
# --------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )