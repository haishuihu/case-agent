import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { listModels, type ModelOption } from "../services/api";

const STORAGE_KEY = "case-agent:selectedModelKey";

function getStoredModelKey(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function setStoredModelKey(key: string | undefined): void {
  try {
    if (key) {
      localStorage.setItem(STORAGE_KEY, key);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // localStorage may be unavailable
  }
}

interface ModelConfigContextValue {
  modelOptions: ModelOption[];
  selectedModelKey: string | undefined;
  setSelectedModelKey: (key: string) => void;
  selectedModel: ModelOption | undefined;
}

const ModelConfigContext = createContext<ModelConfigContextValue | null>(null);

export function ModelConfigProvider({ children }: { children: ReactNode }) {
  const [modelOptions, setModelOptions] = useState<ModelOption[]>([]);
  const [selectedModelKey, _setSelectedModelKey] = useState<string | undefined>(
    () => getStoredModelKey() ?? undefined
  );

  useEffect(() => {
    let cancelled = false;
    listModels()
      .then((opts) => {
        if (cancelled) return;
        setModelOptions(opts);
        _setSelectedModelKey((current) => {
          // If the stored key still exists in the fetched model list, keep it
          if (current && opts.some((m) => m.key === current)) {
            return current;
          }
          // Otherwise default to first option
          const fallback = opts[0]?.key;
          setStoredModelKey(fallback);
          return fallback;
        });
      })
      .catch(() => {
        // Silently ignore; pages can show their own error state
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const setSelectedModelKey = useCallback((key: string) => {
    setStoredModelKey(key);
    _setSelectedModelKey(key);
  }, []);

  const selectedModel = useMemo(
    () => modelOptions.find((m) => m.key === selectedModelKey),
    [modelOptions, selectedModelKey]
  );

  const value = useMemo<ModelConfigContextValue>(
    () => ({
      modelOptions,
      selectedModelKey,
      setSelectedModelKey,
      selectedModel,
    }),
    [modelOptions, selectedModelKey, setSelectedModelKey, selectedModel]
  );

  return (
    <ModelConfigContext.Provider value={value}>
      {children}
    </ModelConfigContext.Provider>
  );
}

export function useModelConfig(): ModelConfigContextValue {
  const ctx = useContext(ModelConfigContext);
  if (!ctx) {
    throw new Error("useModelConfig must be used within ModelConfigProvider");
  }
  return ctx;
}
