#!/usr/bin/env python3
"""
Clean ChromaDB by removing collection pages
"""
import sys
import re
from pathlib import Path
from typing import List

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from chromadb import PersistentClient


def is_collection_page(title: str, url: str) -> bool:
    """
    Detect if a recipe entry is actually a collection page
    """
    if not title:
        return False

    title_lower = title.lower()
    url_lower = url.lower()

    # Check URL for collection indicators
    collection_url_patterns = [
        '/collection/', '/collections/',
        '/roundup/', '/roundups/',
        '/ideas/', '/browse/'
    ]

    if any(pattern in url_lower for pattern in collection_url_patterns):
        return True

    # Check if title ends with " recipes" or " dishes"
    if title_lower.endswith(' recipes') or title_lower.endswith(' dishes'):
        return True

    # Check for collection keywords in title
    collection_keywords = [
        'collection', 'roundup',
        'best ', 'top ',
        'easy recipes', 'quick recipes',
        'dinner recipes', 'lunch recipes', 'breakfast recipes',
        'vegetarian recipes', 'vegan recipes',
        'batch cooking recipes',
        '30-minute', 'minute meal'
    ]

    if any(keyword in title_lower for keyword in collection_keywords):
        return True

    # Check for number patterns like "10 easy recipes"
    has_number_list = bool(re.search(
        r'\d+\s+(easy|quick|best|top|vegan|vegetarian)?\s*(recipes|dishes|meals|snacks)',
        title_lower
    ))

    return has_number_list


def clean_chromadb():
    """Remove collection pages from ChromaDB"""
    print("=" * 80)
    print("ChromaDB Collection Page Cleanup")
    print("=" * 80)

    # Find ChromaDB directory
    possible_paths = [
        Path(__file__).resolve().parent / "chroma_db",
        Path(__file__).resolve().parent / "data" / "chroma_db",
        Path(__file__).resolve().parent / "backend" / "chroma_db",
    ]

    chroma_dir = None
    for path in possible_paths:
        if path.exists() and (path / "chroma.sqlite3").exists():
            chroma_dir = path
            break

    if not chroma_dir:
        print("❌ ChromaDB directory not found!")
        return

    print(f"\n📁 Database path: {chroma_dir}")

    # Initialize ChromaDB client
    try:
        client = PersistentClient(path=str(chroma_dir))
        collection = client.get_collection("recipes")
        print(f"✅ Connected to ChromaDB")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return

    # Get all items
    initial_count = collection.count()
    print(f"\n📊 Current recipe count: {initial_count}")

    print(f"\n🔍 Fetching all recipes to analyze...")
    try:
        results = collection.get(include=["metadatas"])
        all_ids = results['ids']
        all_metadata = results['metadatas']

        print(f"✅ Retrieved {len(all_ids)} recipes")
    except Exception as e:
        print(f"❌ Failed to fetch recipes: {e}")
        return

    # Identify collection pages
    collection_page_ids: List[str] = []
    collection_page_titles: List[str] = []

    print(f"\n🔎 Analyzing recipes for collection pages...")

    for recipe_id, metadata in zip(all_ids, all_metadata):
        title = metadata.get('title', '')
        url = metadata.get('url', '')

        if is_collection_page(title, url):
            collection_page_ids.append(recipe_id)
            collection_page_titles.append(title)

    print(f"\n{'=' * 80}")
    print(f"Found {len(collection_page_ids)} collection pages to remove:")
    print(f"{'=' * 80}")

    for i, title in enumerate(collection_page_titles[:20], 1):
        print(f"   {i}. {title}")

    if len(collection_page_titles) > 20:
        print(f"   ... and {len(collection_page_titles) - 20} more")

    if not collection_page_ids:
        print("\n✅ No collection pages found! Database is clean.")
        return

    # Confirm deletion
    print(f"\n⚠️  About to delete {len(collection_page_ids)} collection pages")
    response = input("Continue? (yes/no): ").strip().lower()

    if response != 'yes':
        print("❌ Cancelled")
        return

    # Delete collection pages
    print(f"\n🗑️  Removing collection pages...")

    try:
        # Delete in batches to avoid issues
        batch_size = 100
        deleted_count = 0

        for i in range(0, len(collection_page_ids), batch_size):
            batch_ids = collection_page_ids[i:i+batch_size]
            collection.delete(ids=batch_ids)
            deleted_count += len(batch_ids)
            print(f"   Deleted {deleted_count}/{len(collection_page_ids)}...")

        final_count = collection.count()

        print(f"\n{'=' * 80}")
        print("✅ Cleanup Complete!")
        print(f"{'=' * 80}")
        print(f"   Before: {initial_count} recipes")
        print(f"   Deleted: {len(collection_page_ids)} collection pages")
        print(f"   After: {final_count} real recipes")
        print(f"\n💡 {final_count} recipes remain in the database")

    except Exception as e:
        print(f"❌ Deletion failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    clean_chromadb()
