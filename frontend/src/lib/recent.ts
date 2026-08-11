const KEY = "discover-recent-v15";

export interface RecentItem {
  query: string;
  when: number;
}

export function getRecent(): RecentItem[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

export function addRecent(query: string) {
  const items = getRecent().filter((r) => r.query !== query);
  items.unshift({ query, when: Date.now() });
  localStorage.setItem(KEY, JSON.stringify(items.slice(0, 12)));
}
