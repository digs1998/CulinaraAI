import { RecipeResults } from "../components/recipesResults";

export default function SearchPage() {
  const recipes = [
    {
      id: "1",
      title: "Quick Greek Spinach and Chicken Orzo",
      category: "One Dish Meal",
      cook_time_minutes: 30,
      rating: 5,
      match_percentage: 68
    }
  ];

  return (
    <div className="max-w-4xl mx-auto p-6">
      <RecipeResults recipes={recipes} />
    </div>
  );
}
