# run_ingestion.py

import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path
workspace_root = Path(__file__).resolve().parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from scrape.foodScrapper import RecipeScraper
from scrape.prepareEmbeddings import RecipeEmbeddingPrep
from scrape.generateEmbeddings import RecipeEmbedder

load_dotenv()


async def scrape_recipes_pipeline():
    """
    Scrape recipes from web and save to backup JSON and DB.
    """
    scraper = RecipeScraper(
        allowed_domains=[
            "www.food.com",
            "www.allrecipes.com",
            "www.seriouseats.com",
            "www.bbcgoodfood.com",
            "www.americastestkitchen.com",
            "www.blueapron.com",
        ],
        max_recipes=1000,
        db_path="recipes.db",  # Save to current directory
    )

    start_urls = [
        "https://www.food.com/",
        "https://www.allrecipes.com/",
        "https://www.seriouseats.com/",
        "https://www.bbcgoodfood.com/",
        "https://www.americastestkitchen.com/",
        "https://www.blueapron.com/cookbook/",
    ]

    print("🚀 Scraping recipes...")
    recipes = await scraper.scrape_recipes(start_urls)
    scraper.export_to_json("recipes_backup.json")
    print(f"✅ Scraped {len(recipes)} recipes.")
    return recipes


def prepare_recipes_for_embedding():
    """
    Load recipes from DB and export to JSONL for embeddings.
    """
    print("\n📦 Preparing recipes for embeddings...")
    prep = RecipeEmbeddingPrep(db_path="recipes.db")
    docs = prep.load_recipes_from_db()

    if not docs:
        print("❌ No recipes found in DB. Aborting.")
        return None

    prep.get_statistics()
    jsonl_path = "recipes_for_embedding.jsonl"
    prep.export_for_embedding(jsonl_path)
    print(f"✅ Prepared {len(docs)} recipes for embedding → {jsonl_path}")
    return jsonl_path


def generate_and_ingest_embeddings(jsonl_path):
    """
    Generate embeddings and ingest into ChromaDB.
    CRITICAL: Use the SAME path that main.py uses!
    """
    print("\n⚡ Generating embeddings and ingesting into ChromaDB...")

    # FIXED: Correct path calculation
    # If run_ingestion.py is in /backend/, then:
    # Path(__file__).resolve().parent = /backend/
    # Path(__file__).resolve().parent / "chroma_db" = /backend/chroma_db ✅
    chroma_dir = Path(__file__).resolve().parent / "chroma_db"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 ChromaDB directory: {chroma_dir}")
    print(f"📁 Absolute path: {chroma_dir.absolute()}")

    embedder = RecipeEmbedder(
        provider="gemini",
        model="models/text-embedding-004",
        persist_dir=str(chroma_dir),
        collection_name="recipes",
        batch_size=32,
        embedding_dim=768,
        chunk_size=300
    )

    embedder.ingest_jsonl(jsonl_path)
    print(f"✅ Embeddings ingested into ChromaDB at: {chroma_dir}")
    print(f"   Collection: '{embedder.collection_name}'")


async def main():
    print("\n🎯 Starting full ingestion pipeline...\n")
    print(f"📂 Script location: {Path(__file__).resolve()}")
    print(f"📂 Working directory: {Path.cwd()}")
    print(f"📂 Target ChromaDB: {Path(__file__).resolve().parent / 'chroma_db'}")
    print()
    
    # 1️⃣ Scrape recipes
    await scrape_recipes_pipeline()
    
    # 2️⃣ Prepare recipes for embeddings
    jsonl_path = prepare_recipes_for_embedding()
    if not jsonl_path:
        return

    # 3️⃣ Generate embeddings and ingest to Chroma
    generate_and_ingest_embeddings(jsonl_path)

    print("\n🎉 Full ingestion pipeline completed successfully!")
    print("\n📋 Next steps:")
    print("   1. Run: python debug_chroma_db.py")
    print("   2. Verify recipes are loaded")
    print("   3. Start your server: python backend/main.py")


if __name__ == "__main__":
    asyncio.run(main())