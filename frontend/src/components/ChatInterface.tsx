import React, { useState, useRef, useEffect } from "react";
import { CulinaraAIAPI } from "../services/api";
import { ChatMessage } from "../types";
import { RecipeResults } from "../components/recipesResults.tsx";
import { usePreferences } from "../contexts/PreferencesContext";

// Helper function to get food category background image
const getFoodBackgroundImage = (query: string): string => {
  const queryLower = query.toLowerCase();

  const foodImages: Record<string, string> = {
    pasta: "https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=1600",
    salad: "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=1600",
    chicken: "https://images.unsplash.com/photo-1598103442097-8b74394b95c6?w=1600",
    tofu: "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=1600",
    vegan: "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=1600",
    dessert: "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=1600",
    pizza: "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=1600",
    burger: "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=1600",
    soup: "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=1600",
    seafood: "https://images.unsplash.com/photo-1559737558-2f5a555e8160?w=1600",
  };

  // Find matching category
  for (const [key, imageUrl] of Object.entries(foodImages)) {
    if (queryLower.includes(key)) {
      return imageUrl;
    }
  }

  // Default food background
  return "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1600";
};

interface ChatInterfaceProps {
  onBackToPreferences?: () => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ onBackToPreferences }) => {
  const { preferences, clearPreferences } = usePreferences();
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showWelcome, setShowWelcome] = useState(true);
  const [welcomeBackgroundImage, setWelcomeBackgroundImage] = useState(
    getFoodBackgroundImage("")
  );
  const hasAutoQueried = useRef(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSend = async (messageOverride?: string) => {
    const userMessage = messageOverride || input.trim();
    if (!userMessage || isLoading) return;

    if (!messageOverride) {
      setInput("");
    }
    setShowWelcome(false);

    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await CulinaraAIAPI.sendMessage({
        message: userMessage,
        preferences: preferences || undefined
      });

      console.log("📊 Backend response:", response);
      console.log("💡 Facts received:", response.facts);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.response,
          recipes: response.recipes,
          facts: response.facts, // 👈 LLM-generated facts
        },
      ]);
    } catch (err) {
      console.error("API Error:", err);
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            `⚠️ Failed to connect to the backend. ${errorMessage}. Please check your connection and try again.`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Auto-query based on preferences when component mounts
  useEffect(() => {
    if (preferences && !hasAutoQueried.current) {
      hasAutoQueried.current = true;

      // Skip auto-query if user skipped onboarding (empty preferences)
      const hasPreferences = preferences.diets.length > 0 || preferences.skill || preferences.goal;

      if (!hasPreferences) {
        // User skipped - just show welcome screen without auto-querying
        return;
      }

      // Generate personalized query from preferences
      const dietText = preferences.diets.length > 0
        ? preferences.diets.join(", ").toLowerCase()
        : "";

      const goalMap: Record<string, string> = {
        "Balanced": "balanced nutrition",
        "Weight Loss": "weight loss and low calorie",
        "Muscle Gain": "high protein and muscle building",
        "Energy Boost": "energy boosting and high energy"
      };

      const parts = [];
      if (dietText) parts.push(dietText);
      if (preferences.skill) parts.push(`${preferences.skill.toLowerCase()} difficulty`);
      parts.push(`${preferences.servings} servings`);
      if (preferences.goal) parts.push(goalMap[preferences.goal] || preferences.goal.toLowerCase());

      const query = `Show me recipes that are ${parts.join(", ")}`;

      handleSend(query);
    }
  }, [preferences]);


  return (
    <>
      <style>{`
        .chat-container {
          display: flex;
          flex-direction: column;
          height: 100vh;
          height: 100dvh; /* Mobile viewport height */
          overflow: hidden;
          background: linear-gradient(135deg, rgba(240,253,244,0.92), rgba(187,247,208,0.92)),
            url("/images/bell-pepper.jpg"),
            url("/images/celery.jpg"),
            url("/images/italian-dish.jpg");
          background-size: cover, 400px, 350px, cover;
          background-position: center, top left, bottom right, center;
          background-repeat: no-repeat;
        }

        .chat-header {
          background: linear-gradient(135deg, #22c55e, #16a34a);
          color: white;
          padding: 16px;
          box-shadow: 0 4px 20px rgba(34,197,94,0.35);
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-shrink: 0;
        }

        .header-title {
          flex: 1;
        }

        .header-title h1 {
          margin: 0;
          font-size: 20px;
        }

        .header-title p {
          margin-top: 4px;
          opacity: 0.95;
          margin-bottom: 0;
          font-size: 12px;
        }

        .preferences-button {
          background: rgba(255, 255, 255, 0.15);
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-radius: 10px;
          padding: 8px 12px;
          color: white;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 6px;
          transition: all 0.2s ease;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          white-space: nowrap;
        }

        .preferences-button:active {
          transform: scale(0.95);
        }

        .preferences-badge {
          background: rgba(255, 255, 255, 0.95);
          border-bottom: 2px solid #bbf7d0;
          padding: 10px 16px;
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
          flex-shrink: 0;
          overflow-x: auto;
        }

        .preferences-label {
          font-size: 12px;
          font-weight: 600;
          color: #166534;
          white-space: nowrap;
        }

        .preference-tag {
          padding: 4px 10px;
          border-radius: 16px;
          font-size: 11px;
          font-weight: 600;
          white-space: nowrap;
          flex-shrink: 0;
        }

        .tag-diet {
          background: linear-gradient(135deg, #dcfce7, #bbf7d0);
          color: #166534;
          border: 1px solid #86efac;
        }

        .tag-skill {
          background: linear-gradient(135deg, #fef3c7, #fde68a);
          color: #92400e;
          border: 1px solid #fcd34d;
        }

        .tag-servings {
          background: linear-gradient(135deg, #dbeafe, #bfdbfe);
          color: #1e40af;
          border: 1px solid #93c5fd;
        }

        .tag-goal {
          background: linear-gradient(135deg, #fce7f3, #fbcfe8);
          color: #9f1239;
          border: 1px solid #f9a8d4;
        }

        .messages-container {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
          -webkit-overflow-scrolling: touch;
        }

        .messages-inner {
          max-width: 1200px;
          margin: 0 auto;
        }

        .welcome-screen {
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100%;
          background-size: cover;
          background-position: center;
          border-radius: 16px;
          margin: 0 -16px;
          padding: 32px 16px;
          position: relative;
          overflow: hidden;
        }

        .welcome-card {
          max-width: 900px;
          padding: 32px 24px;
          border-radius: 24px;
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(240, 253, 244, 0.95));
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.5) inset;
          backdrop-filter: blur(20px);
          border: 3px solid rgba(187, 247, 208, 0.5);
          position: relative;
          z-index: 1;
        }

        .welcome-icon {
          font-size: 60px;
          margin-bottom: 16px;
          text-align: center;
        }

        .welcome-title {
          font-size: 32px;
          font-weight: 800;
          background: linear-gradient(135deg, #16a34a, #22c55e, #4ade80);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          margin-bottom: 16px;
          text-align: center;
          line-height: 1.2;
        }

        .welcome-subtitle {
          font-size: 16px;
          line-height: 1.6;
          color: #166534;
          margin-bottom: 24px;
          text-align: center;
          font-weight: 500;
        }

        .suggestions-title {
          text-align: center;
          margin-bottom: 16px;
          font-size: 13px;
          color: #15803d;
          font-weight: 600;
          letter-spacing: 0.5px;
        }

        .suggestions-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 12px;
          margin-top: 16px;
        }

        .suggestion-button {
          padding: 16px 20px;
          border-radius: 16px;
          border: 2px solid #22c55e;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          font-size: 15px;
        }

        .suggestion-button:active {
          transform: scale(0.97);
        }

        .tagline {
          margin-top: 24px;
          text-align: center;
          font-size: 12px;
          color: #16a34a;
          font-style: italic;
          opacity: 0.8;
        }

        .message-bubble {
          display: flex;
          margin-bottom: 14px;
        }

        .message-bubble.user {
          justify-content: flex-end;
        }

        .message-bubble.assistant {
          justify-content: flex-start;
        }

        .message-content {
          max-width: 85%;
          padding: 14px 16px;
          border-radius: 16px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }

        .message-content.user {
          background: linear-gradient(135deg, #22c55e, #16a34a);
          color: white;
          box-shadow: 0 4px 14px rgba(34,197,94,0.35);
        }

        .message-content.assistant {
          background: rgba(255,255,255,0.96);
          color: #1f2937;
          max-width: 95%;
        }

        .message-text {
          line-height: 1.5;
          margin: 0;
          font-family: Arial, sans-serif;
          font-weight: bold;
          font-size: 14px;
        }

        .facts-container {
          margin-top: 12px;
          margin-bottom: 12px;
          padding: 14px;
          border-radius: 12px;
          background: linear-gradient(135deg, #fff7ed, #ffedd5);
          border: 1px solid #fed7aa;
        }

        .facts-title {
          color: #9a3412;
          font-size: 14px;
          font-weight: 600;
          margin-bottom: 8px;
        }

        .facts-list {
          margin-top: 10px;
          padding-left: 18px;
          margin-bottom: 0;
        }

        .fact-item {
          font-size: 13px;
          color: #7c2d12;
          line-height: 1.6;
          margin-bottom: 6px;
        }

        .recipes-container {
          margin-top: 12px;
        }

        .loading-indicator {
          color: #166534;
          font-weight: 500;
          font-size: 14px;
          padding: 12px;
        }

        .input-container {
          background: rgba(255,255,255,0.95);
          padding: 12px;
          border-top: 1px solid #bbf7d0;
          flex-shrink: 0;
        }

        .input-wrapper {
          max-width: 1200px;
          margin: 0 auto;
          display: flex;
          gap: 8px;
        }

        .chat-input {
          flex: 1;
          padding: 12px 18px;
          border-radius: 24px;
          border: 2px solid #bbf7d0;
          font-size: 15px;
          outline: none;
        }

        .chat-input:focus {
          border-color: #22c55e;
        }

        .send-button {
          padding: 12px 24px;
          border-radius: 24px;
          border: none;
          background: #22c55e;
          color: white;
          font-weight: 600;
          cursor: pointer;
          font-size: 15px;
          white-space: nowrap;
          transition: all 0.2s;
        }

        .send-button:active {
          transform: scale(0.95);
        }

        .send-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        /* Tablet */
        @media (min-width: 640px) {
          .chat-header {
            padding: 20px;
          }

          .header-title h1 {
            font-size: 28px;
          }

          .header-title p {
            font-size: 14px;
            margin-top: 6px;
          }

          .preferences-button {
            padding: 10px 16px;
            font-size: 15px;
            border-radius: 12px;
          }

          .preferences-badge {
            padding: 12px 20px;
            gap: 10px;
          }

          .preferences-label {
            font-size: 13px;
          }

          .preference-tag {
            padding: 6px 12px;
            font-size: 12px;
          }

          .messages-container {
            padding: 20px;
          }

          .welcome-card {
            padding: 48px 40px;
            border-radius: 28px;
          }

          .welcome-icon {
            font-size: 70px;
            margin-bottom: 20px;
          }

          .welcome-title {
            font-size: 38px;
            margin-bottom: 18px;
          }

          .welcome-subtitle {
            font-size: 18px;
            margin-bottom: 32px;
          }

          .suggestions-title {
            font-size: 14px;
            margin-bottom: 20px;
          }

          .suggestions-grid {
            grid-template-columns: repeat(2, 1fr);
            gap: 14px;
          }

          .suggestion-button {
            padding: 18px 22px;
            font-size: 16px;
          }

          .tagline {
            margin-top: 32px;
            font-size: 13px;
          }

          .message-content {
            max-width: 75%;
            padding: 16px 18px;
            border-radius: 18px;
          }

          .message-text {
            font-size: 15px;
          }

          .input-container {
            padding: 16px;
          }

          .input-wrapper {
            gap: 10px;
          }

          .chat-input {
            padding: 14px 20px;
            font-size: 16px;
          }

          .send-button {
            padding: 14px 32px;
            font-size: 16px;
          }
        }

        /* Desktop */
        @media (min-width: 1024px) {
          .chat-header {
            padding: 24px;
          }

          .header-title h1 {
            font-size: 32px;
          }

          .preferences-badge {
            padding: 12px 24px;
            gap: 12px;
          }

          .preferences-label {
            font-size: 14px;
          }

          .preference-tag {
            padding: 6px 14px;
            font-size: 13px;
          }

          .messages-container {
            padding: 24px;
          }

          .welcome-card {
            padding: 60px 50px;
            border-radius: 32px;
          }

          .welcome-icon {
            font-size: 80px;
            margin-bottom: 24px;
          }

          .welcome-title {
            font-size: 42px;
            margin-bottom: 20px;
          }

          .welcome-subtitle {
            font-size: 20px;
            margin-bottom: 40px;
          }

          .suggestions-title {
            font-size: 16px;
            margin-bottom: 24px;
          }

          .suggestions-grid {
            gap: 16px;
          }

          .suggestion-button {
            padding: 20px 24px;
            font-size: 17px;
          }

          .tagline {
            margin-top: 40px;
            font-size: 14px;
          }

          .message-content {
            max-width: 70%;
            padding: 20px;
            border-radius: 20px;
          }

          .message-content.assistant {
            max-width: 95%;
          }

          .message-text {
            font-size: 16px;
            line-height: 1.6;
          }

          .facts-container {
            padding: 18px;
            border-radius: 14px;
          }

          .facts-title {
            font-size: 16px;
          }

          .facts-list {
            padding-left: 20px;
          }

          .fact-item {
            font-size: 14px;
            line-height: 1.7;
          }

          .input-container {
            padding: 18px;
          }

          .chat-input {
            padding: 14px 22px;
          }

          .send-button {
            padding: 14px 36px;
          }
        }
      `}</style>

      <div className="chat-container">
        {/* Header */}
        <div className="chat-header">
          <div className="header-title">
            <h1>🍳 CulinaraAI</h1>
            <p>Your AI Culinary Coach with Attitude 🌿</p>
          </div>

          {/* Settings Button */}
          {onBackToPreferences && (
            <button
              onClick={() => {
                clearPreferences();
                onBackToPreferences();
              }}
              className="preferences-button"
              title="Change your dietary preferences and settings"
            >
              <span style={{ fontSize: "18px" }}>⚙️</span>
              <span className="button-text">Preferences</span>
            </button>
          )}
        </div>

        {/* Preferences Badge */}
        {preferences && (preferences.diets.length > 0 || preferences.skill || preferences.goal) && (
          <div className="preferences-badge">
            <span className="preferences-label">Active Preferences:</span>
            {preferences.diets.length > 0 && (
              <span className="preference-tag tag-diet">
                🥗 {preferences.diets.join(", ")}
              </span>
            )}
            {preferences.skill && (
              <span className="preference-tag tag-skill">
                👨‍🍳 {preferences.skill}
              </span>
            )}
            <span className="preference-tag tag-servings">
              🍽️ {preferences.servings} servings
            </span>
            {preferences.goal && (
              <span className="preference-tag tag-goal">
                🎯 {preferences.goal}
              </span>
            )}
          </div>
        )}

        {/* Messages */}
        <div className="messages-container">
          <div className="messages-inner">
            {/* Welcome Screen */}
            {showWelcome && messages.length === 0 && (
              <div
                className="welcome-screen"
                style={{
                  backgroundImage: `linear-gradient(135deg, rgba(34, 197, 94, 0.85), rgba(22, 163, 74, 0.85)), url('${welcomeBackgroundImage}')`,
                }}
              >
                <div className="welcome-card">
                  <div className="welcome-icon">🍳</div>
                  <h2 className="welcome-title">Welcome to CulinaraAI! 🌿</h2>
                  <p className="welcome-subtitle">
                    Your personal AI chef is here to help you discover delicious, healthy recipes tailored just for you.
                    Let's create something amazing together!
                  </p>

                  <div className="suggestions-title">🔥 POPULAR SEARCHES</div>
                  <div className="suggestions-grid">
                    {[
                      { emoji: "🥗", text: "Healthy salad ideas", color: "#dcfce7" },
                      { emoji: "🍝", text: "Quick pasta recipes", color: "#fef3c7" },
                      { emoji: "🌮", text: "Vegan options", color: "#dbeafe" },
                      { emoji: "🍰", text: "Easy desserts", color: "#fce7f3" },
                    ].map((suggestion, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setInput(suggestion.text);
                          setWelcomeBackgroundImage(getFoodBackgroundImage(suggestion.text));
                        }}
                        onMouseEnter={() => {
                          setWelcomeBackgroundImage(getFoodBackgroundImage(suggestion.text));
                        }}
                        onMouseLeave={() => {
                          setWelcomeBackgroundImage(getFoodBackgroundImage(""));
                        }}
                        className="suggestion-button"
                        style={{
                          background: suggestion.color,
                          color: "#166534",
                        }}
                      >
                        <span style={{ fontSize: "24px" }}>{suggestion.emoji}</span>
                        <span>{suggestion.text}</span>
                      </button>
                    ))}
                  </div>

                  <div className="tagline">
                    "Great cooking is about being inspired by the simple things around you" 🌱
                  </div>
                </div>
              </div>
            )}

            {messages.map((message, idx) => (
              <div key={idx} className={`message-bubble ${message.role}`}>
                <div className={`message-content ${message.role}`}>
                  {/* Assistant text */}
                  {message.content && (
                    <p className="message-text">{message.content}</p>
                  )}

                  {/* LLM-generated facts */}
                  {message.facts && message.facts.length > 0 && (
                    <div className="facts-container">
                      <div className="facts-title">💡 Chef's Notes</div>
                      <ul className="facts-list">
                        {message.facts.map((fact, i) => (
                          <li key={i} className="fact-item">{fact}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Recipes */}
                  {message.recipes && message.recipes.length > 0 && (
                    <div className="recipes-container">
                      <RecipeResults recipes={message.recipes} />
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="loading-indicator">
                🍳 CulinaraAI is cooking something delicious…
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="input-container">
          <div className="input-wrapper">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask me anything… 🌱"
              className="chat-input"
              disabled={isLoading}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
              className="send-button"
            >
              Send 🚀
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
