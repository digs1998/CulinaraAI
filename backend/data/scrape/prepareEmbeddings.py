# prepareEmbeddings.py

import json
import sqlite3
import html
from typing import List, Optional
from dataclasses import dataclass
import numpy as np


# ===============================
# Data model
# ===============================
@dataclass
class RecipeDocument:
    recipe_id: int
    url: str
    title: str
    description: str
    full_text: str
    ingredients_text: str
    instructions_text: str
    ingredients_list: List[str]  # NEW: Keep original list
    instructions_list: List[str]  # NEW: Keep original list
    metadata: dict


# ===============================
# Embedding preparation
# ===============================
class RecipeEmbeddingPrep:
    def __init__(self, db_path):
        self.db_path = db_path
        self.documents: List[RecipeDocument] = []

    # -----------------------------
    # Cleaning helpers
    # -----------------------------
    def clean_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        text = html.unescape(str(text))
        text = " ".join(text.split())
        return text.strip()

    def clean_ingredient(self, ingredient) -> str:
        if isinstance(ingredient, dict):
            ingredient = " ".join(str(v) for v in ingredient.values())
        return self.clean_text(str(ingredient))

    def clean_instruction(self, instruction) -> str:
        if isinstance(instruction, dict):
            instruction = " ".join(str(v) for v in instruction.values())
        text = self.clean_text(str(instruction))
        if text and not text.endswith("."):
            text += "."
        return text

    # -----------------------------
    # Extract recipe from DB row
    # -----------------------------
    def extract_recipe_from_row(self, recipe_id: int, row: tuple) -> RecipeDocument:
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

        # parse JSON safely
        try:
            ingredients = json.loads(ingredients_json or "[]")
        except json.JSONDecodeError:
            ingredients = []

        try:
            instructions = json.loads(instructions_json or "[]")
        except json.JSONDecodeError:
            instructions = []

        # clean
        cleaned_ingredients = [self.clean_ingredient(i) for i in ingredients if i]
        cleaned_instructions = [self.clean_instruction(i) for i in instructions if i]

        ingredients_text = "\n".join(f"- {i}" for i in cleaned_ingredients)
        instructions_text = "\n".join(f"{idx+1}. {step}" for idx, step in enumerate(cleaned_instructions))

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

        # CRITICAL: Include ingredients and instructions in metadata for RAG search
        metadata = {
            "id": f"recipe_{recipe_id}",
            "title": title,
            "category": category,
            "cuisine": cuisine,
            "rating": float(rating) if rating is not None else None,
            "ingredient_count": len(cleaned_ingredients),
            "step_count": len(cleaned_instructions),
            "url": url,
            "ingredients": cleaned_ingredients,  # Full ingredients list
            "instructions": cleaned_instructions,  # Full instructions list
            # Placeholder facts (can be populated from JSON-LD if available)
            "prep_time": None,
            "cook_time": None,
            "total_time": None,
            "servings": None,
            "calories": None,
        }
        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return RecipeDocument(
            recipe_id=recipe_id,
            url=url,
            title=title,
            description=self.clean_text(description),
            full_text=full_text,
            ingredients_text=ingredients_text,
            instructions_text=instructions_text,
            ingredients_list=cleaned_ingredients,
            instructions_list=cleaned_instructions,
            metadata=metadata,
        )

    # -----------------------------
    # Load all recipes
    # -----------------------------
    def load_recipes_from_db(self) -> List[RecipeDocument]:
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
                print(f"⚠️ Failed recipe {recipe_id}: {e}")

        print(f"✅ Prepared {len(self.documents)} documents")
        return self.documents

    # -----------------------------
    # Export for embedding
    # -----------------------------
    def export_for_embedding(self, output_path: str):
        with open(output_path, "w") as f:
            for doc in self.documents:
                f.write(
                    json.dumps({
                        "id": doc.metadata["id"],
                        "text": doc.full_text,
                        "metadata": doc.metadata,
                    }) + "\n"
                )
        print(f"✅ Exported {len(self.documents)} docs → {output_path}")

    # -----------------------------
    # Stats
    # -----------------------------
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