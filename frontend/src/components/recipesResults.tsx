import React from "react";

type Recipe = {
  id: string;
  title: string;
  category?: string;
  total_time?: string;
  rating?: number;
  score: number;
  url?: string;
};

type Props = {
  recipes: Recipe[];
};

export const RecipeResults: React.FC<Props> = ({ recipes }) => {
  return (
    <div style={{ marginTop: "16px" }}>
      {recipes.map((recipe, index) => (
        <div
          key={recipe.id}
          style={{
            backgroundColor: index === 0 ? "#e5e7eb" : "#f3f4f6",
            borderRadius: "12px",
            padding: "16px",
            marginBottom: "12px",
            border: "1px solid #e5e7eb",
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          <div>
            <h3 style={{ fontWeight: 600, margin: "0 0 6px 0" }}>
              {recipe.title}
            </h3>

            <div style={{ display: "flex", gap: "12px", fontSize: "14px", color: "#6b7280" }}>
              {recipe.category && <span>🏷 {recipe.category}</span>}
              {recipe.total_time && <span>⏱ {recipe.total_time}</span>}
              {recipe.rating && <span>⭐ {recipe.rating}/5</span>}
            </div>
          </div>

          <span
            style={{
              alignSelf: "center",
              fontSize: "12px",
              backgroundColor: "#fed7aa",
              color: "#c2410c",
              padding: "6px 10px",
              borderRadius: "999px",
              whiteSpace: "nowrap",
            }}
          >
            {(recipe.score * 100).toFixed(0)}% match
          </span>
        </div>
      ))}
    </div>
  );
};
