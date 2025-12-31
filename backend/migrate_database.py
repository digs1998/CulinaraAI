#!/usr/bin/env python3
"""
Migration script to fix ChromaDB embedding dimension mismatch.

Problem: Existing database has 384-dim embeddings (default ChromaDB)
Solution: Re-create database with 768-dim Gemini embeddings

This script:
1. Exports existing recipes from old database
2. Deletes old database
3. Re-creates database with Gemini embeddings
"""

import os
import json
import shutil
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from chromadb import PersistentClient
from chromadb.utils.embedding_functions import GoogleGenerativeAiEmbeddingFunction

load_dotenv()

# Paths
BACKEND_DIR = Path(__file__).resolve().parent
OLD_DB_PATH = BACKEND_DIR / "data" / "chroma_db"
BACKUP_FILE = BACKEND_DIR / "data" / "recipes_backup_migration.json"

def export_existing_recipes():
    """Export all recipes from existing database"""
    print(f"📤 Exporting recipes from: {OLD_DB_PATH}")

    if not OLD_DB_PATH.exists():
        print("❌ Old database not found!")
        return None

    try:
        client = PersistentClient(path=str(OLD_DB_PATH))
        collection = client.get_collection("recipes")

        count = collection.count()
        print(f"📊 Found {count} recipes")

        # Get all recipes
        results = collection.get(include=["metadatas"])
        recipes = []

        for meta in results["metadatas"]:
            # Parse JSON strings back to lists
            if 'ingredients' in meta and isinstance(meta['ingredients'], str):
                try:
                    meta['ingredients'] = json.loads(meta['ingredients'])
                except:
                    meta['ingredients'] = [meta['ingredients']]

            if 'instructions' in meta and isinstance(meta['instructions'], str):
                try:
                    meta['instructions'] = json.loads(meta['instructions'])
                except:
                    meta['instructions'] = [meta['instructions']]

            if 'facts' in meta and isinstance(meta['facts'], str):
                try:
                    meta['facts'] = json.loads(meta['facts'])
                except:
                    meta['facts'] = {}

            recipes.append(meta)

        # Save backup
        with open(BACKUP_FILE, 'w') as f:
            json.dump(recipes, f, indent=2)

        print(f"✅ Backed up {len(recipes)} recipes to: {BACKUP_FILE}")
        return recipes

    except Exception as e:
        print(f"❌ Export failed: {e}")
        return None


def delete_old_database():
    """Delete the old database directory"""
    print(f"\n🗑️  Deleting old database: {OLD_DB_PATH}")

    if OLD_DB_PATH.exists():
        shutil.rmtree(OLD_DB_PATH)
        print("✅ Old database deleted")
    else:
        print("⚠️  Old database already deleted")


def create_new_database(recipes):
    """Create new database with Gemini embeddings"""
    print(f"\n⚡ Creating new database with Gemini embeddings...")

    # Configure Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment!")
        return False

    genai.configure(api_key=api_key)

    # Create new database directory
    OLD_DB_PATH.mkdir(parents=True, exist_ok=True)

    # Create Gemini embedding function
    embedding_function = GoogleGenerativeAiEmbeddingFunction(
        api_key=api_key,
        model_name="models/text-embedding-004",
        task_type="retrieval_document"
    )

    # Create ChromaDB client with embedding function
    client = PersistentClient(path=str(OLD_DB_PATH))

    # Delete collection if it exists
    try:
        client.delete_collection("recipes")
        print("   Deleted existing collection")
    except Exception as e:
        print(f"   No existing collection to delete: {e}")

    # Create new collection with Gemini embedding function
    try:
        collection = client.get_or_create_collection(
            name="recipes",
            embedding_function=embedding_function,
            metadata={"description": "Recipe embeddings for RAG search (Gemini 768-dim)"}
        )
    except Exception as e:
        print(f"   Error creating collection: {e}")
        # Try force delete and recreate
        try:
            all_collections = client.list_collections()
            print(f"   Existing collections: {[c.name for c in all_collections]}")
            for col in all_collections:
                if col.name == "recipes":
                    client.delete_collection("recipes")
            collection = client.create_collection(
                name="recipes",
                embedding_function=embedding_function,
                metadata={"description": "Recipe embeddings for RAG search (Gemini 768-dim)"}
            )
        except Exception as e2:
            print(f"   Failed to create collection: {e2}")
            return False

    print(f"📊 Ingesting {len(recipes)} recipes...")

    # Prepare data for ingestion
    ids = []
    documents = []
    metadatas = []

    for i, recipe in enumerate(recipes):
        # Create document text for embedding
        title = recipe.get('title', 'Recipe')
        ingredients = recipe.get('ingredients', [])
        instructions = recipe.get('instructions', [])

        # Create rich text for embedding
        ing_text = " ".join(ingredients[:10]) if isinstance(ingredients, list) else ""
        inst_text = " ".join(instructions[:5]) if isinstance(instructions, list) else ""

        document = f"{title}. Ingredients: {ing_text}. Instructions: {inst_text}"

        # Prepare metadata (store ingredients/instructions as JSON strings)
        metadata = recipe.copy()

        # Ensure ingredients/instructions are JSON strings
        if 'ingredients' in metadata and isinstance(metadata['ingredients'], list):
            metadata['ingredients'] = json.dumps(metadata['ingredients'])

        if 'instructions' in metadata and isinstance(metadata['instructions'], list):
            metadata['instructions'] = json.dumps(metadata['instructions'])

        if 'facts' in metadata and isinstance(metadata['facts'], dict):
            metadata['facts'] = json.dumps(metadata['facts'])

        # Generate unique ID
        recipe_id = recipe.get('id', f"recipe_{i}")

        ids.append(recipe_id)
        documents.append(document)
        metadatas.append(metadata)

        if (i + 1) % 50 == 0:
            print(f"   Processed {i + 1}/{len(recipes)} recipes...")

    # Ingest in batches to avoid rate limits
    batch_size = 50
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i+batch_size]
        batch_docs = documents[i:i+batch_size]
        batch_metas = metadatas[i:i+batch_size]

        collection.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_metas
        )

        print(f"   Ingested batch {i//batch_size + 1}/{(len(ids) + batch_size - 1)//batch_size}")

    final_count = collection.count()
    print(f"✅ Created new database with {final_count} recipes!")
    print(f"   Embedding model: text-embedding-004 (768 dimensions)")
    print(f"   Location: {OLD_DB_PATH}")

    return True


