"""Parses a paper PDF into structured fields using GROBID, plus custom
handling for the author list and the publication venue footer."""

import requests
from bs4 import BeautifulSoup
import json
import re
import fitz

GROBID_URL = "http://localhost:8070/api/processFulltextDocument"

def pdf_to_tei(pdf_path):
    with open(pdf_path, "rb") as f:
        r = requests.post(GROBID_URL, files={"input": f})
    return r.text


def extract_authors(soup):

    institution_keywords = {
        "university","institute","college","research","laboratory",
        "lab","school","center","centre","department","faculty",
        "corp","inc","ltd","company","kaist","iit","ai","cloud","mbzuai","neutrino","flux",
        "llm","survey","google","indian","mit","csail","usa","randomness"
    }

    authors = []
    analytic = soup.find("analytic")
    if not analytic:
        return authors

    metadata_seen = False
    no_metadata_streak = 0
    cutoff_streak = 5  # threshold for detecting references

    for author in analytic.find_all("author"):

        pers = author.find("persName")
        if not pers:
            continue

        forenames = pers.find_all("forename")
        surname = pers.find("surname")

        name_parts = [f.text.strip() for f in forenames if f.text]
        if surname:
            name_parts.append(surname.text.strip())

        full_name = " ".join(name_parts).strip()

        if not full_name:
            continue

        
        full_name = re.sub(r"[^\w\s\-]", "", full_name)

   
        lower_name = full_name.lower()
        if any(word in lower_name for word in institution_keywords):
            continue

        
        has_metadata = (
            author.find("email") is not None or
            author.find("affiliation") is not None or
            author.find("orgName") is not None or
            author.find("address") is not None
        )

        if has_metadata:
            metadata_seen = True
            no_metadata_streak = 0
        else:
            no_metadata_streak += 1

        authors.append(full_name)

        if metadata_seen and no_metadata_streak >= cutoff_streak:
            authors = authors[:-cutoff_streak]
            break

    return authors


def extract_publication_from_footer(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc[0]
    blocks = page.get_text("blocks")

    footer_y = None
    for b in blocks:
        if "Proceedings of" in b[4]:
            footer_y = b[1]
            break

    if footer_y is None:
        return ""

    selected = []
    seen = set()

    for b in blocks:
        x0, y0, x1, y1, text, *_ = b
        if abs(y0 - footer_y) < 40 and (x1 - x0) > 200:
            key = (round(x0), round(y0), round(x1), round(y1))
            if key not in seen:
                seen.add(key)
                selected.append((y0, text.strip()))

    selected.sort()
    return " ".join(t for _, t in selected)


def extract_all_sections(soup):
    sections = []
    body = soup.find("body")
    if not body:
        return sections

    idx = 0
    for div in body.find_all("div", recursive=False):
        head = div.find("head")
        if not head:
            continue

        heading = head.get_text(" ", strip=True).lower()
        text = div.get_text(" ", strip=True).replace(head.text, "").strip()

        if len(text) < 300 and not any(k in heading for k in ["conclusion", "limitation","limitations","conclusions"]):
            continue

        idx += 1
        sections.append({
            "section_index": idx,
            "heading": heading,
            "text": text,
            "length": len(text)
        })

    return sections



def extract_conclusion(soup, sections):

    has_conclusion = any(
        any(k in s["heading"] for k in ["conclusion", "conclusions"])
        for s in sections
    )

    if has_conclusion:
        for s in sections:
            if any(k in s["heading"] for k in ["conclusion", "conclusions"]):
                return s["text"]

    for s in sections:
        if "discussion" in s["heading"]:
            return s["text"]
            

    conclusion_prefix = None

    for div in soup.find_all("div"):
        head = div.find("head")
        if not head:
            continue

        heading_text = head.get_text(" ", strip=True).lower()

        if "conclusion" in heading_text:
            conclusion_prefix = head.get("n")
            break

    if conclusion_prefix:
        conclusion_prefix = conclusion_prefix.strip(".")

        collected = []

        for div in soup.find_all("div"):
            head = div.find("head")
            if not head:
                continue

            n_val = head.get("n", "")

            if n_val.startswith(conclusion_prefix + "."):
                text = div.get_text(" ", strip=True)

                text = text.replace(head.get_text(" ", strip=True), "").strip()

                if text:
                    collected.append(text)

        if collected:
            return " ".join(collected)

    candidates = []

    for tag in soup.find_all(["head", "cell"]):

        text = tag.get_text(" ", strip=True).lower()

        if "conclusion" in text:

            next_block = tag.find_next(["p", "cell"])

            if next_block:
                candidates.append(next_block.get_text(" ", strip=True))

    if candidates:
        return max(candidates, key=len)

    return ""

def parse_pdf(pdf_path):
    tei_xml = pdf_to_tei(pdf_path)
    soup = BeautifulSoup(tei_xml, "lxml-xml")

    title = soup.find("title").text.strip()
    authors = extract_authors(soup)

    abstract = soup.find("abstract").text.strip()
    abstract = re.split(r"\bcode\b", abstract, flags=re.IGNORECASE)[0].strip()

    sections = extract_all_sections(soup)
    introduction = next(
    (s["text"] for s in sections if "introduction" in s["heading"]),
    ""
    )


    limitations = next(
    (s["text"] for s in sections if any(k in s["heading"] for k in ["limitation", "limitations"])),
    ""
    )

    conclusion = extract_conclusion(soup, sections)

    references = [
        r.get_text(" ", strip=True)
        for r in soup.find_all("biblStruct")
        if r.find_parent("listBibl")
    ]

    publication_info = extract_publication_from_footer(pdf_path)

    data = {
        "title": title,
        "authors": ", ".join(authors),
        "abstract": abstract,
        "introduction": introduction,
        "limitations": limitations,
        "conclusion": conclusion,
        "publication_info": publication_info,
        "references": "\n".join(references)
    }

    return data, tei_xml
