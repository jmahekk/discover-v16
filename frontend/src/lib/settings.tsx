import { createContext, useContext, useEffect, useState, ReactNode } from "react";

export interface Settings {
  mode: "auto" | "manual" | "all";
  manualCategories: string[];
  bm25K: number;
  finalK: number;
  debugContext: boolean;
}

const DEFAULTS: Settings = {
  mode: "auto",
  manualCategories: [],
  bm25K: 100,
  finalK: 7,
  debugContext: false,
};

const KEY = "discover-settings-v15";

interface Ctx {
  settings: Settings;
  update: (patch: Partial<Settings>) => void;
}

const SettingsContext = createContext<Ctx>({ settings: DEFAULTS, update: () => {} });

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(() => {
    try {
      const raw = localStorage.getItem(KEY);
      return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : DEFAULTS;
    } catch {
      return DEFAULTS;
    }
  });

  useEffect(() => {
    localStorage.setItem(KEY, JSON.stringify(settings));
  }, [settings]);

  const update = (patch: Partial<Settings>) =>
    setSettings((prev) => ({ ...prev, ...patch }));

  return (
    <SettingsContext.Provider value={{ settings, update }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  return useContext(SettingsContext);
}
