# services/recipe_scraper_pipeline.py
import asyncio
from urllib.parse import urlparse, urljoin, unquote
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from bs4 import BeautifulSoup
import json
import re

# ----------------------------
# Utility to normalize URLs
# ----------------------------
def normalize_url(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url.lstrip("/")
    return url

def unwrap_duckduckgo(url: str) -> str:
    """Remove DuckDuckGo redirect wrapper"""
    if "duckduckgo.com/l/?" in url:
        parsed = urlparse(url)
        qs = parsed.query
        for part in qs.split("&"):
            if part.startswith("uddg="):
                return unquote(part.split("=", 1)[1])
    return url

# ----------------------------
# Web Recipe Scraper Class
# ----------------------------
class WebRecipeScraper:
    def __init__(self):
        self.browser_config = BrowserConfig(
            browser_type="firefox", 
            headless=True, 
            verbose=False
        )
        self.crawl_config = CrawlerRunConfig(
            cache_mode="BYPASS", 
            page_timeout=25000,  # Reduced timeout
            wait_for=None
        )

    async def fetch_page_html(self, url: str, crawler: AsyncWebCrawler):
        """Fetch HTML from URL with error handling"""
        try:
            result = await crawler.arun(url=url, config=self.crawl_config)
            if result.success and result.html:
                return result.html
            else:
                print(f"    ⚠️ Crawler returned unsuccessful result for {url[:50]}")
                return None
        except asyncio.TimeoutError:
            print(f"    ⚠️ Timeout fetching {url[:50]}")
            return None
        except Exception as e:
            print(f"    ⚠️ Error fetching {url[:50]}: {str(e)[:100]}")
            return None

    def parse_recipe(self, html: str, url: str) -> dict:
        """Parse recipe from HTML with fallback strategies"""
        soup = BeautifulSoup(html, "html.parser")

        # Strategy 1: Attempt JSON-LD first (best quality)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    # Sometimes recipes are in a list
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Recipe":
                            data = item
                            break
                
                if isinstance(data, dict) and data.get("@type") == "Recipe":
                    # Parse instructions
                    instructions = data.get("recipeInstructions", [])
                    if isinstance(instructions, list):
                        instructions = [
                            step.get("text") if isinstance(step, dict) else str(step)
                            for step in instructions
                        ]
                    elif isinstance(instructions, str):
                        instructions = [instructions]
                    
                    # Parse ingredients
                    ingredients = data.get("recipeIngredient", [])
                    if not isinstance(ingredients, list):
                        ingredients = [str(ingredients)]

                    return {
                        "title": data.get("name", "Recipe"),
                        "ingredients": ingredients,
                        "instructions": instructions,
                        "facts": {
                            "prep_time": data.get("prepTime"),
                            "cook_time": data.get("cookTime"),
                            "total_time": data.get("totalTime"),
                            "servings": data.get("recipeYield"),
                            "calories": data.get("nutrition", {}).get("calories")
                            if isinstance(data.get("nutrition"), dict) else None
                        },
                        "source": url
                    }
            except (json.JSONDecodeError, AttributeError, KeyError) as e:
                continue

        # Strategy 2: Look for common recipe markup patterns
        title_tag = soup.find("h1") or soup.find("h2", class_=re.compile(r"recipe|title"))
        title = title_tag.get_text(strip=True) if title_tag else "Recipe"

        # Find ingredients (common patterns)
        ingredients = []
        for pattern in ["ingredient", "ingred", "item"]:
            ing_list = soup.find_all("li", class_=re.compile(pattern, re.I))
            if ing_list:
                ingredients = [li.get_text(strip=True) for li in ing_list[:20]]
                break
        
        # Find instructions (common patterns)
        instructions = []
        for pattern in ["instruction", "step", "direction", "method"]:
            inst_list = soup.find_all("li", class_=re.compile(pattern, re.I))
            if inst_list:
                instructions = [li.get_text(strip=True) for li in inst_list[:20]]
                break
        
        # If still no instructions, try paragraphs in specific sections
        if not instructions:
            for pattern in ["instruction", "step", "direction", "method", "procedure"]:
                section = soup.find(class_=re.compile(pattern, re.I))
                if section:
                    paragraphs = section.find_all("p")
                    instructions = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20][:15]
                    if instructions:
                        break

        # Only return if we have meaningful data
        if ingredients or instructions:
            return {
                "title": title,
                "ingredients": ingredients,
                "instructions": instructions,
                "facts": {},
                "source": url
            }
        
        # Failed to extract recipe
        return None

    async def scrape_recipe_from_url(self, url: str, retries=1) -> dict:
        """Scrape recipe from URL with retry logic"""
        url = normalize_url(url)
        
        for attempt in range(retries):
            try:
                async with AsyncWebCrawler(config=self.browser_config) as crawler:
                    html = await self.fetch_page_html(url, crawler)
                    if html:
                        recipe = self.parse_recipe(html, url)
                        if recipe:
                            return recipe
                        else:
                            print(f"    ⚠️ Could not parse recipe from HTML")
            except Exception as e:
                print(f"    ⚠️ Scraping attempt {attempt + 1} failed: {str(e)[:80]}")
                if attempt < retries - 1:
                    await asyncio.sleep(1)  # Brief pause before retry
                    continue
        
        # All attempts failed
        return {
            "title": "Could not fetch recipe",
            "ingredients": [],
            "instructions": [],
            "facts": {},
            "source": url
        }


# ----------------------------
# Entry point for MCP fallback
# ----------------------------
def scrape_recipe_via_mcp(url: str) -> dict:
    """
    Synchronous wrapper to call async Crawl4AI scraper.
    Returns structured recipe dict ready for MCP.
    """
    url = unwrap_duckduckgo(url)
    scraper = WebRecipeScraper()
    
    try:
        recipe = asyncio.run(scraper.scrape_recipe_from_url(url))
        return recipe
    except Exception as e:
        print(f"    ⚠️ Fatal error in scrape_recipe_via_mcp: {str(e)[:100]}")
        return {
            "title": "Could not fetch recipe",
            "ingredients": [],
            "instructions": [],
            "facts": {},
            "source": url
        }