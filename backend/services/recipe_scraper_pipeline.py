# services/recipe_scraper_pipeline.py
import asyncio
from urllib.parse import urlparse, urljoin, unquote
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from bs4 import BeautifulSoup
import json
import re
import html

# ----------------------------
# Utility to normalize URLs
# ----------------------------
def normalize_url(url: str) -> str:
    if not isinstance(url, str):
        url = str(url)
    if not url.startswith("http"):
        url = "https://" + url.lstrip("/")
    return url

def unwrap_duckduckgo(url: str) -> str:
    """Remove DuckDuckGo redirect wrapper"""
    if not isinstance(url, str):
        url = str(url)
    if "duckduckgo.com/l/?" in url:
        parsed = urlparse(url)
        qs = parsed.query
        for part in qs.split("&"):
            if part.startswith("uddg="):
                return unquote(part.split("=", 1)[1])
    return url

def parse_iso_duration(duration: str) -> str:
    """
    Convert ISO 8601 duration (PT10M, PT1H30M, etc.) to readable format.
    """
    if not duration or not isinstance(duration, str):
        return None

    duration = duration.strip().upper()
    if not duration.startswith('PT'):
        return duration

    duration = duration[2:]
    hours = 0
    minutes = 0

    if 'H' in duration:
        parts = duration.split('H')
        try:
            hours = int(parts[0])
            duration = parts[1] if len(parts) > 1 else ''
        except:
            pass

    if 'M' in duration:
        parts = duration.split('M')
        try:
            minutes = int(parts[0])
        except:
            pass

    result = []
    if hours > 0:
        result.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        result.append(f"{minutes} min{'s' if minutes != 1 else ''}")

    return ' '.join(result) if result else None

def clean_text(text: str) -> str:
    """Decode HTML entities like &#38; -> &"""
    if not text or not isinstance(text, str):
        return text
    return html.unescape(text)


