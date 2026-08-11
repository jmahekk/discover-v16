"""Downloads a paper's PDF from its URL, skipping known paywalled domains."""

import requests
import os
from urllib.parse import urlparse

PAYWALLED_DOMAINS = [
    "dl.acm.org",
    "sciencedirect.com",
    "springer.com",
    "ieeexplore.ieee.org"
]

def normalize_pdf_url(url: str) -> str:
    url = url.strip()

    # arXiv abstract -> PDF
    if "arxiv.org/abs/" in url:
        paper_id = url.split("/abs/")[1]
        return f"https://arxiv.org/pdf/{paper_id}.pdf"

    # arXiv HTML -> PDF
    if "arxiv.org/html/" in url:
        paper_id = url.split("/html/")[1]
        return f"https://arxiv.org/pdf/{paper_id}.pdf"

    # ACL Anthology landing page -> PDF
    if "aclanthology.org" in url and not url.endswith(".pdf"):
        return url.rstrip("/") + ".pdf"

    return url


def is_paywalled(url: str) -> bool:
    domain = urlparse(url).netloc
    return any(p in domain for p in PAYWALLED_DOMAINS)


def download_pdf(url, out_dir, idx):
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"paper_{idx:03}.pdf")

    original_url = url
    url = normalize_pdf_url(url)

    if is_paywalled(url):
        return None, "Paywalled domain"

    try:
        r = requests.get(
            url,
            timeout=30,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        if r.status_code != 200:
            return None, f"HTTP Error {r.status_code}"

        content_type = r.headers.get("Content-Type", "").lower()
        if "application/pdf" not in content_type:
            return None, "Not a PDF content"

        with open(pdf_path, "wb") as f:
            f.write(r.content)

        return pdf_path, None  

    except Exception as e:
        return None, str(e)
