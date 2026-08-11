export interface CategoryCount {
  name: string;
  count: number;
}

export interface Meta {
  total_papers: number;
  categories: CategoryCount[];
  venues: CategoryCount[];
  colbert_cache: boolean;
}

export interface Routing {
  mode: "single" | "multi" | "all" | "manual";
  confidence: "high" | "medium" | "low" | "manual";
  categories: string[];
  scores: { name: string; score: number }[];
  elapsed_ms: number;
}

export interface PaperSummary {
  id: number;
  title: string;
  authors: string;
  publication: string;
  broad_category: string;
  category: string;
  abstract: string;
  keywords: string;
}

export interface ResultPaper extends PaperSummary {
  novelty: string;
  bm25: number;
  colbert: number;
}

export interface Candidate {
  id: number;
  title: string;
  broad_category: string;
  bm25: number;
}

export interface SearchResponse {
  routing: Routing;
  papers_in_scope: number;
  candidates: Candidate[];
  results: ResultPaper[];
  timings: { bm25_ms: number; colbert_ms: number };
}

export interface PaperDetail extends PaperSummary {
  introduction: string;
  conclusion: string;
  limitations: string;
  novelty: string;
}

export interface Insights {
  total_papers: number;
  categories: CategoryCount[];
  venues: CategoryCount[];
  coverage: Record<string, number>;
}

export interface AnswerMeta {
  intent: string;
  sources: string[];
}
