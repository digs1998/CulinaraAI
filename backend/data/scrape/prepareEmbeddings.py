# prepareEmbeddings.py

import json
import sqlite3
import html
from typing import List, Optional
from dataclasses import dataclass
import numpy as np

# ============================================================
# Data Model
# ============================================================
@dataclass
class RecipeDocument:
    recipe_id: int
    url: str
    title: str
    description: str
    full_text: str
    ingredients_text: str
    instructions_text: str
    metadata: dict


# ============================================================
# Embedding Preparation
# ============================================================
class RecipeEmbeddingPrep:
    def __init__(self, db_path: str = "recipes.db"):
        self.db_path = db_path
        self.documents: List[RecipeDocument] = []

    # ----------------------------
    # Cleaning helpers
    # ----------------------------
    def clean_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        text = html.unescape(text)
        text = " ".join(text.split())
        return text.strip()

    def clean_ingredient(self, ingredient: str) -> str:
        return self.clean_text(ingredient).strip("., ")

    def clean_instruction(self, instruction: str) -> str:
        text = self.clean_text(instruction)
        if text and not text.endswith("."):
            text += "."
        return text

    # ----------------------------
    # Normalize lists
    # ----------------------------
    def normalize_list(self, value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return [value]
        if isinstance(value, str):
            return [value]
        return []

    # ----------------------------
    # DB extraction
    # ----------------------------
    def extract_recipe_from_row(
        self,
        recipe_id: int,
        row: tuple,
    ) -> RecipeDocument:

        (
            url,
            title,
            description,
            ingredients_json,
            instructions_json,
            category,
            cuisine,
            rating,
        ) = row

        # Parse JSON safely
        try:
            ingredients_raw = json.loads(ingredients_json) if ingredients_json else []
        except Exception:
            ingredients_raw = ingredients_json or []

        try:
            instructions_raw = json.loads(instructions_json) if instructions_json else []
        except Exception:
            instructions_raw = instructions_json or []

        # Normalize to lists
        ingredients = self.normalize_list(ingredients_raw)
        instructions = self.normalize_list(instructions_raw)

        # Clean ingredients and instructions
        cleaned_ingredients = [
            self.clean_ingredient(i.get("text") if isinstance(i, dict) else str(i))
            for i in ingredients
            if i
        ]

        cleaned_instructions = [
            self.clean_instruction(i.get("text") if isinstance(i, dict) else str(i))
            for i in instructions
            if i
        ]

        ingredients_text = "\n".join(f"- {i}" for i in cleaned_ingredients)
        instructions_text = "\n".join(f"{idx+1}. {step}" for idx, step in enumerate(cleaned_instructions))

        # Compose full text
        full_text_parts = [
            f"Recipe: {title}",
            f"Ingredients:\n{ingredients_text}",
            f"Instructions:\n{instructions_text}"
        ]

        if description:
            full_text_parts.insert(1, f"Description: {self.clean_text(description)}")
        if category:
            full_text_parts.append(f"Category: {category}")
        if cuisine:
            full_text_parts.append(f"Cuisine: {cuisine}")

        full_text = "\n\n".join(full_text_parts)

        # Metadata
        metadata = {
            "title": title,
            "category": category,
            "cuisine": cuisine,
            "rating": float(rating) if rating is not None else None,
            "ingredient_count": len(cleaned_ingredients),
            "step_count": len(cleaned_instructions),
            "url": url,
        }
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return RecipeDocument(
            recipe_id=recipe_id,
            url=url,
            title=title,
            description=self.clean_text(description),
            full_text=full_text,
            ingredients_text=ingredients_text,
            instructions_text=instructions_text,
            metadata=metadata,
        )

    # ----------------------------
    # Load all recipes
    # ----------------------------
    def load_recipes_from_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                url,
                title,
                description,
                ingredients,
                instructions,
                category,
                cuisine,
                rating
            FROM recipes
        """)

        rows = cursor.fetchall()
        conn.close()

        print(f"📚 Loading {len(rows)} recipes from database")

        for row in rows:
            recipe_id = row[0]
            try:
                doc = self.extract_recipe_from_row(recipe_id, row[1:])
                self.documents.append(doc)
            except Exception as e:
                print(f"⚠ Failed recipe {recipe_id}: {e}")

        print(f"✓ Prepared {len(self.documents)} documents")
        return self.documents

    # ----------------------------
    # Export
    # ----------------------------
    def export_for_embedding(self, output_path: str):
        with open(output_path, "w") as f:
            for doc in self.documents:
                f.write(
                    json.dumps({
                        "id": f"recipe_{doc.recipe_id}",
                        "text": doc.full_text,
                        "metadata": doc.metadata,
                    }) + "\n"
                )
        print(f"✓ Exported {len(self.documents)} docs → {output_path}")

    # ----------------------------
    # Stats
    # ----------------------------
    def get_statistics(self):
        if not self.documents:
            return

        avg_text_len = np.mean([len(d.full_text) for d in self.documents])
        avg_ingredients = np.mean([d.metadata["ingredient_count"] for d in self.documents])
        avg_steps = np.mean([d.metadata["step_count"] for d in self.documents])

        print("\n📊 Stats")
        print(f"   Documents: {len(self.documents)}")
        print(f"   Avg text length: {avg_text_len:.0f}")
        print(f"   Avg ingredients: {avg_ingredients:.1f}")
        print(f"   Avg steps: {avg_steps:.1f}")


# ----------------------------
# CLI
# ----------------------------
def main():
    print("🚀 Recipe Embedding Prep\n")
    prep = RecipeEmbeddingPrep("recipes.db")
    docs = prep.load_recipes_from_db()

    if not docs:
        print("❌ No recipes found")
        return

    prep.get_statistics()
    prep.export_for_embedding("recipes_for_embedding.jsonl")
    print("\n✅ Ready for Chroma ingestion")


if __name__ == "__main__":
    main()