def verify_database():
    """Verify the new database works correctly"""
    print(f"\n🔍 Verifying new database...")

    try:
        # Configure Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)

        # Create embedding function
        embedding_function = GoogleGenerativeAiEmbeddingFunction(
            api_key=api_key,
            model_name="models/text-embedding-004",
            task_type="retrieval_query"
        )

        # Connect to database
        client = PersistentClient(path=str(OLD_DB_PATH))
        collection = client.get_collection(
            name="recipes",
            embedding_function=embedding_function
        )

        # Test query
        test_query = "vegan recipes"
        print(f"   Testing query: '{test_query}'")

        results = collection.query(
            query_texts=[test_query],
            n_results=3,
            include=["metadatas", "distances"]
        )

        print(f"   ✅ Query successful! Found {len(results['metadatas'][0])} results:")

        for i, (meta, distance) in enumerate(zip(results['metadatas'][0], results['distances'][0]), 1):
            similarity = 1.0 - distance
            print(f"      {i}. {meta.get('title', 'No title')[:50]} (similarity: {similarity:.2%})")

        return True

    except Exception as e:
        print(f"   ❌ Verification failed: {e}")
        return False


def main():
    print("=" * 60)
    print("ChromaDB Migration: 384-dim → 768-dim Gemini Embeddings")
    print("=" * 60)

    # Step 1: Export existing recipes (or load from backup)
    recipes = export_existing_recipes()

    if not recipes:
        # Try loading from backup
        if BACKUP_FILE.exists():
            print(f"\n📦 Loading recipes from backup: {BACKUP_FILE}")
            with open(BACKUP_FILE, 'r') as f:
                recipes = json.load(f)
            print(f"✅ Loaded {len(recipes)} recipes from backup")
        else:
            print("\n❌ Migration aborted - no recipes found and no backup exists")
            return

    # Step 2: Delete old database (if exists)
    if OLD_DB_PATH.exists():
        delete_old_database()
    else:
        print(f"\n⚠️  Old database doesn't exist (already deleted or fresh install)")

    # Step 3: Create new database with Gemini embeddings
    success = create_new_database(recipes)
    if not success:
        print("\n❌ Migration failed - could not create new database")
        return

    # Step 4: Verify database works
    if verify_database():
        print("\n" + "=" * 60)
        print("✅ MIGRATION SUCCESSFUL!")
        print("=" * 60)
        print(f"\nBackup saved to: {BACKUP_FILE}")
        print(f"New database at: {OLD_DB_PATH}")
        print("\n📋 Next steps:")
        print("   1. Run: python backend/main.py")
        print("   2. Test recipe search in the app")
        print("   3. Verify recipes appear correctly")
    else:
        print("\n⚠️  Migration completed but verification failed")
        print("   Check GEMINI_API_KEY and try running the app")


if __name__ == "__main__":
    main()
