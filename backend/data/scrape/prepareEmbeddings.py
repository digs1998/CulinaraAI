import json
import sqlite3
import re
from typing import List, Dict, Optional
from datetime import datetime
import numpy as np
from dataclasses import dataclass, asdict


@dataclass
class RecipeDocument:
    """Structured recipe document for embedding"""
    recipe_id: int
    url: str
    title: str
    description: str
    full_text: str  # Combined searchable text
    ingredients_text: str
    instructions_text: str
    metadata: dict
    

class RecipeEmbeddingPrep:
    """Prepare recipe data for embedding and vector storage"""
    
    def __init__(self, db_path: str = "recipes.db"):
        self.db_path = db_path
        self.documents: List[RecipeDocument] = []
        
    def clean_time_format(self, time_str: Optional[str]) -> str:
        """Convert ISO 8601 duration to human readable format"""
        if not time_str:
            return "Not specified"
        
        # Parse ISO 8601 duration (PT15M, PT1H30M, etc.)
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', time_str)
        if match:
            hours = int(match.group(1)) if match.group(1) else 0
            minutes = int(match.group(2)) if match.group(2) else 0
            
            parts = []
            if hours:
                parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
            if minutes:
                parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
            
            return " ".join(parts) if parts else "Not specified"
        
        return time_str
    
    def clean_html_entities(self, text: str) -> str:
        """Clean HTML entities from text"""
        if not text:
            return ""
        
        # Common HTML entities
        replacements = {
            '&#xB0;': '°',
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
        }
        
        for entity, char in replacements.items():
            text = text.replace(entity, char)
        
        # Remove any remaining HTML entities
        text = re.sub(r'&#?\w+;', '', text)
        
        return text
    
    def clean_ingredient(self, ingredient: str) -> str:
        """Clean and standardize ingredient text"""
        ingredient = self.clean_html_entities(ingredient)
        
        # Remove extra whitespace
        ingredient = ' '.join(ingredient.split())
        
        # Remove leading/trailing punctuation
        ingredient = ingredient.strip('., ')
        
        return ingredient
    
    def clean_instruction(self, instruction: str) -> str:
        """Clean and standardize instruction text"""
        instruction = self.clean_html_entities(instruction)
        
        # Remove extra whitespace
        instruction = ' '.join(instruction.split())
        
        # Ensure proper punctuation
        if instruction and not instruction.endswith('.'):
            instruction += '.'
        
        return instruction
    
    def extract_recipe_from_db(self, recipe_id: int, recipe_row: tuple) -> RecipeDocument:
        """Extract and clean recipe data from database row"""
        (url, title, description, prep_time, cook_time, total_time,
         servings, calories, ingredients_json, instructions_json,
         category, cuisine, rating, review_count) = recipe_row
        
        # Parse JSON fields
        try:
            ingredients = json.loads(ingredients_json) if ingredients_json else []
            instructions = json.loads(instructions_json) if instructions_json else []
        except json.JSONDecodeError:
            ingredients = []
            instructions = []
        
        # Clean ingredients
        cleaned_ingredients = [self.clean_ingredient(ing) for ing in ingredients if ing]
        
        # Clean instructions
        cleaned_instructions = [self.clean_instruction(inst) for inst in instructions if inst]
        
        # Clean times
        prep_time_clean = self.clean_time_format(prep_time)
        cook_time_clean = self.clean_time_format(cook_time)
        total_time_clean = self.clean_time_format(total_time)
        
        # Clean description
        description_clean = self.clean_html_entities(description) if description else ""
        
        # Create structured text representations
        ingredients_text = "\n".join([f"- {ing}" for ing in cleaned_ingredients])
        instructions_text = "\n".join([f"{i+1}. {inst}" for i, inst in enumerate(cleaned_instructions)])
        
        # Create comprehensive searchable text
        # This is the main text that will be embedded
        full_text_parts = []
        
        # Title (weighted more heavily by including twice)
        full_text_parts.append(f"Recipe: {title}")
        full_text_parts.append(f"Dish: {title}")
        
        # Description
        if description_clean:
            full_text_parts.append(f"Description: {description_clean}")
        
        # Category and cuisine
        if category:
            full_text_parts.append(f"Category: {category}")
        if cuisine:
            full_text_parts.append(f"Cuisine: {cuisine}")
        
        # Time information
        full_text_parts.append(f"Preparation time: {prep_time_clean}")
        full_text_parts.append(f"Cooking time: {cook_time_clean}")
        full_text_parts.append(f"Total time: {total_time_clean}")
        
        # Servings
        if servings:
            full_text_parts.append(f"Servings: {servings}")
        
        # Ingredients (key for search)
        full_text_parts.append(f"Ingredients:\n{ingredients_text}")
        
        # Instructions
        full_text_parts.append(f"Instructions:\n{instructions_text}")
        
        # Combine all text
        full_text = "\n\n".join(full_text_parts)
        
        # Create metadata dictionary
        metadata = {
            "title": title,
            "category": category,
            "cuisine": cuisine,
            "prep_time": prep_time_clean,
            "cook_time": cook_time_clean,
            "total_time": total_time_clean,
            "servings": servings,
            "calories": calories,
            "rating": float(rating) if rating else None,
            "review_count": int(review_count) if review_count else 0,
            "ingredient_count": len(cleaned_ingredients),
            "step_count": len(cleaned_instructions),
            "url": url
        }
        
        return RecipeDocument(
            recipe_id=recipe_id,
            url=url,
            title=title,
            description=description_clean,
            full_text=full_text,
            ingredients_text=ingredients_text,
            instructions_text=instructions_text,
            metadata=metadata
        )
    
    def load_recipes_from_db(self):
        """Load all recipes from database and prepare documents"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, url, title, description, prep_time, cook_time, total_time,
                   servings, calories, ingredients, instructions, category, 
                   cuisine, rating, review_count
            FROM recipes
        """)
        
        recipes = cursor.fetchall()
        conn.close()
        
        print(f"📚 Loading {len(recipes)} recipes from database...")
        
        for recipe in recipes:
            recipe_id = recipe[0]
            recipe_data = recipe[1:]
            
            try:
                doc = self.extract_recipe_from_db(recipe_id, recipe_data)
                self.documents.append(doc)
            except Exception as e:
                print(f"⚠ Error processing recipe {recipe_id}: {str(e)}")
        
        print(f"✓ Loaded {len(self.documents)} recipe documents")
        
        return self.documents
    
    def export_for_embedding(self, output_path: str = "recipes_for_embedding.jsonl"):
        """Export cleaned documents in JSONL format for embedding"""
        with open(output_path, 'w') as f:
            for doc in self.documents:
                # Create embedding-ready format
                embedding_doc = {
                    "id": f"recipe_{doc.recipe_id}",
                    "text": doc.full_text,  # Main text to embed
                    "metadata": doc.metadata
                }
                f.write(json.dumps(embedding_doc) + "\n")
        
        print(f"✓ Exported {len(self.documents)} documents to {output_path}")
        
    def export_separate_fields(self, output_dir: str = "embedding_data"):
        """Export separate files for different embedding strategies"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Strategy 1: Full recipe text (comprehensive search)
        with open(f"{output_dir}/full_recipes.jsonl", 'w') as f:
            for doc in self.documents:
                f.write(json.dumps({
                    "id": f"recipe_{doc.recipe_id}",
                    "text": doc.full_text,
                    "metadata": doc.metadata
                }) + "\n")
        
        # Strategy 2: Ingredients only (ingredient-based search)
        with open(f"{output_dir}/ingredients_only.jsonl", 'w') as f:
            for doc in self.documents:
                f.write(json.dumps({
                    "id": f"recipe_{doc.recipe_id}_ingredients",
                    "text": f"{doc.title}\n\n{doc.ingredients_text}",
                    "metadata": doc.metadata
                }) + "\n")
        
        # Strategy 3: Title + Description (quick overview search)
        with open(f"{output_dir}/title_description.jsonl", 'w') as f:
            for doc in self.documents:
                text = f"{doc.title}\n\n{doc.description}" if doc.description else doc.title
                f.write(json.dumps({
                    "id": f"recipe_{doc.recipe_id}_summary",
                    "text": text,
                    "metadata": doc.metadata
                }) + "\n")
        
        print(f"✓ Exported separate embedding strategies to {output_dir}/")
    
    def get_statistics(self):
        """Get statistics about the processed documents"""
        if not self.documents:
            print("No documents loaded. Run load_recipes_from_db() first.")
            return
        
        total_docs = len(self.documents)
        avg_text_length = np.mean([len(doc.full_text) for doc in self.documents])
        avg_ingredients = np.mean([doc.metadata['ingredient_count'] for doc in self.documents])
        avg_steps = np.mean([doc.metadata['step_count'] for doc in self.documents])
        
        # Categories
        categories = {}
        cuisines = {}
        for doc in self.documents:
            cat = doc.metadata.get('category')
            if cat:
                categories[cat] = categories.get(cat, 0) + 1
            
            cui = doc.metadata.get('cuisine')
            if cui:
                cuisines[cui] = cuisines.get(cui, 0) + 1
        
        print(f"\n📊 Embedding Preparation Statistics:")
        print(f"   Total documents: {total_docs}")
        print(f"   Average text length: {avg_text_length:.0f} characters")
        print(f"   Average ingredients per recipe: {avg_ingredients:.1f}")
        print(f"   Average steps per recipe: {avg_steps:.1f}")
        print(f"\n   Categories: {len(categories)}")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"      - {cat}: {count}")
        
        if cuisines:
            print(f"\n   Cuisines: {len(cuisines)}")
            for cui, count in sorted(cuisines.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"      - {cui}: {count}")
    
    def preview_documents(self, n: int = 3):
        """Preview a few documents"""
        print(f"\n🔍 Preview of {min(n, len(self.documents))} documents:\n")
        
        for i, doc in enumerate(self.documents[:n]):
            print(f"{'='*80}")
            print(f"Document {i+1}: {doc.title}")
            print(f"{'='*80}")
            print(f"ID: recipe_{doc.recipe_id}")
            print(f"URL: {doc.url}")
            print(f"Category: {doc.metadata.get('category', 'N/A')}")
            print(f"Ingredients: {doc.metadata['ingredient_count']}")
            print(f"Steps: {doc.metadata['step_count']}")
            print(f"\nFull text preview (first 500 chars):")
            print(doc.full_text[:500] + "...")
            print()


def main():
    """Main function to prepare embeddings"""
    print("🚀 Recipe Embedding Preparation System\n")
    
    # Initialize
    prep = RecipeEmbeddingPrep(db_path="recipes.db")
    
    # Load recipes
    documents = prep.load_recipes_from_db()
    
    if not documents:
        print("❌ No recipes found in database. Run the scraper first!")
        return
    
    # Show statistics
    prep.get_statistics()
    
    # Preview some documents
    prep.preview_documents(n=2)
    
    # Export for embedding
    print(f"\n📤 Exporting documents for embedding...")
    
    # Option 1: Single file with full recipes (recommended for general RAG)
    prep.export_for_embedding("recipes_for_embedding.jsonl")
    
    # Option 2: Separate strategies (for multi-index approach)
    prep.export_separate_fields("embedding_data")
    
    print(f"\n✅ Embedding preparation complete!")
    print(f"\n💡 Next steps:")
    print(f"   1. Choose an embedding model (OpenAI, Cohere, or open-source)")
    print(f"   2. Generate embeddings from recipes_for_embedding.jsonl")
    print(f"   3. Store embeddings in a vector database (Pinecone, Weaviate, ChromaDB)")
    print(f"   4. Build your RAG query system")
    print(f"\n📝 Recommended approach:")
    print(f"   - Use 'recipes_for_embedding.jsonl' for comprehensive search")
    print(f"   - Or use separate files in 'embedding_data/' for specialized indexes")


if __name__ == "__main__":
    main()