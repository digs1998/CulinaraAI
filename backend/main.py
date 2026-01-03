# backend/main.py

import sys
import os
import logging
from pathlib import Path
from typing import Optional, Dict, List
import asyncio
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# --------------------------------------------------
# Ensure current directory is on PYTHONPATH for Docker compatibility
# --------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# --------------------------------------------------
# Local imports
# --------------------------------------------------
from rag_engine import RecipeRAGEngine
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
        # Check if Supabase is configured (new architecture)
        use_supabase = os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY")

        if use_supabase:
            # NEW: Use Supabase with pgvector
            logger.info("📊 Using Supabase PostgreSQL + pgvector")
            from rag_engine_supabase import SupabaseRAGEngine

            rag_engine = SupabaseRAGEngine()

            # Get recipe count from Supabase
            stats = rag_engine.get_statistics()
            logger.info(f"📊 Supabase has {stats['total_recipes']} recipes, {stats['total_embeddings']} embeddings")

            if stats['total_recipes'] == 0:
                logger.warning("⚠️  Supabase has no recipes! Run GitHub Actions scraper or scripts/scrape_recipes.py")

            logger.info("✅ RAG Engine ready with Supabase")

        else:
            # OLD: Fall back to ChromaDB (backward compatibility)
            logger.info("📊 Using ChromaDB (legacy mode - consider migrating to Supabase)")
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

        # Initialize MCP Orchestrator (works with both engines)
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
class UserPreferences(BaseModel):
    diets: List[str]
    skill: str
    servings: int
    goal: str

class ChatRequest(BaseModel):
    message: str
    preferences: Optional[UserPreferences] = None

class RecipeResult(BaseModel):
    title: str
    ingredients: List[str]
    instructions: List[str]
    facts: Dict
    source: str
    score: float

class CollectionPage(BaseModel):
    title: str
    url: str

class ChatResponse(BaseModel):
    response: str
    recipes: List[RecipeResult]
    facts: Optional[List[str]] = []
    collection_pages: Optional[List[CollectionPage]] = []

# --------------------------------------------------
# MCP Pipeline
# --------------------------------------------------
def mcp_process_query(query: str, preferences: Optional[UserPreferences] = None) -> Dict:
    if not mcp_orchestrator:
        raise RuntimeError("MCP Orchestrator not initialized")

    logger.info("=" * 60)
    logger.info(f"🎯 MCP Orchestrator Processing: '{query}'")
    if preferences:
        logger.info(f"👤 User Preferences: diets={preferences.diets}, skill={preferences.skill}, servings={preferences.servings}, goal={preferences.goal}")
    logger.info("=" * 60)

    # Step 1: Process query via MCP orchestrator
    orchestrator_result = mcp_orchestrator.process_query(query, preferences=preferences)

    recipes_list = []
    facts_list = orchestrator_result.get("facts", [])

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

    # Step 3: If no RAG DB results, use pre-scraped and filtered recipes from orchestrator
    elif orchestrator_result.get("has_web_results"):
        logger.info("🌐 Using web search results")
        web_results = orchestrator_result.get("web_results", {})

        # Use the pre-scraped, filtered recipes from orchestrator (already limited to 3)
        web_recipes = web_results.get("recipes", [])

        if web_recipes:
            logger.info(f"✅ Using {len(web_recipes)} pre-scraped recipes from orchestrator")
            for recipe in web_recipes:
                recipes_list.append({
                    "title": recipe.get("title", "Recipe"),
                    "ingredients": recipe.get("ingredients", []),
                    "instructions": recipe.get("instructions", []),
                    "facts": recipe.get("facts", {}),
                    "source": recipe.get("source", "web"),
                    "score": 95.0  # High score for web results since they matched search
                })
                logger.info(f"  ✅ Added recipe: {recipe.get('title', 'Unknown')[:50]}")
        else:
            logger.warning("⚠️ No recipes available from web search after filtering")

    logger.info(f"💡 Generated {len(facts_list)} culinary facts")
    if facts_list:
        logger.info("📋 Facts being returned:")
        for i, fact in enumerate(facts_list, 1):
            logger.info(f"   {i}. {fact[:100]}")
    else:
        logger.warning("⚠️ No facts generated for this query!")

    return {
        "response": orchestrator_result.get("message", "I couldn't find relevant recipes."),
        "recipes": recipes_list,
        "facts": facts_list,
        "collection_pages": orchestrator_result.get("collection_pages", [])
    }