def extract_recipe_from_item_list_entry(item: dict, collection_url: str) -> dict:
    """
    Extract recipe data directly from an ItemList entry.
    
    Many sites (like Delish) embed full recipe info in the ItemList JSON-LD:
    - name: Recipe title
    - description: Recipe description (often contains "Get the X recipe" link text)
    - image: Recipe image URL
    - url: Fragment URL like #slide-1 (not a separate page)
    
    Returns a recipe dict or None if not enough data.
    """
    if not isinstance(item, dict):
        return None
    
    name = item.get('name') or (item.get('item', {}).get('name') if isinstance(item.get('item'), dict) else None)
    description = item.get('description') or (item.get('item', {}).get('description') if isinstance(item.get('item'), dict) else None)
    image = item.get('image') or (item.get('item', {}).get('image') if isinstance(item.get('item'), dict) else None)
    item_url = item.get('url') or (item.get('item', {}).get('url') if isinstance(item.get('item'), dict) else None)
    
    if not name:
        return None
    
    # Clean up the description - remove "Get the X recipe" suffix
    if description:
        description = clean_text(description)
        # Remove common suffixes like "Get the Recipe Name recipe."
        description = re.sub(r'Get the .+ recipe\.?\s*$', '', description, flags=re.IGNORECASE).strip()
    
    # Build full URL if it's a fragment
    source_url = collection_url
    if item_url:
        if item_url.startswith('#') or '#slide-' in item_url:
            source_url = f"{collection_url.split('#')[0]}{item_url if item_url.startswith('#') else '#' + item_url.split('#')[-1]}"
        elif item_url.startswith('http'):
            source_url = item_url
        else:
            source_url = urljoin(collection_url, item_url)
    
    return {
        "title": clean_text(name),
        "description": description,
        "image": image,
        "ingredients": [],  # Not available from ItemList
        "instructions": [],  # Not available from ItemList
        "facts": {
            "collection_page": collection_url,
            "position": item.get('position')
        },
        "source": source_url
    }


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
            page_timeout=25000,
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

    def parse_recipe(self, html_content: str, url: str) -> dict:
        """Parse recipe from HTML with fallback strategies"""
        soup = BeautifulSoup(html_content, "html.parser")

        # Strategy 1: Attempt JSON-LD first (best quality)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Recipe":
                            data = item
                            break
                
                if isinstance(data, dict) and data.get("@type") == "Recipe":
                    instructions = data.get("recipeInstructions", [])
                    if isinstance(instructions, list):
                        instructions = [
                            step.get("text") if isinstance(step, dict) else str(step)
                            for step in instructions
                        ]
                    elif isinstance(instructions, str):
                        instructions = [instructions]

                    ingredients = data.get("recipeIngredient", [])
                    if not isinstance(ingredients, list):
                        ingredients = [str(ingredients)]

                    title = clean_text(data.get("name", "Recipe"))
                    ingredients = [clean_text(ing) for ing in ingredients if ing]
                    ingredients = [ing for ing in ingredients if ing and ing.strip()]
                    instructions = [clean_text(inst) for inst in instructions if inst]
                    instructions = [inst for inst in instructions if inst and inst.strip()]

                    prep_time = parse_iso_duration(data.get("prepTime"))
                    cook_time = parse_iso_duration(data.get("cookTime"))
                    total_time = parse_iso_duration(data.get("totalTime"))

                    return {
                        "title": title,
                        "ingredients": ingredients,
                        "instructions": instructions,
                        "facts": {
                            "prep_time": prep_time,
                            "cook_time": cook_time,
                            "total_time": total_time,
                            "servings": data.get("recipeYield"),
                            "calories": data.get("nutrition", {}).get("calories")
                            if isinstance(data.get("nutrition"), dict) else None
                        },
                        "source": url
                    }
            except (json.JSONDecodeError, AttributeError, KeyError):
                continue

        # Strategy 2: Look for common recipe markup patterns
        title_tag = soup.find("h1") or soup.find("h2", class_=re.compile(r"recipe|title"))
        title = clean_text(title_tag.get_text(strip=True)) if title_tag else "Recipe"

        ingredients = []
        for pattern in ["ingredient", "ingred", "item"]:
            ing_list = soup.find_all("li", class_=re.compile(pattern, re.I))
            if ing_list:
                ingredients = [clean_text(li.get_text(strip=True)) for li in ing_list[:20]]
                ingredients = [ing for ing in ingredients if ing and ing.strip()]
                break

        instructions = []
        for pattern in ["instruction", "step", "direction", "method"]:
            inst_list = soup.find_all("li", class_=re.compile(pattern, re.I))
            if inst_list:
                instructions = [clean_text(li.get_text(strip=True)) for li in inst_list[:20]]
                instructions = [inst for inst in instructions if inst and inst.strip()]
                break

        if not instructions:
            for pattern in ["instruction", "step", "direction", "method", "procedure"]:
                section = soup.find(class_=re.compile(pattern, re.I))
                if section:
                    paragraphs = section.find_all("p")
                    instructions = [clean_text(p.get_text(strip=True)) for p in paragraphs if len(p.get_text(strip=True)) > 20][:15]
                    instructions = [inst for inst in instructions if inst and inst.strip()]
                    if instructions:
                        break

        if ingredients or instructions:
            return {
                "title": title,
                "ingredients": ingredients,
                "instructions": instructions,
                "facts": {},
                "source": url
            }
        
        return None

    async def scrape_recipe_from_url(self, url: str, retries=1) -> dict:
        """Scrape recipe from URL with retry logic"""
        url = normalize_url(url)
        
        for attempt in range(retries):
            try:
                async with AsyncWebCrawler(config=self.browser_config) as crawler:
                    html_content = await self.fetch_page_html(url, crawler)
                    if html_content:
                        recipe = self.parse_recipe(html_content, url)
                        if recipe:
                            return recipe
                        else:
                            print(f"    ⚠️ Could not parse recipe from HTML")
            except Exception as e:
                print(f"    ⚠️ Scraping attempt {attempt + 1} failed: {str(e)[:80]}")
                if attempt < retries - 1:
                    await asyncio.sleep(1)
                    continue
        
        return {
            "title": "Could not fetch recipe",
            "ingredients": [],
            "instructions": [],
            "facts": {},
            "source": url
        }


