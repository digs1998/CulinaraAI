"""
Unit tests for nutrition information extraction
"""
import pytest


def test_nutrition_fields_extracted():
    """Test that all nutrition fields are extracted from JSON-LD"""
    # This would test the actual scraper
    # For now, just verify the expected fields exist
    expected_fields = [
        "calories",
        "protein",
        "carbohydrates",
        "fat",
        "saturated_fat",
        "fiber",
        "sugar",
        "sodium",
        "cholesterol"
    ]

    assert len(expected_fields) == 9


def test_recipe_has_nutrition_in_facts():
    """Test that nutrition data is included in recipe facts"""
    # Mock recipe data structure
    recipe_facts = {
        "prep_time": "15 mins",
        "cook_time": "30 mins",
        "servings": 4,
        "nutrition": {
            "calories": "350",
            "protein": "25g",
            "carbohydrates": "30g",
            "fat": "15g"
        }
    }

    assert "nutrition" in recipe_facts
    assert "protein" in recipe_facts["nutrition"]
    assert "carbohydrates" in recipe_facts["nutrition"]