# --------------------------------------------------
# Routes
# --------------------------------------------------
@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # Start timing
    start_time = time.time()
    logger.info(f"⏱️  Query started at {time.strftime('%H:%M:%S')}: '{req.message[:50]}...'")

    if not rag_engine or not mcp_orchestrator:
        raise HTTPException(status_code=500, detail="Engines not initialized")

    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        result = mcp_process_query(req.message.strip(), preferences=req.preferences)

        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        logger.info(f"⏱️  Query completed in {elapsed_time:.2f} seconds")

        # Log warning if query took too long
        if elapsed_time > 8.0:
            logger.warning(f"⚠️  Query exceeded 8 second target! Took {elapsed_time:.2f}s")
        else:
            logger.info(f"✅ Query completed within target time ({elapsed_time:.2f}s < 8s)")
        
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
        
        response_data = {
            "response": result.get("response", ""),
            "recipes": validated_recipes,
            "facts": result.get("facts", []),
            "collection_pages": result.get("collection_pages", [])
        }

        logger.info(f"📤 Sending response with {len(response_data['facts'])} facts")

        return response_data
    except Exception as e:
        logger.exception("❌ MCP pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------
# User Preferences Endpoints
# --------------------------------------------------
class SavePreferencesRequest(BaseModel):
    session_id: str
    preferences: UserPreferences

class PreferencesResponse(BaseModel):
    success: bool
    message: str
    preferences: Optional[UserPreferences] = None

@app.post("/api/preferences/save", response_model=PreferencesResponse)
def save_preferences(req: SavePreferencesRequest):
    """Save user preferences to database"""
    try:
        # Check if Supabase is available
        use_supabase = os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY")

        if not use_supabase:
            return PreferencesResponse(
                success=False,
                message="Database not configured. Preferences will be stored locally only."
            )

        from supabase import create_client

        supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )

        # Upsert preferences (insert or update)
        data = {
            "session_id": req.session_id,
            "diets": req.preferences.diets,
            "skill": req.preferences.skill,
            "servings": req.preferences.servings,
            "goal": req.preferences.goal
        }

        result = supabase.table("user_preferences").upsert(data).execute()

        logger.info(f"💾 Saved preferences for session {req.session_id[:8]}...")

        return PreferencesResponse(
            success=True,
            message="Preferences saved successfully",
            preferences=req.preferences
        )
    except Exception as e:
        logger.exception("❌ Failed to save preferences")
        return PreferencesResponse(
            success=False,
            message=f"Failed to save preferences: {str(e)}"
        )

@app.get("/api/preferences/{session_id}", response_model=PreferencesResponse)
def get_preferences(session_id: str):
    """Retrieve user preferences from database"""
    try:
        # Check if Supabase is available
        use_supabase = os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY")

        if not use_supabase:
            return PreferencesResponse(
                success=False,
                message="Database not configured"
            )

        from supabase import create_client

        supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )

        result = supabase.table("user_preferences").select("*").eq("session_id", session_id).execute()

        if result.data and len(result.data) > 0:
            prefs_data = result.data[0]
            preferences = UserPreferences(
                diets=prefs_data["diets"],
                skill=prefs_data["skill"],
                servings=prefs_data["servings"],
                goal=prefs_data["goal"]
            )

            logger.info(f"📥 Retrieved preferences for session {session_id[:8]}...")

            return PreferencesResponse(
                success=True,
                message="Preferences retrieved successfully",
                preferences=preferences
            )
        else:
            return PreferencesResponse(
                success=False,
                message="No preferences found for this session"
            )
    except Exception as e:
        logger.exception("❌ Failed to retrieve preferences")
        return PreferencesResponse(
            success=False,
            message=f"Failed to retrieve preferences: {str(e)}"
        )

# --------------------------------------------------
# Serve Frontend Static Files (for production deployment)
# --------------------------------------------------
# Mount frontend build directory if it exists
# Check both local dev path and Docker/Railway path
frontend_paths = [
    Path(__file__).parent / "frontend" / "dist",  # Docker/Railway path
    Path(__file__).parent.parent / "frontend" / "dist",  # Local dev path
]

frontend_dist = None
for path in frontend_paths:
    if path.exists():
        frontend_dist = path
        break

if frontend_dist:
    logger.info(f"📦 Serving frontend from {frontend_dist}")
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
else:
    logger.warning("⚠️ Frontend dist folder not found. API-only mode.")

# --------------------------------------------------
# Local Run
# --------------------------------------------------
if __name__ == "__main__":
    # Use PORT environment variable (Railway uses 8080) or default to 8000 for local dev
    port = int(os.getenv("PORT", 8000))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )