"""
Unit tests for dietary compatibility logic
"""
import pytest
from services.mcp_orchestrator import MCPOrchestrator


class TestDietaryCompatibility:
    """Test dietary compatibility filtering"""

    def test_non_veg_requires_meat(self):
        """Non-vegetarian preference should require meat in recipe"""
        orchestrator = MCPOrchestrator(rag_engine=None, mcp_tools=None)

        # Recipe with meat - should pass
        assert orchestrator._check_dietary_compatibility(
            title="Grilled Chicken",
            ingredients="chicken breast, salt, pepper",
            diet_preferences=["Non-Vegetarian"]
        ) is True

        # Recipe without meat - should fail
        assert orchestrator._check_dietary_compatibility(
            title="Caesar Salad",
            ingredients="lettuce, croutons, parmesan",
            diet_preferences=["Non-Vegetarian"]
        ) is False

    def test_non_veg_low_carb_allows_meat_with_carbs(self):
        """Non-Vegetarian + Low Carb should allow meat dishes with moderate carbs"""
        orchestrator = MCPOrchestrator(rag_engine=None, mcp_tools=None)

        # Chicken with rice - should PASS (meat dish with moderate carbs)
        assert orchestrator._check_dietary_compatibility(
            title="Chicken Fried Rice",
            ingredients="chicken, rice, soy sauce, vegetables",
            diet_preferences=["Non-Vegetarian", "Low Carb"]
        ) is True

        # Grilled steak with potatoes - should PASS
        assert orchestrator._check_dietary_compatibility(
            title="Grilled Steak with Roasted Potatoes",
            ingredients="steak, potatoes, garlic, butter",
            diet_preferences=["Non-Vegetarian", "Low Carb"]
        ) is True

    def test_non_veg_low_carb_rejects_high_carb_without_meat(self):
        """Non-Vegetarian + Low Carb should reject very high-carb dishes without meat"""
        orchestrator = MCPOrchestrator(rag_engine=None, mcp_tools=None)

        # Pasta primavera (high carb, no meat) - should FAIL
        assert orchestrator._check_dietary_compatibility(
            title="Pasta Primavera",
            ingredients="pasta, tomatoes, basil, olive oil",
            diet_preferences=["Non-Vegetarian", "Low Carb"]
        ) is False

        # Bread pudding (very high carb, no meat) - should FAIL
        assert orchestrator._check_dietary_compatibility(
            title="Bread Pudding",
            ingredients="bread, milk, sugar, eggs",
            diet_preferences=["Non-Vegetarian", "Low Carb"]
        ) is False

    def test_vegetarian_rejects_meat(self):
        """Vegetarian preference should reject meat"""
        orchestrator = MCPOrchestrator(rag_engine=None, mcp_tools=None)

        # Recipe with chicken - should fail
        assert orchestrator._check_dietary_compatibility(
            title="Chicken Tikka",
            ingredients="chicken, yogurt, spices",
            diet_preferences=["Vegetarian"]
        ) is False

        # Recipe without meat - should pass
        assert orchestrator._check_dietary_compatibility(
            title="Vegetable Curry",
            ingredients="potatoes, peas, tomatoes, spices",
            diet_preferences=["Vegetarian"]
        ) is True

    def test_low_carb_only_strict_filtering(self):
        """Low Carb alone (without Non-Veg) should be strict"""
        orchestrator = MCPOrchestrator(rag_engine=None, mcp_tools=None)

        # Recipe with rice - should FAIL
        assert orchestrator._check_dietary_compatibility(
            title="Vegetable Fried Rice",
            ingredients="rice, vegetables, soy sauce",
            diet_preferences=["Low Carb"]
        ) is False

        # Keto-friendly recipe - should PASS
        assert orchestrator._check_dietary_compatibility(
            title="Cauliflower Rice Stir Fry",
            ingredients="cauliflower, vegetables, soy sauce",
            diet_preferences=["Low Carb"]
        ) is True

    def test_gluten_free(self):
        """Gluten-free preference should reject wheat/gluten"""
        orchestrator = MCPOrchestrator(rag_engine=None, mcp_tools=None)

        # Recipe with pasta - should fail
        assert orchestrator._check_dietary_compatibility(
            title="Spaghetti Carbonara",
            ingredients="pasta, bacon, eggs, parmesan",
            diet_preferences=["Gluten Free"]
        ) is False

        # Recipe without gluten - should pass
        assert orchestrator._check_dietary_compatibility(
            title="Grilled Salmon",
            ingredients="salmon, lemon, herbs, olive oil",
            diet_preferences=["Gluten Free"]
        ) is True

    def test_multiple_diets(self):
        """Test combination of multiple dietary restrictions"""
        orchestrator = MCPOrchestrator(rag_engine=None, mcp_tools=None)

        # Gluten-free + Dairy-free chicken - should pass
        assert orchestrator._check_dietary_compatibility(
            title="Grilled Chicken Breast",
            ingredients="chicken, olive oil, herbs, salt",
            diet_preferences=["Non-Vegetarian", "Gluten Free", "Dairy Free"]
        ) is True

        # Has dairy - should fail
        assert orchestrator._check_dietary_compatibility(
            title="Chicken Alfredo",
            ingredients="chicken, pasta, cream, parmesan",
            diet_preferences=["Non-Vegetarian", "Gluten Free", "Dairy Free"]
        ) is False
