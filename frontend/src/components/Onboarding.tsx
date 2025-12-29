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

  const dietOptions = ["Vegan", "Vegetarian", "Non-Vegetarian", "Keto", "Paleo", "Gluten Free", "Dairy Free", "Low Carb", "Others"];
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
    <>
      <style>{`
        * {
          box-sizing: border-box;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }

        .onboarding-container {
          min-height: 100vh;
          background: linear-gradient(135deg, #1a1a1a 0%, #2d5016 50%, #1a1a1a 100%);
          background-size: cover;
          background-position: center;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 16px;
          overflow-y: auto;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
        }

        .onboarding-card {
          background: rgba(0,0,0,0.55);
          backdrop-filter: blur(12px);
          border-radius: 24px;
          padding: 28px 20px;
          max-width: 600px;
          width: 100%;
          color: white;
          text-align: center;
          margin: auto;
        }

        .onboarding-title {
          font-size: 28px;
          margin-bottom: 8px;
          margin-top: 0;
          line-height: 1.2;
        }

        .onboarding-subtitle {
          opacity: 0.9;
          margin-bottom: 28px;
          font-size: 14px;
          line-height: 1.4;
        }

        .section {
          margin-bottom: 24px;
        }

        .section-title {
          color: #bbf7d0;
          font-size: 14px;
          margin-bottom: 12px;
          letter-spacing: 0.5px;
          margin-top: 0;
          line-height: 1.3;
        }

        .diet-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 10px;
          margin-top: 12px;
        }

        .diet-button {
          padding: 12px 8px;
          border-radius: 14px;
          border: none;
          font-weight: 600;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          justify-content: center;
          line-height: 1.2;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }

        .diet-button:active {
          transform: scale(0.95);
        }

        .skill-servings-container {
          display: flex;
          flex-direction: column;
          gap: 20px;
          margin-bottom: 24px;
        }

        .skill-container, .servings-container {
          width: 100%;
        }

        .skill-buttons {
          display: flex;
          gap: 8px;
          margin-top: 12px;
          justify-content: center;
          flex-wrap: wrap;
        }

        .skill-button {
          padding: 10px 16px;
          border-radius: 14px;
          border: none;
          cursor: pointer;
          font-size: 13px;
          font-weight: 600;
          transition: all 0.2s;
          flex: 1;
          min-width: 90px;
          display: flex;
          align-items: center;
          justify-content: center;
          line-height: 1.2;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }

        .skill-button:active {
          transform: scale(0.95);
        }

        .servings-controls {
          margin-top: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 16px;
        }

        .servings-button {
          padding: 10px 16px;
          background: rgba(255,255,255,0.15);
          border: none;
          border-radius: 12px;
          color: white;
          font-size: 18px;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.2s;
          min-width: 44px;
          display: flex;
          align-items: center;
          justify-content: center;
          line-height: 1;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
        }

        .servings-button:active {
          transform: scale(0.9);
        }

        .servings-display {
          padding: 8px 20px;
          font-size: 20px;
          font-weight: 600;
          min-width: 50px;
        }

        .goal-buttons {
          margin-top: 12px;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .goal-button {
          padding: 14px 24px;
          border-radius: 16px;
          border: none;
          font-weight: 600;
          cursor: pointer;
          font-size: 15px;
          transition: all 0.2s;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          line-height: 1.2;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }

        .goal-button:active {
          transform: scale(0.97);
        }

        .discover-button {
          background: #22c55e;
          color: white;
          padding: 16px 48px;
          border-radius: 50px;
          border: none;
          font-size: 18px;
          font-weight: 600;
          cursor: pointer;
          margin-top: 8px;
          width: 100%;
          max-width: 320px;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          justify-content: center;
          line-height: 1;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }

        .discover-button:active {
          transform: scale(0.97);
        }

        .action-buttons {
          display: flex;
          flex-direction: column;
          gap: 12px;
          align-items: center;
          margin-top: 8px;
        }

        .skip-button {
          background: transparent;
          color: rgba(255, 255, 255, 0.7);
          padding: 12px 32px;
          border-radius: 50px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          justify-content: center;
          line-height: 1;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }

        .skip-button:hover {
          background: rgba(255, 255, 255, 0.1);
          color: white;
        }

        .skip-button:active {
          transform: scale(0.97);
        }

        /* Tablet and up */
        @media (min-width: 640px) {
          .onboarding-card {
            padding: 36px 40px;
            border-radius: 30px;
          }

          .onboarding-title {
            font-size: 36px;
          }

          .onboarding-subtitle {
            font-size: 16px;
            margin-bottom: 36px;
          }

          .section {
            margin-bottom: 28px;
          }

          .section-title {
            font-size: 15px;
          }

          .diet-grid {
            grid-template-columns: repeat(3, 1fr);
          }

          .diet-button {
            padding: 14px 12px;
            font-size: 15px;
          }

          .skill-servings-container {
            flex-direction: row;
            justify-content: center;
          }

          .skill-container, .servings-container {
            width: auto;
          }

          .skill-button {
            padding: 12px 20px;
            font-size: 14px;
            flex: 0;
          }

          .goal-buttons {
            flex-direction: row;
            flex-wrap: wrap;
            justify-content: center;
          }

          .goal-button {
            width: auto;
            padding: 16px 32px;
            font-size: 16px;
          }

          .discover-button {
            width: auto;
            padding: 18px 60px;
            font-size: 20px;
          }

          .action-buttons {
            flex-direction: row;
            gap: 16px;
          }

          .skip-button {
            font-size: 16px;
            padding: 14px 40px;
          }
        }

        /* Desktop */
        @media (min-width: 768px) {
          .onboarding-container {
            padding: 20px;
          }

          .onboarding-card {
            padding: 40px 50px;
          }

          .section {
            margin-bottom: 30px;
          }

          .section-title {
            font-size: 16px;
          }
        }
      `}</style>

      <div className="onboarding-container">
        <div className="onboarding-card">
          <h1 className="onboarding-title">CulinaraAI</h1>
          <p className="onboarding-subtitle">
            Personalize your healthy culinary journey.
          </p>

          {/* Dietary Path */}
          <div className="section">
            <h3 className="section-title">DIETARY PATH</h3>
            <div className="diet-grid">
              {dietOptions.map(diet => (
                <button
                  key={diet}
                  onClick={() => toggleDiet(diet)}
                  className="diet-button"
                  style={{
                    background: diets.includes(diet) ? "#22c55e" : "rgba(255,255,255,0.15)",
                    color: "white",
                  }}
                >
                  {diet}
                </button>
              ))}
            </div>
          </div>

          {/* Skill & Servings */}
          <div className="skill-servings-container">
            <div className="skill-container">
              <h3 className="section-title">SKILL LEVEL</h3>
              <div className="skill-buttons">
                {skillOptions.map(s => (
                  <button
                    key={s}
                    onClick={() => setSkill(s)}
                    className="skill-button"
                    style={{
                      background: skill === s ? "#22c55e" : "rgba(255,255,255,0.15)",
                      color: "white",
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            <div className="servings-container">
              <h3 className="section-title">SERVINGS</h3>
              <div className="servings-controls">
                <button
                  onClick={() => setServings(Math.max(1, servings - 1))}
                  className="servings-button"
                >
                  -
                </button>
                <span className="servings-display">{servings}</span>
                <button
                  onClick={() => setServings(servings + 1)}
                  className="servings-button"
                >
                  +
                </button>
              </div>
            </div>
          </div>

          {/* Health Goal */}
          <div className="section">
            <h3 className="section-title">YOUR HEALTH GOAL</h3>
            <div className="goal-buttons">
              {goalOptions.map(g => (
                <button
                  key={g}
                  onClick={() => setGoal(g)}
                  className="goal-button"
                  style={{
                    background: goal === g ? "#22c55e" : "rgba(255,255,255,0.15)",
                    color: "white",
                  }}
                >
                  {g}
                </button>
              ))}
            </div>
          </div>

          <div className="action-buttons">
            <button
              onClick={() => onComplete({ diets, skill, servings, goal })}
              className="discover-button"
            >
              Discover Recipes
            </button>
            <button
              onClick={() => onComplete({ diets: [], skill: "", servings: 2, goal: "" })}
              className="skip-button"
            >
              Skip for now
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
