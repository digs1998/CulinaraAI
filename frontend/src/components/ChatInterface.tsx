import React, { useState, useRef, useEffect } from "react";
import { CulinaraAIAPI } from "../services/api";
import { ChatMessage } from "../types";
import { RecipeResults } from "../components/recipesResults.tsx";

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

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showWelcome, setShowWelcome] = useState(true);
  const [welcomeBackgroundImage, setWelcomeBackgroundImage] = useState(
    getFoodBackgroundImage("")
  );

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setShowWelcome(false);

    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await CulinaraAIAPI.sendMessage({ message: userMessage });

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
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "⚠️ Something went wrong. Make sure the backend is running on http://localhost:8000",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        overflow: "hidden",
        background: `
          linear-gradient(135deg, rgba(240,253,244,0.92), rgba(187,247,208,0.92)),
          url("/images/bell-pepper.jpg"),
          url("/images/celery.jpg"),
          url("/images/italian-dish.jpg")
        `,
        backgroundSize: "cover, 400px, 350px, cover",
        backgroundPosition: "center, top left, bottom right, center",
        backgroundRepeat: "no-repeat",
      }}
    >
      {/* Header */}
      <div
        style={{
          background: "linear-gradient(135deg, #22c55e, #16a34a)",
          color: "white",
          padding: "24px",
          boxShadow: "0 4px 20px rgba(34,197,94,0.35)",
        }}
      >
        <h1 style={{ margin: 0, fontSize: "32px" }}>🍳 CulinaraAI</h1>
        <p style={{ marginTop: 6, opacity: 0.95 }}>
          Your AI Culinary Coach with Attitude 🌿
        </p>
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "24px",
        }}
      >
        <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
          {/* Welcome Screen */}
          {showWelcome && messages.length === 0 && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                minHeight: "calc(100vh - 300px)",
                backgroundImage: `linear-gradient(135deg, rgba(34, 197, 94, 0.85), rgba(22, 163, 74, 0.85)), url('${welcomeBackgroundImage}')`,
                backgroundSize: "cover",
                backgroundPosition: "center",
                borderRadius: "20px",
                margin: "0 -24px",
                padding: "48px 24px",
                position: "relative",
                overflow: "hidden",
              }}
            >
              {/* Animated floating food icons */}
              <div style={{
                position: "absolute",
                top: "10%",
                left: "10%",
                fontSize: "60px",
                animation: "float 6s ease-in-out infinite",
                opacity: 0.3,
              }}>🥗</div>
              <div style={{
                position: "absolute",
                top: "20%",
                right: "15%",
                fontSize: "50px",
                animation: "float 8s ease-in-out infinite 1s",
                opacity: 0.3,
              }}>🍳</div>
              <div style={{
                position: "absolute",
                bottom: "15%",
                left: "15%",
                fontSize: "55px",
                animation: "float 7s ease-in-out infinite 2s",
                opacity: 0.3,
              }}>🥘</div>
              <div style={{
                position: "absolute",
                bottom: "25%",
                right: "10%",
                fontSize: "45px",
                animation: "float 9s ease-in-out infinite 1.5s",
                opacity: 0.3,
              }}>🌮</div>

              <div
                style={{
                  maxWidth: "900px",
                  padding: "60px 50px",
                  borderRadius: "32px",
                  background: "linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(240, 253, 244, 0.95))",
                  boxShadow: "0 20px 60px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.5) inset",
                  backdropFilter: "blur(20px)",
                  border: "3px solid rgba(187, 247, 208, 0.5)",
                  animation: "slideUp 0.8s ease-out",
                  position: "relative",
                  zIndex: 1,
                }}
              >
                {/* Sparkle effect */}
                <div style={{
                  position: "absolute",
                  top: "20px",
                  right: "30px",
                  fontSize: "30px",
                  animation: "sparkle 2s ease-in-out infinite",
                }}>✨</div>
                <div style={{
                  position: "absolute",
                  top: "40px",
                  left: "30px",
                  fontSize: "25px",
                  animation: "sparkle 2s ease-in-out infinite 0.5s",
                }}>⭐</div>

                <div
                  style={{
                    fontSize: "80px",
                    marginBottom: "24px",
                    textAlign: "center",
                    animation: "bounce 2s ease-in-out infinite",
                  }}
                >
                  🍳
                </div>
                <h2
                  style={{
                    fontSize: "42px",
                    fontWeight: 800,
                    background: "linear-gradient(135deg, #16a34a, #22c55e, #4ade80)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    backgroundClip: "text",
                    marginBottom: "20px",
                    textAlign: "center",
                    lineHeight: 1.2,
                    letterSpacing: "-0.5px",
                  }}
                >
                  Welcome to CulinaraAI! 🌿
                </h2>
                <p
                  style={{
                    fontSize: "20px",
                    lineHeight: 1.8,
                    color: "#166534",
                    marginBottom: "40px",
                    textAlign: "center",
                    fontWeight: 500,
                  }}
                >
                  Your personal AI chef is here to help you discover delicious, healthy recipes tailored just for you.
                  Let's create something amazing together!
                </p>

                {/* Quick start suggestions */}
                <div style={{
                  textAlign: "center",
                  marginBottom: "30px",
                  fontSize: "16px",
                  color: "#15803d",
                  fontWeight: 600,
                  letterSpacing: "0.5px",
                }}>
                  🔥 POPULAR SEARCHES
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, 1fr)",
                    gap: "16px",
                    marginTop: "24px",
                  }}
                >
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
                      onMouseEnter={(e) => {
                        setWelcomeBackgroundImage(getFoodBackgroundImage(suggestion.text));
                        e.currentTarget.style.transform = "translateY(-4px) scale(1.02)";
                        e.currentTarget.style.boxShadow = "0 12px 24px rgba(34, 197, 94, 0.3)";
                      }}
                      onMouseLeave={(e) => {
                        setWelcomeBackgroundImage(getFoodBackgroundImage(""));
                        e.currentTarget.style.transform = "translateY(0) scale(1)";
                        e.currentTarget.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.1)";
                      }}
                      style={{
                        padding: "20px 24px",
                        borderRadius: "20px",
                        border: "3px solid #22c55e",
                        background: suggestion.color,
                        color: "#166534",
                        fontSize: "17px",
                        fontWeight: 600,
                        cursor: "pointer",
                        transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.1)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "10px",
                      }}
                    >
                      <span style={{ fontSize: "28px" }}>{suggestion.emoji}</span>
                      <span>{suggestion.text}</span>
                    </button>
                  ))}
                </div>

                {/* Fun tagline */}
                <div style={{
                  marginTop: "40px",
                  textAlign: "center",
                  fontSize: "14px",
                  color: "#16a34a",
                  fontStyle: "italic",
                  opacity: 0.8,
                }}>
                  "Great cooking is about being inspired by the simple things around you" 🌱
                </div>
              </div>

              <style>{`
                @keyframes float {
                  0%, 100% { transform: translateY(0px); }
                  50% { transform: translateY(-20px); }
                }
                @keyframes slideUp {
                  from {
                    opacity: 0;
                    transform: translateY(30px);
                  }
                  to {
                    opacity: 1;
                    transform: translateY(0);
                  }
                }
                @keyframes bounce {
                  0%, 100% { transform: translateY(0); }
                  50% { transform: translateY(-10px); }
                }
                @keyframes sparkle {
                  0%, 100% { opacity: 0.3; transform: scale(1); }
                  50% { opacity: 1; transform: scale(1.2); }
                }
              `}</style>
            </div>
          )}

          {messages.map((message, idx) => (
            <div
              key={idx}
              style={{
                display: "flex",
                justifyContent:
                  message.role === "user" ? "flex-end" : "flex-start",
                marginBottom: "18px",
              }}
            >
              <div
                style={{
                  maxWidth: message.role === "user" ? "70%" : "95%",
                  padding: "20px",
                  borderRadius: "20px",
                  background:
                    message.role === "user"
                      ? "linear-gradient(135deg, #22c55e, #16a34a)"
                      : "rgba(255,255,255,0.96)",
                  color: message.role === "user" ? "white" : "#1f2937",
                  boxShadow:
                    message.role === "user"
                      ? "0 4px 14px rgba(34,197,94,0.35)"
                      : "0 2px 12px rgba(0,0,0,0.08)",
                }}
              >
                {/* Assistant text */}
                {message.content && (
                  <p style={{
                    lineHeight: 1.6,
                    marginBottom: "14px",
                    margin: 0,
                    fontFamily: "Arial, sans-serif",
                    fontWeight: "bold"
                  }}>
                    {message.content}
                  </p>
                )}

                {/* DEBUG: Show if facts exist */}
                {message.role === "assistant" && (
                  <div style={{ display: "none" }}>
                    Facts array: {JSON.stringify(message.facts)}
                    Facts length: {message.facts?.length || 0}
                  </div>
                )}

                {/* LLM-generated facts - Show FIRST */}
                {message.facts && message.facts.length > 0 && (
                  <div
                    style={{
                      marginTop: "16px",
                      marginBottom: "16px",
                      padding: "18px",
                      borderRadius: "14px",
                      background:
                        "linear-gradient(135deg, #fff7ed, #ffedd5)",
                      border: "1px solid #fed7aa",
                    }}
                  >
                    <strong style={{ color: "#9a3412", fontSize: "16px" }}>
                      💡 Chef's Notes
                    </strong>
                    <ul style={{ marginTop: "12px", paddingLeft: "20px", marginBottom: 0 }}>
                      {message.facts.map((fact, i) => (
                        <li
                          key={i}
                          style={{
                            fontSize: "14px",
                            color: "#7c2d12",
                            lineHeight: 1.7,
                            marginBottom: "8px",
                          }}
                        >
                          {fact}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Recipes */}
                {message.recipes && message.recipes.length > 0 && (
                  <div style={{ marginTop: "16px" }}>
                    <RecipeResults recipes={message.recipes} />
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div style={{ color: "#166534", fontWeight: 500 }}>
              🍳 CulinaraAI is cooking something delicious…
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div
        style={{
          background: "rgba(255,255,255,0.95)",
          padding: "18px",
          borderTop: "1px solid #bbf7d0",
        }}
      >
        <div style={{ maxWidth: "1200px", margin: "0 auto", display: "flex" }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask me anything… 🌱"
            style={{
              flex: 1,
              padding: "14px 22px",
              borderRadius: "30px",
              border: "2px solid #bbf7d0",
              fontSize: "16px",
            }}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            style={{
              marginLeft: "12px",
              padding: "14px 36px",
              borderRadius: "30px",
              border: "none",
              background: "#22c55e",
              color: "white",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Send 🚀
          </button>
        </div>
      </div>
    </div>
  );
};
