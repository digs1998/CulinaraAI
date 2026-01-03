#!/bin/bash
# Startup script for Railway deployment
# Uses Supabase PostgreSQL + pgvector for vector storage

echo "🚀 Starting CulinaraAI with Supabase..."

# Check if Supabase is configured (required)
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    echo "❌ ERROR: SUPABASE_URL and SUPABASE_KEY must be set!"
    echo "💡 ChromaDB has been removed - Supabase is now required."
    echo "   Please set SUPABASE_URL and SUPABASE_KEY environment variables."
    exit 1
fi

echo "📊 Using Supabase PostgreSQL + pgvector"
echo "   URL: $SUPABASE_URL"
echo "✅ Data persists in Supabase cloud database"
echo "💡 No ingestion needed on deployment - data is managed via Supabase!"

echo "🎯 Starting FastAPI server..."
python main.py
