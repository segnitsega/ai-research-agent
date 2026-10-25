export type ThemeChoice = "light" | "dark" | "system";
export type DepthChoice = "quick" | "standard" | "deep";

export type DeskPrefs = {
  theme: ThemeChoice;
  depth: DepthChoice;
  useMemory: boolean;
};

export const defaultPrefs: DeskPrefs = {
  theme: "system",
  depth: "standard",
  useMemory: true,
};

const KEY = "folio-prefs";
const EVENT = "folio-prefs";

export function readPrefs(): DeskPrefs {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return defaultPrefs;
    const parsed = JSON.parse(raw) as Partial<DeskPrefs>;
    return {
      theme: parsed.theme === "light" || parsed.theme === "dark" || parsed.theme === "system" ? parsed.theme : "system",
      depth: parsed.depth === "quick" || parsed.depth === "standard" || parsed.depth === "deep" ? parsed.depth : "standard",
      useMemory: typeof parsed.useMemory === "boolean" ? parsed.useMemory : true,
    };
  } catch {
    return defaultPrefs;
  }
}

export function writePrefs(next: DeskPrefs) {
  localStorage.setItem(KEY, JSON.stringify(next));
  applyTheme(next.theme);
  window.dispatchEvent(new Event(EVENT));
}

export function applyTheme(theme: ThemeChoice) {
  const dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
  document.documentElement.classList.toggle("light", theme === "light");
  document.documentElement.dataset.theme = theme;
}

export function subscribePrefs(onStoreChange: () => void) {
  const onChange = () => onStoreChange();
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onChange);
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const onMedia = () => {
    if (readPrefs().theme === "system") applyTheme("system");
    onStoreChange();
  };
  media.addEventListener("change", onMedia);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onChange);
    media.removeEventListener("change", onMedia);
  };
}
