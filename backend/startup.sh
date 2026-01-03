#!/bin/bash
# Startup script for Railway deployment
# Auto-detects Supabase or ChromaDB mode

echo "🚀 Starting CulinaraAI..."

# Check if Supabase is configured (new architecture)
if [ -n "$SUPABASE_URL" ] && [ -n "$SUPABASE_KEY" ]; then
    echo "📊 Supabase detected - using cloud PostgreSQL + pgvector"
    echo "   URL: $SUPABASE_URL"
    echo "✅ Skipping ChromaDB setup (data is in Supabase)"
    echo "💡 No ingestion needed on deployment - data persists in cloud!"

else
    echo "📊 Supabase not configured - using ChromaDB (legacy mode)"
    echo "💡 To use Supabase, set SUPABASE_URL and SUPABASE_KEY environment variables"

    # Railway persistent storage: Use /data volume if available
    CHROMA_DIR="${RAILWAY_VOLUME_MOUNT_PATH:-chroma_db}"

    # If Railway volume exists, symlink it to chroma_db
    if [ -n "$RAILWAY_VOLUME_MOUNT_PATH" ]; then
        echo "📦 Railway volume detected at: $RAILWAY_VOLUME_MOUNT_PATH"

        # Create chroma_db directory in volume if it doesn't exist
        mkdir -p "$RAILWAY_VOLUME_MOUNT_PATH/chroma_db"

        # Remove local chroma_db if it exists and create symlink
        rm -rf chroma_db
        ln -sf "$RAILWAY_VOLUME_MOUNT_PATH/chroma_db" chroma_db

        echo "✅ Linked chroma_db to persistent volume"
    fi

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
        echo "✅ ChromaDB exists with data ($(ls -1 chroma_db 2>/dev/null | wc -l) files)"
    fi
fi

echo "🎯 Starting FastAPI server..."
python main.py
