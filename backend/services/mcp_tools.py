"""
MCP (Model Context Protocol) Tools for Internet Recipe Search
Provides tools that LLM can call to fetch recipes from the internet
"""

import os
import requests
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import json
from urllib.parse import quote_plus
import time


class MCPRecipeTools:
    """Tools for searching and fetching recipes from the internet"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_recipe_web(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """
        Search for recipes on the web using DuckDuckGo or similar
        
        Args:
            query: Recipe search query (e.g., "butter paneer masala recipe")
            max_results: Maximum number of recipe sources to return
            
        Returns:
            Dictionary with search results containing titles, URLs, and snippets
        """
        try:
            # Use DuckDuckGo Instant Answer API or web search
            search_query = f"{query} recipe"
            encoded_query = quote_plus(search_query)
            
            # Try DuckDuckGo HTML search (doesn't require API key)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Parse DuckDuckGo results
            result_divs = soup.find_all('div', class_='result', limit=max_results)
            
            for div in result_divs:
                title_elem = div.find('a', class_='result__a')
                snippet_elem = div.find('a', class_='result__snippet')
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    # Filter for recipe sites
                    recipe_sites = ['allrecipes', 'food.com', 'tasty', 'british', 'bbc', 
                                  'seriouseats', 'bonappetit', 'foodnetwork', 'tasteofhome',
                                  'recipe', 'cooking', 'chef', 'cuisine']
                    
                    if any(site in url.lower() for site in recipe_sites) or 'recipe' in url.lower():
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet
                        })
            
            # Fallback: if no results, try a simpler approach with common recipe sites
            if not results:
                results = self._fallback_recipe_search(query, max_results)
            
            return {
                "success": True,
                "query": query,
                "results": results[:max_results],
                "count": len(results)
            }
            
        except Exception as e:
            print(f"Error searching web for recipes: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "count": 0
            }
    
    def _fallback_recipe_search(self, query: str, max_results: int) -> List[Dict]:
        """Fallback search using common recipe site URLs"""
        recipe_sites = [
            {
                "title": f"{query} Recipe - AllRecipes",
                "url": f"https://www.allrecipes.com/search/results/?search={quote_plus(query)}",
                "snippet": f"Find {query} recipes on AllRecipes"
            },
            {
                "title": f"{query} Recipe - Food.com",
                "url": f"https://www.food.com/search/{quote_plus(query)}",
                "snippet": f"Find {query} recipes on Food.com"
            }
        ]
        return recipe_sites[:max_results]
    
    def fetch_recipe_from_url(self, url: str) -> Dict[str, Any]:
        """
        Fetch and parse recipe details from a URL
        
        Args:
            url: URL to fetch recipe from
            
        Returns:
            Dictionary with parsed recipe information
        """
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to extract recipe information using common schema.org patterns
            recipe_data = {}
            
            # Look for JSON-LD structured data
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'Recipe':
                        recipe_data.update(self._parse_structured_recipe(data))
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == 'Recipe':
                                recipe_data.update(self._parse_structured_recipe(item))
                                break
                except:
                    continue
            
            # Fallback: try to extract basic info from HTML
            if not recipe_data:
                recipe_data = self._parse_html_recipe(soup, url)
            
            recipe_data['url'] = url
            recipe_data['success'] = True
            
            return recipe_data
            
        except Exception as e:
            print(f"Error fetching recipe from URL {url}: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    def _parse_structured_recipe(self, data: Dict) -> Dict:
        """Parse structured recipe data from JSON-LD"""
        recipe = {
            "title": data.get("name", ""),
            "description": data.get("description", ""),
            "ingredients": data.get("recipeIngredient", []),
            "instructions": [],
            "prepTime": data.get("prepTime", ""),
            "cookTime": data.get("cookTime", ""),
            "totalTime": data.get("totalTime", ""),
            "servings": data.get("recipeYield", ""),
            "rating": None,
        }
        
        # Parse instructions
        instructions = data.get("recipeInstructions", [])
        if isinstance(instructions, list):
            for step in instructions:
                if isinstance(step, dict):
                    recipe["instructions"].append(step.get("text", ""))
                elif isinstance(step, str):
                    recipe["instructions"].append(step)
        
        # Parse rating
        if "aggregateRating" in data:
            rating_data = data["aggregateRating"]
            if isinstance(rating_data, dict):
                recipe["rating"] = rating_data.get("ratingValue")
        
        return recipe
    
    def _parse_html_recipe(self, soup: BeautifulSoup, url: str) -> Dict:
        """Fallback HTML parsing for recipe information"""
        recipe = {
            "title": "",
            "description": "",
            "ingredients": [],
            "instructions": [],
            "url": url
        }
        
        # Try to find title
        title_selectors = ['h1', '.recipe-title', '[itemprop="name"]']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                recipe["title"] = title_elem.get_text(strip=True)
                break
        
        # Try to find ingredients
        ingredient_selectors = [
            '[itemprop="recipeIngredient"]',
            '.ingredient',
            '.recipe-ingredients li',
            'ul.ingredients li'
        ]
        for selector in ingredient_selectors:
            ingredients = soup.select(selector)
            if ingredients:
                recipe["ingredients"] = [ing.get_text(strip=True) for ing in ingredients[:20]]
                break
        
        # Try to find instructions
        instruction_selectors = [
            '[itemprop="recipeInstructions"]',
            '.instruction',
            '.recipe-steps li',
            'ol.instructions li'
        ]
        for selector in instruction_selectors:
            instructions = soup.select(selector)
            if instructions:
                recipe["instructions"] = [inst.get_text(strip=True) for inst in instructions]
                break
        
        return recipe
    
    def get_tool_definitions(self) -> List[Dict]:
        """
        Get MCP tool definitions for Gemini function calling
        
        Returns:
            List of tool definitions in Gemini format
        """
        return [
            {
                "function_declarations": [
                    {
                        "name": "search_recipe_web",
                        "description": "Search the internet for recipe websites and sources when a recipe is not found in the local database. Use this to find recipes from popular cooking websites.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Recipe search query (e.g., 'butter paneer masala recipe')"
                                },
                                "max_results": {
                                    "type": "integer",
                                    "description": "Maximum number of recipe sources to return (default: 3)",
                                    "default": 3
                                }
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "fetch_recipe_from_url",
                        "description": "Fetch detailed recipe information from a specific recipe URL. Use this to get full recipe details including ingredients and instructions.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "URL of the recipe page to fetch"
                                }
                            },
                            "required": ["url"]
                        }
                    }
                ]
            }
        ]


# Singleton instance
_mcp_tools = None

def get_mcp_tools() -> MCPRecipeTools:
    """Get singleton instance of MCP tools"""
    global _mcp_tools
    if _mcp_tools is None:
        _mcp_tools = MCPRecipeTools()
    return _mcp_tools

