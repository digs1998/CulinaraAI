# load_recipes_to_chroma.py
"""
Load recipes from JSON backup into ChromaDB
"""
import sys
import json
from pathlib import Path
from typing import List, Dict

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from chromadb import Client
from chromadb.config import Settings

def load_recipes_from_json(json_path: str) -> List[Dict]:
    """Load recipes from JSON file"""
    print(f"📂 Loading recipes from: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle different JSON structures
    if isinstance(data, list):
        recipes = data
    elif isinstance(data, dict) and 'recipes' in data:
        recipes = data['recipes']
    else:
        recipes = [data]
    
    print(f"✅ Loaded {len(recipes)} recipes from JSON")
    return recipes

def prepare_recipe_for_chromadb(recipe: Dict) -> tuple:
    """
    Prepare recipe data for ChromaDB insertion
    Returns: (id, document, metadata)
    """
    # Generate ID (use title or create one)
    recipe_id = recipe.get('id') or f"recipe_{recipe.get('title', 'unknown').lower().replace(' ', '_')}"
    
    # Create document text (for embedding and search)
    # Combine title, ingredients, and instructions for better search
    title = recipe.get('title', '')
    ingredients = recipe.get('ingredients', [])
    instructions = recipe.get('instructions', [])
    
    # Create searchable text
    doc_text = f"Recipe: {title}\n\n"
    doc_text += "Ingredients:\n" + "\n".join([f"- {ing}" for ing in ingredients[:15]]) + "\n\n"
    doc_text += "Instructions:\n" + "\n".join([f"{i+1}. {inst}" for i, inst in enumerate(instructions[:10])])
    
    # Create metadata (must be JSON serializable)
    metadata = {
        'title': title,
        'ingredients': ingredients,
        'instructions': instructions,
        'url': recipe.get('source', recipe.get('url', '')),
        'facts': recipe.get('facts', {}),
    }
    
    # ChromaDB metadata must be flat (no nested dicts in some versions)
    # So let's flatten facts
    facts = recipe.get('facts', {})
    if facts:
        metadata['prep_time'] = str(facts.get('prep_time', ''))
        metadata['cook_time'] = str(facts.get('cook_time', ''))
        metadata['total_time'] = str(facts.get('total_time', ''))
        metadata['servings'] = str(facts.get('servings', ''))
        metadata['calories'] = str(facts.get('calories', ''))
    
    return recipe_id, doc_text, metadata

def load_recipes_to_chromadb(json_path: str):
    """Main function to load recipes into ChromaDB"""
    print("=" * 60)
    print("Loading Recipes to ChromaDB")
    print("=" * 60)
    
    # Load recipes from JSON
    recipes = load_recipes_from_json(json_path)
    
    if not recipes:
        print("❌ No recipes found in JSON file")
        return
    
    # Initialize ChromaDB
    chroma_dir = Path(__file__).parent / "backend" / "chroma_db"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📁 Database path: {chroma_dir}")
    
    chroma_client = Client(
        Settings(
            persist_directory=str(chroma_dir),
            anonymized_telemetry=False,
        )
    )
    
    # Get or create collection
    try:
        # Delete existing collection to start fresh
        try:
            chroma_client.delete_collection("recipes")
            print("🗑️  Deleted existing collection")
        except:
            pass
        
        collection = chroma_client.create_collection("recipes")
        print("✅ Created new collection 'recipes'")
    except Exception as e:
        print(f"❌ Failed to create collection: {e}")
        return
    
    # Prepare data for bulk insert
    ids = []
    documents = []
    metadatas = []
    
    print(f"\n📝 Preparing {len(recipes)} recipes for insertion...")
    
    for i, recipe in enumerate(recipes, 1):
        try:
            recipe_id, doc_text, metadata = prepare_recipe_for_chromadb(recipe)
            ids.append(recipe_id)
            documents.append(doc_text)
            metadatas.append(metadata)
            
            if i % 10 == 0:
                print(f"   Prepared {i}/{len(recipes)} recipes...")
        except Exception as e:
            print(f"⚠️  Skipping recipe {i} due to error: {e}")
            continue
    
    # Insert into ChromaDB
    print(f"\n💾 Inserting {len(ids)} recipes into ChromaDB...")
    
    try:
        # Insert in batches to avoid memory issues
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_docs = documents[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            
            collection.add(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_meta
            )
            print(f"   ✅ Inserted batch {i//batch_size + 1} ({len(batch_ids)} recipes)")
        
        print(f"\n✅ Successfully loaded {len(ids)} recipes into ChromaDB")
        print(f"📊 Collection now has {collection.count()} recipes")
        
        # Test search
        print(f"\n🔍 Testing search with 'chicken'...")
        results = collection.query(
            query_texts=["chicken recipes"],
            n_results=3,
            include=["metadatas", "distances"]
        )
        
        if results['ids'][0]:
            print(f"   ✅ Search works! Found {len(results['ids'][0])} results:")
            for j, (result_id, metadata, distance) in enumerate(
                zip(results['ids'][0], results['metadatas'][0], results['distances'][0]), 1
            ):
                similarity = 1 - distance
                print(f"   {j}. {metadata.get('title', 'Unknown')} (similarity: {similarity:.3f})")
        
    except Exception as e:
        print(f"❌ Failed to insert recipes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Update this path to your JSON backup file
    json_path = input("Enter path to your recipes JSON file: ").strip()
    
    if not Path(json_path).exists():
        print(f"❌ File not found: {json_path}")
        print("\nPlease provide the correct path to your recipes JSON backup.")
        sys.exit(1)
    
    load_recipes_to_chromadb(json_path)