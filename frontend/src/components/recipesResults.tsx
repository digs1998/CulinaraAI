import React from "react";

interface Recipe {
  title: string;
  ingredients: string[];
  instructions: string[];
  facts: {
    prep_time?: string;
    cook_time?: string;
    total_time?: string;
    servings?: string;
    calories?: string;
  };
  source: string;
  score: number;
}

interface RecipeResultsProps {
  recipes: Recipe[];
}

export const RecipeResults: React.FC<RecipeResultsProps> = ({ recipes }) => {
  const topRecipes = recipes.slice(0, 3);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "20px",
        width: "100%",
      }}
    >
      {topRecipes.map((recipe, index) => (
        <a
          key={index}
          href={recipe.source}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            textDecoration: "none",
            color: "inherit",
          }}
        >
          <div
            style={{
              borderRadius: "20px",
              overflow: "hidden",
              background: `
                linear-gradient(
                  180deg,
                  rgba(0,0,0,0.35),
                  rgba(0,0,0,0.05)
                ),
                url("/images/italian-dish.jpg")
              `,
              backgroundSize: "cover",
              backgroundPosition: "center",
              boxShadow: "0 10px 28px rgba(0,0,0,0.15)",
              transition: "all 0.3s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-4px)";
              e.currentTarget.style.boxShadow =
                "0 16px 36px rgba(34,197,94,0.35)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.boxShadow =
                "0 10px 28px rgba(0,0,0,0.15)";
            }}
          >
            {/* Image Header */}
            <div
              style={{
                padding: "20px",
                color: "white",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: "12px",
                flexWrap: "wrap",
              }}
            >
              <h3
                style={{
                  margin: 0,
                  fontSize: "20px",
                  fontWeight: 700,
                  lineHeight: 1.3,
                }}
              >
                {recipe.title}
              </h3>

              <span
                style={{
                  backgroundColor: "rgba(255,237,213,0.95)",
                  color: "#9a3412",
                  padding: "8px 14px",
                  borderRadius: "999px",
                  fontSize: "13px",
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                }}
              >
                {recipe.score.toFixed(1)}% match
              </span>
            </div>

            {/* Content Body */}
            <div
              style={{
                background: "rgba(255,255,255,0.97)",
                padding: "18px 20px 20px",
              }}
            >
              {/* Recipe Facts */}
              {recipe.facts && Object.keys(recipe.facts).length > 0 && (
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(auto-fit, minmax(140px, 1fr))",
                    gap: "12px",
                    marginBottom: "14px",
                    padding: "14px",
                    backgroundColor: "#f0fdf4",
                    borderRadius: "12px",
                    border: "1px solid #bbf7d0",
                  }}
                >
                  {recipe.facts.prep_time && (
                    <Fact icon="⏱️" label="Prep" value={recipe.facts.prep_time} />
                  )}
                  {recipe.facts.cook_time && (
                    <Fact icon="🔥" label="Cook" value={recipe.facts.cook_time} />
                  )}
                  {recipe.facts.total_time && (
                    <Fact icon="⏰" label="Total" value={recipe.facts.total_time} />
                  )}
                  {recipe.facts.servings && (
                    <Fact icon="🍽️" label="Serves" value={recipe.facts.servings} />
                  )}
                  {recipe.facts.calories && (
                    <Fact icon="⚡" label="Energy" value={recipe.facts.calories} />
                  )}
                </div>
              )}

              {/* CTA */}
              <div
                style={{
                  fontSize: "14px",
                  color: "#22c55e",
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                🔗 View full recipe & ingredients
              </div>
            </div>
          </div>
        </a>
      ))}
    </div>
  );
};

/* Small helper component for clarity */
const Fact = ({
  icon,
  label,
  value,
}: {
  icon: string;
  label: string;
  value: string;
}) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: "8px",
      fontSize: "13px",
      color: "#166534",
    }}
  >
    <span style={{ fontSize: "16px" }}>{icon}</span>
    <div style={{ display: "flex", flexDirection: "column" }}>
      <span style={{ fontSize: "11px", opacity: 0.7 }}>{label}</span>
      <span style={{ fontWeight: 500 }}>{value}</span>
    </div>
  </div>
);
