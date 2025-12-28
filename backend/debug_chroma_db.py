# debug_chroma_db.py
"""
Debug script to check ChromaDB contents and test search
"""
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from chromadb import PersistentClient
from chromadb.config import Settings

def debug_chromadb():
    print("=" * 60)
    print("ChromaDB Debug Script")
    print("=" * 60)
    
    # Initialize ChromaDB with PersistentClient (more reliable)
    # Check multiple possible paths
    possible_paths = [
        Path(__file__).resolve().parent / "chroma_db",  # Same directory as script
        Path(__file__).resolve().parent / "backend" / "chroma_db",  # One level up
        Path(__file__).resolve().parent / "data" / "chroma_db",  # In data folder
    ]
    
    chroma_dir = None
    for path in possible_paths:
        if path.exists():
            chroma_dir = path
            break
    
    if not chroma_dir:
        chroma_dir = possible_paths[0]  # Default to first option
    
    print(f"\n📁 Database path: {chroma_dir}")
    print(f"   Exists: {chroma_dir.exists()}")
    
    if not chroma_dir.exists():
        print("❌ ChromaDB directory doesn't exist!")
        return
    
    # List files in directory
    print(f"\n📂 Files in ChromaDB directory:")
    if chroma_dir.exists():
        for item in chroma_dir.iterdir():
            print(f"   - {item.name}")
    
    try:
        # Use PersistentClient instead of Client
        chroma_client = PersistentClient(path=str(chroma_dir))
        print("✅ ChromaDB client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize ChromaDB: {e}")
        return
    
    # List all collections
    try:
        collections = chroma_client.list_collections()
        print(f"\n📚 Collections found: {len(collections)}")
        for col in collections:
            print(f"   - {col.name} ({col.count()} items)")
    except Exception as e:
        print(f"❌ Failed to list collections: {e}")
        return
    
    # Get recipes collection
    try:
        collection = chroma_client.get_collection("recipes")
        print(f"\n✅ Collection 'recipes' loaded")
    except Exception as e:
        print(f"❌ Failed to get collection: {e}")
        print("\n💡 Try creating the collection first with the ingestion script")
        return
    
    # Check collection size
    count = collection.count()
    print(f"\n📊 Total recipes in database: {count}")
    
    if count == 0:
        print("\n⚠️  DATABASE IS EMPTY!")
        print("   Possible issues:")
        print("   1. Ingestion didn't save properly")
        print("   2. Wrong path used during ingestion")
        print("   3. ChromaDB persistence issue")
        print("\n💡 Solution: Re-run ingestion with fixed script")
        return
    
    # Get sample items
    print(f"\n📝 Fetching sample recipes...")
    try:
        results = collection.get(limit=10, include=["metadatas", "documents"])
        
        print(f"\n{'='*60}")
        print("Sample Recipes in Database:")
        print(f"{'='*60}")
        
        for i, (doc_id, metadata, document) in enumerate(
            zip(results['ids'], results['metadatas'], results['documents']), 1
        ):
            title = metadata.get('title', 'Unknown')
            ingredients = metadata.get('ingredients', [])
            if isinstance(ingredients, str):
                # Count comma-separated items if stored as string
                ing_count = len(ingredients.split(','))
            else:
                ing_count = len(ingredients)
            
            print(f"\n{i}. {title}")
            print(f"   ID: {doc_id}")
            print(f"   Ingredients: {ing_count}")
            print(f"   Source: {metadata.get('url', 'N/A')[:60]}")
            print(f"   Document length: {len(document)} chars")
            
    except Exception as e:
        print(f"❌ Error fetching recipes: {e}")
        import traceback
        traceback.print_exc()
    
    # Test search functionality with GEMINI EMBEDDINGS
    print(f"\n{'='*60}")
    print("Testing Search Functionality")
    print(f"{'='*60}")
    
    # Initialize Gemini for embeddings (same as rag_engine)
    import os
    import google.generativeai as genai
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("\n⚠️  GEMINI_API_KEY not found in environment")
        print("   Skipping search tests (they require Gemini embeddings)")
        return
    
    genai.configure(api_key=api_key)
    
    def get_embedding(text: str):
        """Generate embedding using Gemini (same as RAG engine)"""
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_query",
        )
        return result["embedding"]
    
    test_queries = [
        "chicken recipes",
        "paneer",
        "quick dinner",
        "pasta",
    ]
    
    for query in test_queries:
        print(f"\n🔍 Searching for: '{query}'")
        try:
            # Generate embedding with Gemini
            query_embedding = get_embedding(query)
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=3,
                include=["metadatas", "distances"]
            )
            
            if results['ids'] and results['ids'][0]:
                print(f"   ✅ Found {len(results['ids'][0])} results")
                for i, (doc_id, metadata, distance) in enumerate(
                    zip(results['ids'][0], results['metadatas'][0], results['distances'][0]), 1
                ):
                    similarity = 1 - distance  # Convert distance to similarity
                    title = metadata.get('title', 'Unknown')
                    print(f"   {i}. {title} (similarity: {similarity:.3f}, distance: {distance:.3f})")
            else:
                print(f"   ⚠️  No results found")
                
        except Exception as e:
            print(f"   ❌ Search failed: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("Debug Complete")
    print(f"{'='*60}")
    print("\n💡 If database is still empty, check:")
    print("   1. Path used in ingestion matches this path")
    print("   2. Ingestion script completed without errors")
    print("   3. ChromaDB files exist in the directory")

if __name__ == "__main__":
    debug_chromadb()