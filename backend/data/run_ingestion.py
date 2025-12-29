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
        max_recipes=300,
        db_path="recipes.db",
    )

    # More diverse start URLs to find more recipes
    start_urls = [
        # Food.com
        "https://www.food.com/ideas",
        "https://www.food.com/recipes",
        
        # AllRecipes
        "https://www.allrecipes.com/recipes/",
        "https://www.allrecipes.com/recipes/17562/dinner/",
        "https://www.allrecipes.com/recipes/78/breakfast-and-brunch/",
        
        # Serious Eats
        "https://www.seriouseats.com/recipes",
        "https://www.seriouseats.com/easy-recipes-5117887",
        
        # BBC Good Food
        "https://www.bbcgoodfood.com/recipes/collection/quick-recipes",
        "https://www.bbcgoodfood.com/recipes/collection/easy-recipes",
        "https://www.bbcgoodfood.com/recipes",
        
        # America's Test Kitchen
        "https://www.americastestkitchen.com/recipes/browse",
        "https://www.americastestkitchen.com/recipes",
        
        # Blue Apron
        "https://www.blueapron.com/cookbook/",
    ]

    print(f"🚀 Scraping recipes from {len(start_urls)} start URLs...")
    print(f"🎯 Target: {scraper.max_recipes} recipes\n")
    
    recipes = await scraper.scrape_recipes(start_urls)
    scraper.export_to_json("recipes_backup.json")
    
    print(f"\n✅ Final count: {len(recipes)} recipes scraped")
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
    import time
    
    start_time = time.time()
    
    print("\n🎯 Starting full ingestion pipeline...\n")
    print(f"📂 Script location: {Path(__file__).resolve()}")
    print(f"📂 Working directory: {Path.cwd()}")
    print(f"📂 Target ChromaDB: {Path(__file__).resolve().parent / 'chroma_db'}")
    print()
    
    # 1️⃣ Scrape recipes
    scrape_start = time.time()
    await scrape_recipes_pipeline()
    scrape_time = time.time() - scrape_start
    print(f"\n⏱️  Scraping took: {scrape_time:.2f} seconds ({scrape_time/60:.2f} minutes)")
    
    # 2️⃣ Prepare recipes for embeddings
    prep_start = time.time()
    jsonl_path = prepare_recipes_for_embedding()
    if not jsonl_path:
        return
    prep_time = time.time() - prep_start
    print(f"\n⏱️  Preparation took: {prep_time:.2f} seconds")

    # 3️⃣ Generate embeddings and ingest to Chroma
    embed_start = time.time()
    generate_and_ingest_embeddings(jsonl_path)
    embed_time = time.time() - embed_start
    print(f"\n⏱️  Embedding generation took: {embed_time:.2f} seconds ({embed_time/60:.2f} minutes)")
    
    total_time = time.time() - start_time

    print("\n🎉 Full ingestion pipeline completed successfully!")
    print(f"\n⏱️  TOTAL TIME: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
    print(f"   - Scraping: {scrape_time/60:.2f} min")
    print(f"   - Preparation: {prep_time:.2f} sec")
    print(f"   - Embeddings: {embed_time/60:.2f} min")
    print("\n📋 Next steps:")
    print("   1. Run: python debug_chroma_db.py")
    print("   2. Verify recipes are loaded")
    print("   3. Start your server: python backend/main.py")


if __name__ == "__main__":
    asyncio.run(main())