// components/Onboarding.tsx
import React, { useState } from "react";

interface OnboardingProps {
  onComplete: (preferences: {
    diets: string[];
    skill: string;
    servings: number;
    goal: string;
  }) => void;
}

export const Onboarding: React.FC<OnboardingProps> = ({ onComplete }) => {
  const [diets, setDiets] = useState<string[]>([]);
  const [skill, setSkill] = useState<string>("Intermediate");
  const [servings, setServings] = useState(2);
  const [goal, setGoal] = useState<string>("Balanced");

  const dietOptions = ["Vegan", "Vegetarian", "Keto", "Paleo", "Gluten Free", "Dairy Free", "Low Carb", "Others"];
  const skillOptions = ["Beginner", "Intermediate", "Advanced"];
  const goalOptions = ["Balanced", "Weight Loss", "Muscle Gain", "Energy Boost"];

  const toggleDiet = (diet: string) => {
    setDiets(prev => 
      prev.includes(diet) 
        ? prev.filter(d => d !== diet) 
        : [...prev, diet]
    );
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #1a1a1a 0%, #2d5016 50%, #1a1a1a 100%)",
        backgroundSize: "cover",
        backgroundPosition: "center",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
    >
      <div
        style={{
          background: "rgba(0,0,0,0.55)",
          backdropFilter: "blur(12px)",
          borderRadius: "30px",
          padding: "40px 50px",
          maxWidth: "600px",
          width: "100%",
          color: "white",
          textAlign: "center",
        }}
      >
        <h1 style={{ fontSize: "36px", marginBottom: "8px" }}>CulinaraAI</h1>
        <p style={{ opacity: 0.9, marginBottom: "40px" }}>
          Personalize your healthy culinary journey.
        </p>

        {/* Dietary Path */}
        <div style={{ marginBottom: "30px" }}>
          <h3 style={{ color: "#bbf7d0" }}>DIETARY PATH</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "12px", marginTop: "12px" }}>
            {dietOptions.map(diet => (
              <button
                key={diet}
                onClick={() => toggleDiet(diet)}
                style={{
                  padding: "14px",
                  borderRadius: "16px",
                  border: "none",
                  background: diets.includes(diet) ? "#22c55e" : "rgba(255,255,255,0.15)",
                  color: "white",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {diet}
              </button>
            ))}
          </div>
        </div>

        {/* Skill & Servings */}
        <div style={{ display: "flex", gap: "20px", marginBottom: "30px", justifyContent: "center" }}>
          <div>
            <h3 style={{ color: "#bbf7d0" }}>SKILL LEVEL</h3>
            <div style={{ display: "flex", gap: "12px", marginTop: "12px" }}>
              {skillOptions.map(s => (
                <button
                  key={s}
                  onClick={() => setSkill(s)}
                  style={{
                    padding: "12px 20px",
                    borderRadius: "16px",
                    border: "none",
                    background: skill === s ? "#22c55e" : "rgba(255,255,255,0.15)",
                    color: "white",
                    cursor: "pointer",
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div>
            <h3 style={{ color: "#bbf7d0" }}>SERVINGS</h3>
            <div style={{ marginTop: "12px" }}>
              <button
                onClick={() => setServings(Math.max(1, servings - 1))}
                style={{ padding: "12px 16px", background: "rgba(255,255,255,0.15)", border: "none", borderRadius: "12px", color: "white" }}
              >
                -
              </button>
              <span style={{ padding: "12px 24px", fontSize: "20px", fontWeight: 600 }}>{servings}</span>
              <button
                onClick={() => setServings(servings + 1)}
                style={{ padding: "12px 16px", background: "rgba(255,255,255,0.15)", border: "none", borderRadius: "12px", color: "white" }}
              >
                +
              </button>
            </div>
          </div>
        </div>

        {/* Health Goal */}
        <div style={{ marginBottom: "40px" }}>
          <h3 style={{ color: "#bbf7d0" }}>YOUR HEALTH GOAL</h3>
          <div style={{ marginTop: "12px" }}>
            {goalOptions.map(g => (
              <button
                key={g}
                onClick={() => setGoal(g)}
                style={{
                  padding: "16px 32px",
                  borderRadius: "20px",
                  border: "none",
                  background: goal === g ? "#22c55e" : "rgba(255,255,255,0.15)",
                  color: "white",
                  fontWeight: 600,
                  margin: "6px",
                  cursor: "pointer",
                }}
              >
                {g}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() => onComplete({ diets, skill, servings, goal })}
          style={{
            background: "#22c55e",
            color: "white",
            padding: "18px 60px",
            borderRadius: "50px",
            border: "none",
            fontSize: "20px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Discover Recipes
        </button>
      </div>
    </div>
  );
};