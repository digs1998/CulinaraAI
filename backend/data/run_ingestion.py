# run_ingestion.py

import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path so imports work
workspace_root = Path(__file__).parent.parent  # run_ingestion.py is in backend/data/
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from scrape.foodScrapper import RecipeScraper
from scrape.prepareEmbeddings import RecipeEmbeddingPrep
from scrape.generateEmbeddings import RecipeEmbedder

load_dotenv()


async def scrape_recipes_pipeline():
    """
    Scrape recipes from web and save to backup JSON (optional DB insert if needed).
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
    """
    print("\n⚡ Generating embeddings and ingesting into ChromaDB...")

    embedder = RecipeEmbedder(
        provider="gemini",             # or "openai", "sentence-transformers"
        model="text-embedding-004",     
        persist_dir="./chroma_db",     # Chroma persistence directory
        collection_name="recipes",     # Chroma collection name
        batch_size=64,
        embedding_dim=768,
        chunk_size=300
    )

    embedder.ingest_jsonl(jsonl_path)
    print(f"✅ Embeddings ingested into ChromaDB collection '{embedder.collection_name}'.")


async def main():
    print("\n🎯 Starting full ingestion pipeline...\n")
    
    # 1️⃣ Scrape recipes
    await scrape_recipes_pipeline()
    
    # 2️⃣ Prepare recipes for embeddings
    jsonl_path = prepare_recipes_for_embedding()
    if not jsonl_path:
        return

    # 3️⃣ Generate embeddings and ingest to Chroma
    generate_and_ingest_embeddings(jsonl_path)

    print("\n🎉 Full ingestion pipeline completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
