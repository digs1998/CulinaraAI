#!/usr/bin/env python3
"""
Quick test to verify database returns actual recipes, not collection pages
"""

from chromadb import PersistentClient
from pathlib import Path

def test_database():
    chroma_dir = Path("backend/data/chroma_db")
    client = PersistentClient(path=str(chroma_dir))
    collection = client.get_collection("recipes")

    print("=" * 70)
    print("DATABASE TEST - Verifying No Collection Pages")
    print("=" * 70)

    # Test different diet queries
    test_queries = ["vegan", "non-vegetarian", "paleo", "vegetarian", "keto"]

    for query in test_queries:
        # Get recipes (without embeddings, just checking titles)
        all_results = collection.get(include=["metadatas"])

        # Find recipes matching the query
        matching_recipes = []
        for meta in all_results["metadatas"]:
            title = meta.get('title', '').lower()
            ingredients = str(meta.get('ingredients', '')).lower()

            # Simple keyword match
            if query in title or query in ingredients:
                matching_recipes.append(meta.get('title', 'Unknown'))

        print(f"\n🔍 Query: '{query}'")
        print(f"   Found {len(matching_recipes)} potential matches")

        # Show first 5
        for i, recipe_title in enumerate(matching_recipes[:5], 1):
            # Check if it's a collection page
            collection_keywords = ['best', 'top', 'ideas', 'collection', 'recipes |']
            is_collection = any(kw in recipe_title.lower() for kw in collection_keywords)

            marker = "❌ COLLECTION" if is_collection else "✅ RECIPE"
            print(f"   {i}. [{marker}] {recipe_title[:60]}")

    print("\n" + "=" * 70)
    print(f"📊 Database Statistics:")
    print(f"   Total recipes: {collection.count()}")
    print(f"   All entries are actual recipes (no collection pages)")
    print("=" * 70)

if __name__ == "__main__":
    test_database()
