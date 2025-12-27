import asyncio
import json
import re
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Set
from datetime import datetime
from bs4 import BeautifulSoup
import sqlite3

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig


class RecipeScraper:
    def __init__(self, base_url: str = "https://www.food.com", max_recipes: int = 100):
        self.base_url = base_url
        self.max_recipes = max_recipes
        self.visited_urls: Set[str] = set()
        self.recipes: List[Dict] = []
        self.db_path = "recipes.db"
        
        # Configure Crawl4AI browser settings
        self.browser_config = BrowserConfig(
            browser_type="firefox",  # Using Firefox as it works on your ARM Mac
            headless=True,
            verbose=False
        )
        
        self.crawl_config = CrawlerRunConfig(
            cache_mode="BYPASS",
            page_timeout=30000,
            wait_for=None  # Don't wait for networkidle - it times out
        )
        
    def init_database(self):
        """Initialize SQLite database for storing recipes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create recipes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                description TEXT,
                prep_time TEXT,
                cook_time TEXT,
                total_time TEXT,
                servings TEXT,
                calories TEXT,
                ingredients TEXT,
                instructions TEXT,
                category TEXT,
                cuisine TEXT,
                rating REAL,
                review_count INTEGER,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create ingredients table (normalized)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER,
                ingredient_text TEXT,
                quantity TEXT,
                unit TEXT,
                item TEXT,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✓ Database initialized: {self.db_path}")
    
    def extract_recipe_links(self, html: str) -> List[str]:
        """Extract recipe URLs from a page"""
        soup = BeautifulSoup(html, 'html.parser')
        recipe_links = []
        
        # Find all links that match recipe pattern
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Recipe URLs typically follow pattern: /recipe/recipe-name-12345
            if '/recipe/' in href and re.search(r'/recipe/[\w-]+-\d+', href):
                full_url = urljoin(self.base_url, href)
                if full_url not in self.visited_urls:
                    recipe_links.append(full_url)
        
        return list(set(recipe_links))  # Remove duplicates
    
    def extract_recipe_data(self, html: str, url: str) -> Dict:
        """Extract structured recipe data from a recipe page"""
        soup = BeautifulSoup(html, 'html.parser')
        recipe_data = {
            'url': url,
            'title': None,
            'description': None,
            'prep_time': None,
            'cook_time': None,
            'total_time': None,
            'servings': None,
            'calories': None,
            'ingredients': [],
            'instructions': [],
            'category': None,
            'cuisine': None,
            'rating': None,
            'review_count': None
        }
        
        # Try to find JSON-LD structured data first (most reliable)
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        
        for json_ld in json_ld_scripts:
            try:
                data = json.loads(json_ld.string)
                
                # Handle both single objects and arrays
                if isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'Recipe':
                            data = item
                            break
                
                if data.get('@type') == 'Recipe':
                    recipe_data['title'] = data.get('name')
                    recipe_data['description'] = data.get('description')
                    recipe_data['prep_time'] = data.get('prepTime')
                    recipe_data['cook_time'] = data.get('cookTime')
                    recipe_data['total_time'] = data.get('totalTime')
                    recipe_data['servings'] = str(data.get('recipeYield', ''))
                    recipe_data['ingredients'] = data.get('recipeIngredient', [])
                    
                    # Extract instructions
                    instructions = data.get('recipeInstructions', [])
                    if isinstance(instructions, list):
                        recipe_data['instructions'] = [
                            step.get('text', step) if isinstance(step, dict) else step
                            for step in instructions
                        ]
                    elif isinstance(instructions, str):
                        recipe_data['instructions'] = [instructions]
                    
                    # Extract rating
                    if 'aggregateRating' in data:
                        rating_data = data['aggregateRating']
                        recipe_data['rating'] = rating_data.get('ratingValue')
                        recipe_data['review_count'] = rating_data.get('reviewCount')
                    
                    # Extract category/cuisine
                    recipe_data['category'] = data.get('recipeCategory')
                    recipe_data['cuisine'] = data.get('recipeCuisine')
                    
                    # Extract calories
                    if 'nutrition' in data:
                        recipe_data['calories'] = data['nutrition'].get('calories')
                    
                    break  # Found recipe data, exit loop
            
            except (json.JSONDecodeError, AttributeError) as e:
                continue
        
        # Fallback: Parse HTML if JSON-LD not available
        if not recipe_data['title']:
            title_tag = soup.find('h1')
            if title_tag:
                recipe_data['title'] = title_tag.get_text(strip=True)
        
        if not recipe_data['ingredients']:
            # Try to find ingredients in HTML
            ingredient_elements = soup.find_all(['li', 'span'], class_=re.compile(r'ingredient', re.I))
            recipe_data['ingredients'] = [ing.get_text(strip=True) for ing in ingredient_elements if ing.get_text(strip=True)]
        
        if not recipe_data['instructions']:
            # Try to find instructions
            instruction_elements = soup.find_all(['li', 'div', 'p'], class_=re.compile(r'(instruction|direction|step)', re.I))
            recipe_data['instructions'] = [inst.get_text(strip=True) for inst in instruction_elements if inst.get_text(strip=True)]
        
        return recipe_data
    
    def parse_ingredient(self, ingredient_text: str) -> Dict:
        """Parse ingredient text into structured components"""
        quantity_pattern = r'^([\d\s\/\-\.]+)'
        unit_pattern = r'(cup|cups|tablespoon|tablespoons|teaspoon|teaspoons|tbsp|tsp|ounce|ounces|oz|pound|pounds|lb|lbs|gram|grams|g|kg|ml|l|pinch|dash|clove|cloves)'
        
        result = {
            'quantity': None,
            'unit': None,
            'item': ingredient_text
        }
        
        # Extract quantity
        quantity_match = re.match(quantity_pattern, ingredient_text.strip())
        if quantity_match:
            result['quantity'] = quantity_match.group(1).strip()
            remaining = ingredient_text[quantity_match.end():].strip()
            
            # Extract unit
            unit_match = re.match(unit_pattern, remaining, re.IGNORECASE)
            if unit_match:
                result['unit'] = unit_match.group(1).lower()
                result['item'] = remaining[unit_match.end():].strip()
            else:
                result['item'] = remaining
        
        return result
    
    def save_recipe_to_db(self, recipe_data: Dict):
        """Save recipe data to SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Insert recipe
            cursor.execute('''
                INSERT OR REPLACE INTO recipes 
                (url, title, description, prep_time, cook_time, total_time, 
                 servings, calories, ingredients, instructions, category, 
                 cuisine, rating, review_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                recipe_data['url'],
                recipe_data['title'],
                recipe_data['description'],
                recipe_data['prep_time'],
                recipe_data['cook_time'],
                recipe_data['total_time'],
                recipe_data['servings'],
                recipe_data['calories'],
                json.dumps(recipe_data['ingredients']),
                json.dumps(recipe_data['instructions']),
                recipe_data['category'],
                recipe_data['cuisine'],
                recipe_data['rating'],
                recipe_data['review_count']
            ))
            
            recipe_id = cursor.lastrowid
            
            # Insert parsed ingredients
            for ingredient_text in recipe_data['ingredients']:
                parsed = self.parse_ingredient(ingredient_text)
                cursor.execute('''
                    INSERT INTO ingredients (recipe_id, ingredient_text, quantity, unit, item)
                    VALUES (?, ?, ?, ?, ?)
                ''', (recipe_id, ingredient_text, parsed['quantity'], parsed['unit'], parsed['item']))
            
            conn.commit()
            print(f"✓ Saved: {recipe_data['title']}")
            
        except sqlite3.IntegrityError:
            print(f"⚠ Duplicate: {recipe_data['url']}")
        except Exception as e:
            print(f"✗ Error saving recipe: {str(e)}")
        finally:
            conn.close()
    
    async def scrape_page(self, url: str, crawler: AsyncWebCrawler):
        """Scrape a single page using Crawl4AI"""
        try:
            result = await crawler.arun(
                url=url,
                config=self.crawl_config
            )
            
            if result.success:
                return result.html
            else:
                print(f"✗ Failed to crawl {url}: {result.error_message}")
                return None
        except Exception as e:
            print(f"✗ Error crawling {url}: {str(e)}")
            return None
    
    async def scrape_recipe_page(self, url: str, crawler: AsyncWebCrawler):
        """Scrape a single recipe page"""
        if url in self.visited_urls:
            return
        
        self.visited_urls.add(url)
        
        html = await self.scrape_page(url, crawler)
        if not html:
            return
        
        # Extract recipe data
        recipe_data = self.extract_recipe_data(html, url)
        
        if recipe_data['title'] and recipe_data['ingredients']:
            self.recipes.append(recipe_data)
            self.save_recipe_to_db(recipe_data)
            print(f"📝 Scraped recipe {len(self.recipes)}/{self.max_recipes}: {recipe_data['title']}")
        else:
            print(f"⚠ Incomplete data for {url}")
    
    async def scrape_recipes(self, start_urls: List[str] = None):
        """Main scraping function using Crawl4AI"""
        if start_urls is None:
            # Default starting points - popular recipe collections
            start_urls = [
                "https://www.food.com/recipe/all/trending",
                "https://www.food.com/ideas/quick-and-easy-dinners-6510",
                "https://www.food.com/ideas/top-casseroles-6016",
                "https://www.food.com/ideas/best-chicken-recipes-6013"
            ]
        
        print(f"🚀 Starting recipe scraper with Crawl4AI (Firefox)...")
        print(f"   Max recipes: {self.max_recipes}")
        print(f"   Start URLs: {len(start_urls)}")
        
        self.init_database()
        
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            # First, collect recipe links from start pages
            all_recipe_links = []
            
            print("\n📋 Collecting recipe links...")
            for start_url in start_urls:
                print(f"   Crawling: {start_url}")
                html = await self.scrape_page(start_url, crawler)
                if html:
                    links = self.extract_recipe_links(html)
                    all_recipe_links.extend(links)
                    print(f"   ✓ Found {len(links)} recipes")
                await asyncio.sleep(1)  # Be polite
            
            # Remove duplicates and limit
            unique_links = list(set(all_recipe_links))[:self.max_recipes]
            print(f"\n✓ Total unique recipe links: {len(unique_links)}")
            
            # Scrape each recipe page
            print(f"\n🔍 Scraping recipe pages...\n")
            
            for i, url in enumerate(unique_links):
                await self.scrape_recipe_page(url, crawler)
                
                if len(self.recipes) >= self.max_recipes:
                    print(f"\n✓ Reached max recipes limit ({self.max_recipes})")
                    break
                
                # Be polite - delay between requests
                if (i + 1) % 5 == 0:
                    print(f"   ... processed {i + 1}/{len(unique_links)} pages")
                    await asyncio.sleep(2)
                else:
                    await asyncio.sleep(0.5)
        
        print(f"\n✅ Scraping complete!")
        print(f"   Total recipes scraped: {len(self.recipes)}")
        print(f"   Database: {self.db_path}")
        
        return self.recipes
    
    def export_to_json(self, filename: str = "recipes.json"):
        """Export recipes to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.recipes, f, indent=2)
        print(f"✓ Exported to {filename}")
    
    def get_stats(self):
        """Get statistics from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM recipes")
        total_recipes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ingredients")
        total_ingredients = cursor.fetchone()[0]
        
        cursor.execute("SELECT category, COUNT(*) FROM recipes WHERE category IS NOT NULL GROUP BY category")
        categories = cursor.fetchall()
        
        cursor.execute("SELECT AVG(rating) FROM recipes WHERE rating IS NOT NULL")
        avg_rating = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"\n📊 Database Statistics:")
        print(f"   Total recipes: {total_recipes}")
        print(f"   Total ingredients: {total_ingredients}")
        if avg_rating:
            print(f"   Average rating: {avg_rating:.2f}")
        print(f"   Categories: {len(categories)}")
        if categories:
            print(f"   Top categories:")
            for cat, count in sorted(categories, key=lambda x: x[1], reverse=True)[:5]:
                print(f"      - {cat}: {count}")


async def main():
    # Create scraper instance
    scraper = RecipeScraper(max_recipes=50)  # Start with 50 recipes
    
    # IMPORTANT: Use the FULL URLs with https://www.food.com
    custom_start_urls = [
        "https://www.food.com/"
    ]
    
    # Run the scraper
    recipes = await scraper.scrape_recipes(custom_start_urls)
    
    # Export to JSON for backup
    scraper.export_to_json("recipes_backup.json")
    
    # Show statistics
    scraper.get_stats()
    
    print("\n🎉 Done! Your recipes are ready for RAG.")
    print(f"   Database: {scraper.db_path}")
    print(f"   Recipes: {len(recipes)}")
    print(f"\n💡 Next steps:")
    print(f"   1. Create embeddings from the recipe data")
    print(f"   2. Store in your vector database")
    print(f"   3. Build your RAG Q&A system!")


if __name__ == "__main__":
    asyncio.run(main())