def extract_recipes_from_itemlist(item_list_data: dict, collection_url: str, max_items: int = 5) -> list:
    """
    Extract recipe data directly from an ItemList JSON-LD structure.
    
    This is used when a collection page has all recipe info embedded in the JSON-LD
    (common on sites like Delish, Food Network, etc.) rather than on separate pages.
    
    Returns: list of recipe dicts
    """
    recipes = []
    items = item_list_data.get('itemListElement', [])
    
    print(f"    → Extracting recipes directly from ItemList ({len(items)} items available)")
    
    for item in items[:max_items]:
        recipe = extract_recipe_from_item_list_entry(item, collection_url)
        if recipe:
            recipes.append(recipe)
            print(f"    ✓ Extracted: {recipe['title'][:50]}")
    
    return recipes


def is_rich_itemlist(item_list_data: dict) -> bool:
    """
    Check if an ItemList contains rich recipe data (name, description, image)
    or just URLs that need to be scraped separately.
    """
    items = item_list_data.get('itemListElement', [])
    if not items:
        return False
    
    # Check first few items
    rich_count = 0
    for item in items[:3]:
        if not isinstance(item, dict):
            continue
        
        # Check if item has name and description
        has_name = bool(item.get('name') or (isinstance(item.get('item'), dict) and item['item'].get('name')))
        has_desc = bool(item.get('description') or (isinstance(item.get('item'), dict) and item['item'].get('description')))
        
        if has_name and has_desc:
            rich_count += 1
    
    # If most items have rich data, treat as rich ItemList
    return rich_count >= 2


def is_fragment_url(url: str, base_url: str) -> bool:
    """Check if a URL is just a fragment reference to the same page"""
    if not url:
        return False
    if url.startswith('#'):
        return True
    if '#slide-' in url or '#item-' in url:
        return True
    # Check if it resolves to the same base page
    full_url = urljoin(base_url, url)
    return full_url.split('#')[0] == base_url.split('#')[0]


