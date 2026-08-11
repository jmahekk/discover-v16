"""
Builds the context sent to the LLM by scoring every sentence in a paper
against the question and keeping only the sentences that are relevant.
"""

import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


INTENT_PATTERNS = {
    "statistics": [
        r"\bstat(istic)?s?\b", r"\bdataset\b", r"\bdata\b", r"\bsize\b",
        r"\bhow many\b", r"\bnumber of\b", r"\bsamples?\b", r"\bentries\b",
        r"\binstances?\b", r"\bannotations?\b", r"\bcorpus\b", r"\bcount\b",
        r"\brecords?\b", r"\bvolume\b", r"\bhow large\b", r"\bhow big\b"
    ],
    "methodology": [
        r"\bmethod(ology)?\b", r"\bapproach\b", r"\barchitecture\b",
        r"\bhow does\b", r"\bhow do\b", r"\bmodel\b", r"\bframework\b",
        r"\btechnique\b", r"\balgorithm\b", r"\bdesign\b", r"\bpipeline\b",
        r"\bstep\b", r"\bprocess\b", r"\bhow is\b", r"\bbuilt\b"
    ],
    "limitations": [
        r"\blimitation\b", r"\bdrawback\b", r"\bweakness\b", r"\bshortcoming\b",
        r"\bfailure\b", r"\bcriticism\b", r"\bproblem with\b", r"\bissue\b",
        r"\bchallenges?\b", r"\bnot able\b", r"\bcannot\b", r"\bstruggle\b"
    ],
    "comparison": [
        r"\bcompare\b", r"\bvs\b", r"\bversus\b", r"\bbetter than\b",
        r"\bbaseline\b", r"\bstate.of.the.art\b", r"\bsota\b",
        r"\bdifference\b", r"\bsimilar\b", r"\boutperform\b", r"\bbeat\b"
    ],
    "languages": [
        r"\blanguage\b", r"\blingual\b", r"\bmultilingual\b",
        r"\bcross.lingual\b", r"\bwhich languages\b", r"\bsupport\b",
        r"\bcovered\b", r"\blocale\b", r"\btongue\b", r"\bdialect\b"
    ],
    "results": [
        r"\bresult\b", r"\bperformance\b", r"\baccuracy\b", r"\bscore\b",
        r"\bbenchmark\b", r"\bevaluation\b", r"\bmetric\b", r"\bf1\b",
        r"\bbleu\b", r"\brouge\b", r"\bprecision\b", r"\brecall\b",
        r"\bachieve\b", r"\breport\b", r"\bperform\b"
    ],
    "use_case": [
        r"\buse\b", r"\bapplication\b", r"\bcan i use\b", r"\bsuitable\b",
        r"\bfor my\b", r"\btask\b", r"\bgenerat\b", r"\bclassif\b",
        r"\bwhich.*can\b", r"\bwhat.*for\b", r"\bpurpose\b", r"\bused for\b"
    ]
}

INTENT_SECTION_BOOST = {
    "statistics":  ["abstract", "introduction"],
    "methodology": ["introduction", "conclusion"],
    "limitations": ["limitations", "conclusion"],
    "comparison":  ["abstract", "conclusion"],
    "languages":   ["abstract", "introduction"],
    "results":     ["conclusion", "abstract"],
    "use_case":    ["abstract", "introduction"],
    "general":     ["abstract", "conclusion"],
}

ALWAYS_INCLUDE = ["abstract"]

ALL_SECTIONS = [
    "abstract",
    "introduction",
    "conclusion",
    "limitations",
    "novelty",
]

MAX_SENTENCES_PER_SECTION = {
    "abstract":     20,
    "introduction": 12,
    "conclusion":   12,
    "limitations":  10,
    "novelty":       6,
}

MIN_SENTENCE_SCORE = 0.05


