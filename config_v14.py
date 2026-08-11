"""Central configuration for the retrieval pipeline. Tunable parameters live here."""

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

N_CLUSTERS_MIN = 10
N_CLUSTERS_MAX = 15

SAMPLE_PER_SOURCE = 150      # 150 x 7 = 1050 papers total

SIMILARITY_THRESHOLD = 0.35  # below this, classification falls back to the LLM

BROAD_CATEGORIES_FILE = "broad_categories.json"

ROUTER_CENTROID_WEIGHT = 0.6   # weight of question-vs-centroid similarity
ROUTER_DESC_WEIGHT     = 0.4   # weight of question-vs-description similarity
ROUTER_MIN_SCORE       = 0.18  # below this, search all categories
ROUTER_MARGIN          = 0.05  # categories within this of the best are also kept
ROUTER_MAX_CATEGORIES  = 3     # never route to more than this many categories

COLBERT_CACHE_FILE = "colbert_doc_embeddings.npy"
COLBERT_META_FILE  = "colbert_cache_meta.json"