def extract_recipe_links_from_collection_page(url: str, max_links: int = 5) -> list:
    """
    Extract individual recipe links from a collection/listicle page.
    
    Returns:
        - List of recipe dicts if ItemList contains rich data (DIRECT_RECIPES marker)
        - List of URL strings for regular collections
        - Empty list if no recipes found
    """
    scraper = WebRecipeScraper()

    try:
        async def _extract_links():
            async with AsyncWebCrawler(config=scraper.browser_config) as crawler:
                html_content = await scraper.fetch_page_html(url, crawler)
                if not html_content:
                    return []

                soup = BeautifulSoup(html_content, "html.parser")
                recipe_links = []

                # Strategy 1: Look for JSON-LD structured data with ItemList
                print(f"    → Strategy 1: Checking for JSON-LD ItemList...")
                json_ld_scripts = soup.find_all('script', type='application/ld+json')

                def find_item_lists(obj, found_lists=None):
                    """Recursively find all ItemList objects in nested JSON-LD structure"""
                    if found_lists is None:
                        found_lists = []
                    
                    if isinstance(obj, dict):
                        if obj.get('@type') == 'ItemList':
                            found_lists.append(obj)
                        for value in obj.values():
                            find_item_lists(value, found_lists)
                    elif isinstance(obj, list):
                        for item in obj:
                            find_item_lists(item, found_lists)
                    
                    return found_lists
                
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        item_lists = find_item_lists(data)
                        
                        for item_list in item_lists:
                            items = item_list.get('itemListElement', [])
                            if not items:
                                continue
                            
                            # Check if this is a rich ItemList with embedded recipe data
                            if is_rich_itemlist(item_list):
                                print(f"    ✓ Found rich ItemList with {len(items)} recipes")
                                # Extract recipes directly from ItemList
                                recipes = extract_recipes_from_itemlist(item_list, url, max_items=max_links)
                                if recipes:
                                    # Return special marker indicating direct recipes (not URLs)
                                    return [('DIRECT_RECIPES', recipes)]
                            
                            # Otherwise, try to extract individual recipe URLs
                            for item in items[:max_links]:
                                if isinstance(item, dict):
                                    item_url = (
                                        item.get('url') or 
                                        (item.get('item', {}).get('url') if isinstance(item.get('item'), dict) else None)
                                    )
                                    item_name = (
                                        item.get('name') or 
                                        (item.get('item', {}).get('name') if isinstance(item.get('item'), dict) else None)
                                    )
                                    
                                    if item_url and not is_fragment_url(item_url, url):
                                        full_url = urljoin(url, item_url)
                                        recipe_links.append(full_url)
                                        display_name = item_name[:30] if item_name else 'Unknown'
                                        print(f"    → Found (JSON-LD): {display_name} → {full_url[:50]}")
                            
                            if recipe_links:
                                print(f"    ✓ Strategy 1 SUCCESS: Extracted {len(recipe_links)} recipe links")
                                return recipe_links
                                
                    except Exception as e:
                        continue

                # Strategy 2: Look for recipe cards with links to individual recipes
                if not recipe_links:
                    print(f"    → Strategy 2: Looking for recipe cards...")
                    recipe_cards = soup.find_all(['article', 'div'], class_=re.compile(r'recipe.*card|card.*recipe', re.I))

                    if not recipe_cards:
                        recipe_cards = soup.find_all(['article', 'div'], class_=re.compile(r'recipe-(?:item|post|tile|block)|post-\d+', re.I))

                    if not recipe_cards:
                        recipe_cards = soup.find_all(['article', 'div'], class_=re.compile(r'recipe|card|post|item', re.I))

                    if recipe_cards:
                        print(f"    → Found {len(recipe_cards)} potential recipe cards")
                        for card in recipe_cards:
                            links = card.find_all('a', href=True)
                            if not links:
                                continue

                            recipe_link = None
                            for link in links:
                                href = link.get('href')
                                if not href:
                                    continue

                                link_text = link.get_text(strip=True)
                                link_text_lower = link_text.lower()

                                # Skip generic links
                                if link_text and link_text[0].isdigit():
                                    continue

                                if any(generic in link_text_lower for generic in ['shop now', 'get started', 'read more',
                                                                            'view all', 'subscribe', 'newsletter',
                                                                            'author', 'by', 'contributor', 'comments',
                                                                            'share', 'print', 'save', 'pin']):
                                    continue

                                if any(skip in href.lower() for skip in ['about', 'contact', 'privacy', 'subscribe',
                                                                         'newsletter', 'tag', 'category', 'shop',
                                                                         '#comments', '/search', '/store', 'youtube.com',
                                                                         # Social media share links - NOT recipe pages!
                                                                         'facebook.com', 'twitter.com', 'pinterest.com',
                                                                         'instagram.com', 'linkedin.com', 'reddit.com',
                                                                         'sharer.php', 'share?', 'intent/tweet',
                                                                         'whatsapp.com', 'telegram.me', 't.me']):
                                    continue

                                # Skip collection URLs
                                if any(cat in href.lower() for cat in ['/collections/', '/collection/', '/roundup/', 
                                                                       '/best-', '/top-', '-recipes/']):
                                    continue

                                full_url = urljoin(url, href)
                                parsed = urlparse(full_url)

                                if parsed.path in ['/', '', '/recipes', '/recipe'] or len(parsed.path) < 15:
                                    continue

                                path_parts = [p for p in parsed.path.split('/') if p]
                                if len(path_parts) < 2:
                                    continue

                                recipe_link = full_url
                                break

                            if recipe_link and recipe_link not in recipe_links and recipe_link != url:
                                recipe_links.append(recipe_link)
                                print(f"    → Candidate: {recipe_link[:70]}")
                                if len(recipe_links) >= max_links:
                                    break

                        if recipe_links:
                            print(f"    ✓ Strategy 2 SUCCESS: Found {len(recipe_links)} recipe links")
                            return recipe_links

                # Strategy 3: Look for links with "recipe" in URL
                if not recipe_links:
                    print(f"    → Strategy 3: Trying link-based extraction with 'recipe' in URL")
                    for link in soup.find_all("a", href=True):
                        href = link.get("href")
                        link_text = link.get_text(strip=True)

                        if 'recipe' not in href.lower():
                            continue

                        if any(skip in href.lower() for skip in ['about', 'contact', 'privacy', 'subscribe', 
                                                                 'newsletter', 'category', 'tag', 'collection',
                                                                 # Social media share links
                                                                 'facebook.com', 'twitter.com', 'pinterest.com',
                                                                 'instagram.com', 'linkedin.com', 'reddit.com',
                                                                 'sharer.php', 'share?', 'intent/tweet',
                                                                 'whatsapp.com', 'telegram.me', 't.me']):
                            continue

                        full_url = urljoin(url, href)
                        parsed = urlparse(full_url)

                        if len(parsed.path) < 20:
                            continue

                        path_parts = [p for p in parsed.path.split('/') if p]

                        if any(part in ['collection', 'collections', 'roundup', 'roundups'] for part in path_parts):
                            continue

                        if any(part.endswith('-recipes') for part in path_parts):
                            continue

                        if full_url not in recipe_links and full_url != url:
                            recipe_links.append(full_url)
                            print(f"    → Found (link-based): {link_text[:40]} → {full_url[:50]}")
                            if len(recipe_links) >= max_links:
                                break

                    if recipe_links:
                        print(f"    ✓ Strategy 3 SUCCESS: Found {len(recipe_links)} recipe links")

                if not recipe_links:
                    print(f"    ✗ All strategies failed - no recipe links found")

                return recipe_links

        return asyncio.run(_extract_links())

    except Exception as e:
        print(f"  ✗ Error extracting links from collection page: {str(e)[:80]}")
        return []


