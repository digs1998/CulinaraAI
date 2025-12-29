import React, { createContext, useContext, useState, ReactNode } from 'react';

export interface UserPreferences {
  diets: string[];
  skill: string;
  servings: number;
  goal: string;
}

interface PreferencesContextType {
  preferences: UserPreferences | null;
  setPreferences: (prefs: UserPreferences) => void;
  clearPreferences: () => void;
}

const PreferencesContext = createContext<PreferencesContextType | undefined>(undefined);

export const PreferencesProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [preferences, setPreferencesState] = useState<UserPreferences | null>(() => {
    // Try to load from localStorage on init
    const stored = localStorage.getItem('userPreferences');
    return stored ? JSON.parse(stored) : null;
  });

  const setPreferences = (prefs: UserPreferences) => {
    setPreferencesState(prefs);
    localStorage.setItem('userPreferences', JSON.stringify(prefs));
  };

  const clearPreferences = () => {
    setPreferencesState(null);
    localStorage.removeItem('userPreferences');
  };

  return (
    <PreferencesContext.Provider value={{ preferences, setPreferences, clearPreferences }}>
      {children}
    </PreferencesContext.Provider>
  );
};

export const usePreferences = () => {
  const context = useContext(PreferencesContext);
  if (context === undefined) {
    throw new Error('usePreferences must be used within a PreferencesProvider');
  }
  return context;
};
