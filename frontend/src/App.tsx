import React, { useState } from "react";
import { Onboarding } from "./components/Onboarding";
import { ChatInterface } from "./components/ChatInterface";
import { PreferencesProvider, UserPreferences, usePreferences } from "./contexts/PreferencesContext";

const AppContent: React.FC = () => {
  const [showChat, setShowChat] = useState(false);
  const { setPreferences } = usePreferences();

  const handleBackToPreferences = () => {
    setShowChat(false);
  };

  if (!showChat) {
    return (
      <Onboarding
        onComplete={(prefs: UserPreferences) => {
          setPreferences(prefs);
          setShowChat(true);
        }}
      />
    );
  }

  return <ChatInterface onBackToPreferences={handleBackToPreferences} />;
};

export const App: React.FC = () => {
  return (
    <PreferencesProvider>
      <AppContent />
    </PreferencesProvider>
  );
};