# ----------------------------
# Entry point for MCP fallback
# ----------------------------
def scrape_recipe_via_mcp(url: str) -> dict:
    """
    Synchronous wrapper to call async Crawl4AI scraper.
    Returns structured recipe dict ready for MCP.
    """
    # Safety check - ensure url is a string
    if not isinstance(url, str):
        print(f"    ⚠️ Invalid URL type received: {type(url)} - attempting to extract URL")
        if isinstance(url, tuple):
            for item in url:
                if isinstance(item, str) and (item.startswith('http') or item.startswith('//')):
                    url = item
                    break
            else:
                return {
                    "title": "Could not fetch recipe",
                    "ingredients": [],
                    "instructions": [],
                    "facts": {},
                    "source": str(url)
                }
        else:
            url = str(url)
    
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


def scrape_recipes_from_collection(url: str, max_recipes: int = 5) -> dict:
    """
    Scrape multiple recipes from a collection page.
    Handles both:
    1. Rich ItemList collections (data embedded in JSON-LD)
    2. Multi-page collections (separate URLs for each recipe)
    
    Returns dict with:
        'recipes': list of recipe dicts
        'collection_url': URL of the collection page
        'type': 'rich-itemlist', 'multi-page', or 'unknown'
    """
    print(f"\n🔍 Analyzing collection page...")
    
    result = extract_recipe_links_from_collection_page(url, max_links=max_recipes)
    
    if not result:
        print(f"    ⚠️ No recipes found in collection")
        return {'recipes': [], 'collection_url': url, 'type': 'unknown'}
    
    # Check if we got direct recipes from a rich ItemList
    if (isinstance(result, list) and 
        len(result) == 1 and 
        isinstance(result[0], tuple) and 
        result[0][0] == 'DIRECT_RECIPES'):
        
        recipes = result[0][1]
        print(f"    ✓ Extracted {len(recipes)} recipes directly from ItemList")
        return {
            'recipes': recipes,
            'collection_url': url,
            'type': 'rich-itemlist'
        }
    
    # Regular multi-page collection - scrape each recipe URL
    # Filter out any non-string items (tuples, etc.) to prevent errors
    recipe_links = [r for r in result if isinstance(r, str)]
    
    if len(recipe_links) != len(result):
        print(f"    ⚠️ Filtered out {len(result) - len(recipe_links)} non-URL items")
    
    if not recipe_links:
        print(f"    ⚠️ No valid recipe URLs found after filtering")
        return {'recipes': [], 'collection_url': url, 'type': 'multi-page'}
    
    print(f"    ✓ Found {len(recipe_links)} recipe links to scrape")
    recipe_links = recipe_links[:max_recipes]
    
    recipes = []
    for i, recipe_url in enumerate(recipe_links, 1):
        print(f"\n→ Scraping recipe {i}/{len(recipe_links)}: {recipe_url[:60]}...")
        recipe = scrape_recipe_via_mcp(recipe_url)
        if recipe and recipe.get('title') != "Could not fetch recipe":
            recipes.append(recipe)
    
    return {
        'recipes': recipes,
        'collection_url': url,
        'type': 'multi-page'
    }