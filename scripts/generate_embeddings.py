#!/usr/bin/env python3
"""
Generate embeddings for new recipes using Gemini API.
Stores embeddings in Supabase pgvector for semantic search.

Uses Gemini text-embedding-004 (768 dimensions).
Free tier: 1,500 requests/day
"""
import os
import sys
import psycopg2
from typing import List, Tuple
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def connect_db():
    """Connect to Supabase PostgreSQL"""
    db_url = os.getenv('SUPABASE_DATABASE_URL')
    if not db_url:
        print("❌ SUPABASE_DATABASE_URL not set!")
        sys.exit(1)
    return psycopg2.connect(db_url)

def configure_gemini():
    """Configure Gemini API"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set!")
        sys.exit(1)
    genai.configure(api_key=api_key)

def get_pending_recipes(limit: int = 200) -> List[Tuple]:
    """
    Get recipes that don't have embeddings yet.
    Returns: [(recipe_id, title, ingredients, instructions), ...]
    """
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.id, r.title, r.ingredients, r.instructions, r.source_name
        FROM recipes r
        LEFT JOIN recipe_embeddings e ON r.id = e.recipe_id
        WHERE e.id IS NULL
        ORDER BY r.created_at DESC
        LIMIT %s
    """, (limit,))

    recipes = cursor.fetchall()
    cursor.close()
    conn.close()

    return recipes

def create_recipe_text(title: str, ingredients: List[str], instructions: List[str]) -> str:
    """
    Create searchable text from recipe for embedding.
    Combines title, ingredients, and instructions in a semantic format.
    """
    # Start with title
    text = f"Recipe: {title}\n\n"

    # Add ingredients (limit to 15 to avoid token limits)
    text += "Ingredients:\n"
    for ing in ingredients[:15]:
        text += f"- {ing}\n"

    # Add instructions (limit to 10 steps)
    text += "\nInstructions:\n"
    for i, step in enumerate(instructions[:10], 1):
        # Clean up instruction text
        step_text = step.strip()
        if step_text:
            text += f"{i}. {step_text}\n"

    return text

def generate_embedding(text: str, max_retries: int = 3) -> List[float]:
    """
    Generate embedding using Gemini API with retry logic.
    Returns: 768-dimensional embedding vector
    """
    for attempt in range(max_retries):
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result["embedding"]

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # Exponential backoff
                print(f"  ⚠️ Retry {attempt + 1}/{max_retries} after {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise e

def insert_embedding(recipe_id: str, embedding: List[float]) -> bool:
    """
    Insert embedding into Supabase.
    Returns: True if successful, False otherwise
    """
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Convert embedding to string format for pgvector
        embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'

        cursor.execute("""
            INSERT INTO recipe_embeddings (recipe_id, embedding)
            VALUES (%s, %s::vector)
            ON CONFLICT (recipe_id) DO UPDATE
            SET embedding = EXCLUDED.embedding,
                updated_at = NOW()
        """, (recipe_id, embedding_str))

        conn.commit()
        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False

def main():
    print("=" * 70)
    print("⚡ CULINARA AI - EMBEDDING GENERATOR")
    print("=" * 70)
    print()

    # Configure Gemini
    configure_gemini()
    print("✅ Gemini API configured")

    # Get recipes without embeddings
    print("\n🔍 Looking for recipes without embeddings...")
    pending = get_pending_recipes(limit=200)  # Limit to stay within API quota

    if not pending:
        print("✅ All recipes already have embeddings!")
        return

    print(f"📝 Found {len(pending)} recipes needing embeddings")
    print(f"⏱️  Estimated time: ~{len(pending) * 0.5:.0f} seconds")
    print()

    successful = 0
    failed = 0
    skipped = 0

    for i, (recipe_id, title, ingredients, instructions, source_name) in enumerate(pending, 1):
        try:
            # Skip if ingredients or instructions are empty
            if not ingredients or not instructions:
                print(f"  ⏭️  [{i}/{len(pending)}] Skipping '{title}' (missing data)")
                skipped += 1
                continue

            # Create searchable text
            recipe_text = create_recipe_text(title, ingredients, instructions)

            # Generate embedding
            embedding = generate_embedding(recipe_text)

            # Store in database
            if insert_embedding(recipe_id, embedding):
                successful += 1

                # Progress indicator
                if i % 10 == 0:
                    print(f"  ✅ [{i}/{len(pending)}] Processed {successful} recipes...")
            else:
                failed += 1

            # Rate limiting to avoid hitting API quota
            # Gemini free tier: 1500 requests/day = ~1 request every 60 seconds to stay safe
            # But we'll do faster since we only run once per day
            time.sleep(0.5)  # 2 requests/second = 7200/hour (well within limits for daily batch)

        except Exception as e:
            print(f"  ❌ [{i}/{len(pending)}] Failed for '{title[:50]}...': {e}")
            failed += 1

            # If we hit rate limit, wait longer
            if 'quota' in str(e).lower() or 'rate' in str(e).lower():
                print("  ⏸️  Rate limit detected, waiting 60 seconds...")
                time.sleep(60)
            else:
                time.sleep(1)
            continue

    print("\n" + "=" * 70)
    print("📊 EMBEDDING GENERATION SUMMARY")
    print("=" * 70)
    print(f"✅ Successfully generated: {successful} embeddings")
    print(f"❌ Failed: {failed}")
    print(f"⏭️  Skipped (missing data): {skipped}")
    print(f"📊 Total processed: {successful + failed + skipped}/{len(pending)}")
    print("=" * 70)

    # Get final stats
    try:
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM recipes")
        total_recipes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM recipe_embeddings")
        total_embeddings = cursor.fetchone()[0]

        coverage_percent = (total_embeddings / total_recipes * 100) if total_recipes > 0 else 0

        print(f"\n📊 Database Status:")
        print(f"   Total recipes: {total_recipes}")
        print(f"   Total embeddings: {total_embeddings}")
        print(f"   Coverage: {coverage_percent:.1f}%")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"⚠️ Could not get final stats: {e}")

if __name__ == "__main__":
    main()