def detect_intent(query: str) -> str:
    """Detect the primary intent of the user query, or 'general' if none matched."""
    query_lower = query.lower()
    scores = {intent: 0 for intent in INTENT_PATTERNS}

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                scores[intent] += 1

    best_intent = max(scores, key=scores.get)
    return best_intent if scores[best_intent] > 0 else "general"


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences, protecting common abbreviations (et al., Fig., i.e., ...)."""
    protected = text
    abbreviations = [
        "et al.", "Fig.", "fig.", "Eq.", "eq.", "i.e.", "e.g.",
        "vs.", "approx.", "cf.", "Dr.", "Prof.", "Sr.", "Jr.",
        "No.", "nos.", "pp.", "vol.", "ed.", "eds."
    ]
    placeholders = {}
    for i, abbr in enumerate(abbreviations):
        placeholder = f"__ABBR{i}__"
        placeholders[placeholder] = abbr
        protected = protected.replace(abbr, placeholder)

    raw_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', protected)

    sentences = []
    for s in raw_sentences:
        for placeholder, abbr in placeholders.items():
            s = s.replace(placeholder, abbr)
        s = s.strip()
        if len(s) > 30:
            sentences.append(s)

    return sentences


def score_sentences_tfidf(query: str, sentences: list[str]) -> list[float]:
    """
    Score each sentence against the query with TF-IDF cosine similarity.
    Falls back to keyword overlap if TF-IDF fails (too few sentences, etc).
    """
    if not sentences:
        return []

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1
        )
        all_texts = [query] + sentences
        tfidf_matrix = vectorizer.fit_transform(all_texts)

        query_vec = tfidf_matrix[0]
        sentence_vecs = tfidf_matrix[1:]

        similarities = cosine_similarity(query_vec, sentence_vecs)[0]
        return similarities.tolist()

    except Exception:
        return keyword_overlap_scores(query, sentences)


def keyword_overlap_scores(query: str, sentences: list[str]) -> list[float]:
    """Fallback scoring: fraction of query words that appear in each sentence."""
    query_words = set(re.findall(r"\b\w{3,}\b", query.lower()))
    if not query_words:
        return [0.0] * len(sentences)

    scores = []
    for sentence in sentences:
        sent_lower = sentence.lower()
        matches = sum(1 for w in query_words if w in sent_lower)
        scores.append(matches / len(query_words))

    return scores


def extract_query_entities(query: str) -> list[str]:
    """
    Pull out likely paper names, dataset names, and technical terms from the
    query: quoted phrases, capitalised words, and ALL CAPS acronyms.
    """
    entities = []

    quoted = re.findall(r'"([^"]+)"', query)
    entities.extend(quoted)

    caps_words = re.findall(r'\b[A-Z][A-Za-z]{2,}\b', query)
    entities.extend(caps_words)

    acronyms = re.findall(r'\b[A-Z]{2,}\b', query)
    entities.extend(acronyms)

    return list(set(entities))


def compute_entity_bonus(entities: list[str], sentences: list[str]) -> list[float]:
    """Bonus score per sentence based on how many query entities it contains."""
    if not entities:
        return [0.0] * len(sentences)

    bonuses = []
    for sentence in sentences:
        bonus = sum(
            0.15 for entity in entities
            if entity.lower() in sentence.lower()
        )
        bonuses.append(min(bonus, 0.5))

    return bonuses


def extract_relevant_sentences(
    query: str,
    section_text: str,
    section_name: str,
    intent: str,
    entities: list[str],
    is_boosted_section: bool,
    max_sentences: int
) -> str:
    """
    Extract the most relevant sentences from a single section: score with
    TF-IDF + entity bonus + intent boost, filter below MIN_SENTENCE_SCORE,
    take the top max_sentences, then restore original reading order.
    """
    if not section_text or len(section_text.strip()) < 50:
        return ""

    if section_name == "abstract":
        return section_text.strip()

    sentences = split_into_sentences(section_text)
    if not sentences:
        return ""

    tfidf_scores = score_sentences_tfidf(query, sentences)
    entity_bonuses = compute_entity_bonus(entities, sentences)

    combined_scores = []
    for i in range(len(sentences)):
        score = tfidf_scores[i] + entity_bonuses[i]
        if is_boosted_section:
            score *= 1.4
        combined_scores.append(score)

    indexed = list(enumerate(zip(sentences, combined_scores)))

    relevant = [
        (idx, sent, score)
        for idx, (sent, score) in indexed
        if score >= MIN_SENTENCE_SCORE
    ]

    if not relevant:
        top3 = sorted(indexed, key=lambda x: x[1][1], reverse=True)[:3]
        relevant = [(idx, sent, score) for idx, (sent, score) in top3]

    top_relevant = sorted(relevant, key=lambda x: x[2], reverse=True)[:max_sentences]
    top_relevant.sort(key=lambda x: x[0])

    extracted = " ".join(sent for _, sent, _ in top_relevant)
    return extracted.strip()


def build_paper_context(query: str, paper: dict, rank: int, intent: str) -> str:
    """Build a context block for one paper using only its relevant sentences."""
    entities = extract_query_entities(query)
    boosted_sections = INTENT_SECTION_BOOST.get(intent, INTENT_SECTION_BOOST["general"])

    lines = [
        f"{'=' * 60}",
        f"[Paper {rank}] {paper.get('title', 'Untitled')}",
        f"Category: {paper.get('category', '')}",
        f"Keywords: {paper.get('keywords', '')}",
        f"Novelty: {paper.get('novelty', '')}",
        f"{'=' * 60}",
        ""
    ]

    section_label_map = {
        "abstract":     "Abstract",
        "introduction": "Introduction",
        "conclusion":   "Conclusion",
        "limitations":  "Limitations",
        "novelty":      "Novelty (Extended)",
    }

    for section in ALL_SECTIONS:
        text = paper.get(section, "").strip()
        if not text:
            continue

        is_boosted = section in boosted_sections
        max_sents = MAX_SENTENCES_PER_SECTION.get(section, 8)

        extracted = extract_relevant_sentences(
            query=query,
            section_text=text,
            section_name=section,
            intent=intent,
            entities=entities,
            is_boosted_section=is_boosted,
            max_sentences=max_sents
        )

        if extracted:
            label = section_label_map.get(section, section.title())
            lines.append(f"{label}:")
            lines.append(extracted)
            lines.append("")

    return "\n".join(lines)


def build_full_context(query: str, top_papers: list[dict]) -> tuple[str, str]:
    """Build the full LLM context from all top re-ranked papers, one block per paper."""
    intent = detect_intent(query)

    blocks = []
    for rank, item in enumerate(top_papers, 1):
        paper = item["paper"]
        block = build_paper_context(query, paper, rank, intent)
        blocks.append(block)

    context_text = "\n\n".join(blocks)
    return context_text, intent
