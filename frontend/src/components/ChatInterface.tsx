import React, { useState, useRef, useEffect } from "react";
import { feastronAPI } from "../services/api";
import { ChatMessage } from "../types";
import { RecipeResults } from "../components/recipesResults.tsx";

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "👋 Hey! I'm Feastron, your AI culinary coach with attitude. What are you craving today?",
    },
  ]);

  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");

    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await feastronAPI.sendMessage({
        message: userMessage,
      });

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.message,
          recipes: response.recipes,
        },
      ]);
    } catch (error) {
      console.error("Error:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Oops! Something went wrong. Make sure the backend is running on http://localhost:8000",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        maxWidth: "1200px",
        margin: "0 auto",
        backgroundColor: "#f9fafb",
      }}
    >
      {/* Header */}
      <div
        style={{
          background: "linear-gradient(to right, #f97316, #ef4444)",
          color: "white",
          padding: "24px",
        }}
      >
        <h1 style={{ fontSize: "32px", fontWeight: "bold", margin: 0 }}>
          🍳 Feastron
        </h1>
        <p style={{ fontSize: "14px", opacity: 0.9 }}>
          Your AI Culinary Coach with Attitude
        </p>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "24px" }}>
        {messages.map((message, index) => (
          <div
            key={index}
            style={{
              display: "flex",
              justifyContent:
                message.role === "user" ? "flex-end" : "flex-start",
              marginBottom: "16px",
            }}
          >
            <div
              style={{
                maxWidth: "80%",
                borderRadius: "16px",
                padding: "16px 24px",
                backgroundColor:
                  message.role === "user" ? "#f97316" : "white",
                color: message.role === "user" ? "white" : "#1f2937",
              }}
            >
              {(!message.recipes || message.recipes.length === 0) && (
                <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>
                  {message.content}
                </p>
              )}

              {/* ✅ RecipeResults component */}
              {message.recipes && message.recipes.length > 0 && (
                <RecipeResults recipes={message.recipes} />
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div style={{ color: "#6b7280" }}>Feastron is thinking…</div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div
        style={{
          borderTop: "1px solid #e5e7eb",
          backgroundColor: "white",
          padding: "16px",
        }}
      >
        <div style={{ display: "flex", gap: "8px" }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask me anything..."
            style={{
              flex: 1,
              borderRadius: "24px",
              border: "1px solid #d1d5db",
              padding: "12px 24px",
            }}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            style={{
              backgroundColor:
                isLoading || !input.trim() ? "#d1d5db" : "#f97316",
              color: "white",
              borderRadius: "24px",
              padding: "12px 32px",
              border: "none",
              cursor: "pointer",
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};
