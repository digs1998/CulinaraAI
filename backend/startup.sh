#!/bin/bash
# Startup script for Railway deployment
# Runs ingestion if ChromaDB is empty, then starts the FastAPI server

echo "🚀 Starting CulinaraAI..."

# Check if ChromaDB directory exists and has data
if [ ! -d "chroma_db" ] || [ -z "$(ls -A chroma_db 2>/dev/null)" ]; then
    echo "📊 ChromaDB is empty or doesn't exist"

    # Check if we should run ingestion (requires API keys)
    if [ -n "$GEMINI_API_KEY" ] && [ "$RUN_INGESTION" = "true" ]; then
        echo "🔄 Running data ingestion..."
        python data/run_ingestion.py || echo "⚠️ Ingestion failed, will use web search fallback"
    else
        echo "⚠️ Skipping ingestion (RUN_INGESTION not set or no API keys)"
        echo "💡 App will use web search fallback"
    fi
else
    echo "✅ ChromaDB exists with data"
fi

echo "🎯 Starting FastAPI server..."
python main.py
