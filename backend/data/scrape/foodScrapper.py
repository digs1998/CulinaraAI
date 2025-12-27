import asyncio
import json
import re
import sqlite3
import hashlib
from typing import List, Dict, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig


class RecipeScraper:
    def __init__(
        self,
        allowed_domains: List[str],
        max_recipes: int,
        db_path: str = "recipes.db",
    ):
        self.allowed_domains = set(allowed_domains)
        self.max_recipes = max_recipes
        self.db_path = db_path

        self.visited_urls: Set[str] = set()
        self.seen_hashes: Set[str] = set()
        self.recipes: List[Dict] = []

        self.browser_config = BrowserConfig(
            browser_type="firefox",
            headless=True,
            verbose=False,
        )

        self.crawl_config = CrawlerRunConfig(
            cache_mode="BYPASS",
            page_timeout=30000,
            wait_for=None,
        )

    # ---------------------------
    # Database
    # ---------------------------

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                content_hash TEXT UNIQUE,
                title TEXT,
                description TEXT,
                ingredients TEXT,
                instructions TEXT,
                category TEXT,
                cuisine TEXT,
                rating REAL,
                review_count INTEGER,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.commit()
        conn.close()
        print(f"✓ Database initialized: {self.db_path}")

    # ---------------------------
    # Utility
    # ---------------------------

    def recipe_fingerprint(self, recipe):
        title = recipe.get("title", "")
        
        # Ingredients: join as strings
        ingredients = "".join(
            i if isinstance(i, str) else str(i)
            for i in recipe.get("ingredients", [])
        )
        
        # Instructions: extract text if dict has 'text', else str
        instructions = "".join(
            i.get("text") if isinstance(i, dict) and "text" in i else str(i)
            for i in recipe.get("instructions", [])
        )
        
        return title + ingredients + instructions

    # ---------------------------
    # Crawling
    # ---------------------------

    async def scrape_page(self, url: str, crawler: AsyncWebCrawler):
        try:
            result = await crawler.arun(url=url, config=self.crawl_config)
            return result.html if result.success else None
        except Exception:
            return None

    def extract_recipe_links(self, html: str, base_url: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links = set()

        for tag in soup.find_all("a", href=True):
            full_url = urljoin(base_url, tag["href"])
            parsed = urlparse(full_url)

            if parsed.netloc not in self.allowed_domains:
                continue

            if re.search(r"/recipe[s]?/", parsed.path, re.I):
                links.add(full_url)

        return list(links)

    # ---------------------------
    # Parsing
    # ---------------------------

    def extract_recipe_data(self, html: str, url: str) -> Dict:
        soup = BeautifulSoup(html, "html.parser")

        recipe = {
            "url": url,
            "title": None,
            "description": None,
            "ingredients": [],
            "instructions": [],
            "category": None,
            "cuisine": None,
            "rating": None,
            "review_count": None,
        }

        # JSON-LD (canonical path)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    data = next(
                        (x for x in data if x.get("@type") == "Recipe"), None
                    )

                if data and data.get("@type") == "Recipe":
                    recipe["title"] = data.get("name")
                    recipe["description"] = data.get("description")
                    recipe["ingredients"] = data.get("recipeIngredient", [])

                    instructions = data.get("recipeInstructions", [])
                    if isinstance(instructions, list):
                        recipe["instructions"] = [
                            step.get("text", step)
                            if isinstance(step, dict)
                            else step
                            for step in instructions
                        ]
                    elif isinstance(instructions, str):
                        recipe["instructions"] = [instructions]

                    rating = data.get("aggregateRating", {})
                    recipe["rating"] = rating.get("ratingValue")
                    recipe["review_count"] = rating.get("reviewCount")

                    recipe["category"] = data.get("recipeCategory")
                    recipe["cuisine"] = data.get("recipeCuisine")
                    break
            except Exception:
                continue

        return recipe

    # ---------------------------
    # Persistence
    # ---------------------------

    def save_recipe(self, recipe: Dict):
        content_hash = self.recipe_fingerprint(recipe)
        if content_hash in self.seen_hashes:
            return

        self.seen_hashes.add(content_hash)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO recipes (
                    url, content_hash, title, description,
                    ingredients, instructions,
                    category, cuisine, rating, review_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recipe["url"],
                    content_hash,
                    recipe["title"],
                    recipe["description"],
                    json.dumps(recipe["ingredients"]),
                    json.dumps(recipe["instructions"]),
                    recipe["category"],
                    recipe["cuisine"],
                    recipe["rating"],
                    recipe["review_count"],
                ),
            )
            conn.commit()
            self.recipes.append(recipe)
            print(f"✓ Saved: {recipe['title']}")
        finally:
            conn.close()

    # ---------------------------
    # Main pipeline
    # ---------------------------

    async def scrape_recipe_page(self, url: str, crawler: AsyncWebCrawler):
        if url in self.visited_urls:
            return

        self.visited_urls.add(url)
        html = await self.scrape_page(url, crawler)
        if not html:
            return

        recipe = self.extract_recipe_data(html, url)
        if recipe["title"] and recipe["ingredients"]:
            self.save_recipe(recipe)

    async def scrape_recipes(self, start_urls: List[str]):
        self.init_database()

        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            all_links = set()

            print("📋 Collecting recipe links...")
            for start_url in start_urls:
                html = await self.scrape_page(start_url, crawler)
                if html:
                    links = self.extract_recipe_links(html, start_url)
                    all_links.update(links)
                await asyncio.sleep(1)

            print(f"✓ Found {len(all_links)} candidate recipes")

            for url in list(all_links)[: self.max_recipes]:
                await self.scrape_recipe_page(url, crawler)
                if len(self.recipes) >= self.max_recipes:
                    break
                await asyncio.sleep(0.5)

        return self.recipes

    # ---------------------------
    # Export
    # ---------------------------

    def export_to_json(self, filename="recipes.json"):
        with open(filename, "w") as f:
            json.dump(self.recipes, f, indent=2)
        print(f"✓ Exported {len(self.recipes)} recipes → {filename}")


# ---------------------------
# Entry point
# ---------------------------

async def main():
    scraper = RecipeScraper(
        allowed_domains=[
            "www.food.com",
            "www.allrecipes.com",
            "www.seriouseats.com",
            "www.bbcgoodfood.com",
            "www.americastestkitchen.com",
            "www.blueapron.com",
        ],
        max_recipes=500,
    )

    start_urls = [
        "https://www.food.com/",
        "https://www.allrecipes.com/",
        "https://www.seriouseats.com/",
        "https://www.bbcgoodfood.com/",
        "https://www.americastestkitchen.com/",
        "https://www.blueapron.com/cookbook/",
    ]

    recipes = await scraper.scrape_recipes(start_urls)
    scraper.export_to_json("recipes_backup.json")

    print(f"\n🎉 Done. Scraped {len(recipes)} recipes.")


# if __name__ == "__main__":
#     asyncio.run(main())
