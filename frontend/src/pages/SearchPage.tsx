import { RecipeResults } from "../components/recipesResults";

export default function SearchPage() {
  const recipes = [
    {
      title: "Quick Greek Spinach and Chicken Orzo",
      ingredients: ["chicken", "spinach", "orzo"],
      instructions: ["Cook chicken", "Add spinach", "Mix with orzo"],
      facts: {
        prep_time: "10 min",
        cook_time: "20 min",
        total_time: "30 min",
        servings: "4",
      },
      source: "example.com",
      score: 95.0
    }
  ];

  return (
    <div className="max-w-4xl mx-auto p-6">
      <RecipeResults recipes={recipes} />
    </div>
  );
}
