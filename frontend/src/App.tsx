import React, { useState } from "react";
import { Onboarding } from "./components/Onboarding";
import { ChatInterface } from "./components/ChatInterface";

export const App: React.FC = () => {
  const [showChat, setShowChat] = useState(false);

  if (!showChat) {
    return (
      <Onboarding
        onComplete={() => {
          setShowChat(true);
          // Optionally send prefs to your backend or store in context
        }}
      />
    );
  }

  return <ChatInterface />;
};