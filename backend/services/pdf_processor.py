import re
import requests
import pdfplumber
import spacy
import xml.etree.ElementTree as ET
from sklearn.feature_extraction.text import TfidfVectorizer


class PdfProcessor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

    def pdf_to_text(self, uploaded_file):
        if uploaded_file is None:
            raise ValueError("No file uploaded")

        uploaded_file.stream.seek(0)

        with pdfplumber.open(uploaded_file) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)

        full_text = "\n\n".join(pages)

        return {
            "page_count": len(pages),
            "text": full_text,
        }

    def extract_information(self, pdf_text):
        extracted = {
            "keywords": self._extract_keywords(pdf_text),
            "claims": self._extract_claims(pdf_text),
            "facts": self._extract_facts(pdf_text),
            "definitions": self._extract_definitions(pdf_text),
        }
        return extracted

    def _extract_keywords(self, text):
        vectorizer = TfidfVectorizer(max_features=20)
        vectorizer.fit([text])
        return vectorizer.get_feature_names_out().tolist()

    def _extract_claims(self, text):
        doc = self.nlp(text)
        claims = []

        for sent in doc.sents:
            has_verb = any(token.pos_ == "VERB" for token in sent)
            if has_verb and len(sent) > 5:
                claims.append({
                    "text": str(sent),
                    "confidence": 0.8
                })

        return claims[:10]

    def _extract_facts(self, text):
        doc = self.nlp(text)
        facts = []

        for ent in doc.ents:
            if ent.label_ in ["DATE", "CARDINAL", "PERCENT"]:
                facts.append({
                    "value": ent.text,
                    "type": ent.label_
                })

        return facts

    def _extract_definitions(self, text):
        patterns = [
            r'(\w+)\s+is\s+defined\s+as\s+([^.]+)',
            r'(\w+):\s+([^.]+)'
        ]

        definitions = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for term, definition in matches:
                definitions.append({
                    "term": term,
                    "definition": definition.strip()
                })

        return definitions

    def search_all_sources(self, query):
        findings = {
            "query": query,
            "results": [],
            "sources": {
                "crossref": [],
                "pubmed": [],
                "wikipedia": [],
                "arxiv": []
            }
        }

        self._search_crossref(query.values(), findings)
        self._search_pubmed(query.values(), findings)
        self._search_wikipedia(query.values(), findings)
        self._search_arxiv(query.values(), findings)

        return findings

    def _search_crossref(self, query, findings):
        url = "https://api.crossref.org/works"
        params = {
            "query.title": query,
            "rows": 5,
            "select": "title,author,issued,DOI,URL"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                findings["sources"]["crossref"] = [{"error": "CrossRef request failed"}]
                return

            data = response.json()
            items = data.get("message", {}).get("items", [])

            for item in items:
                title = item.get("title", [""])[0]
                year = item.get("issued", {}).get("date-parts", [[None]])[0][0]
                doi = item.get("DOI")
                url = item.get("URL")

                entry = {
                    "source": "crossref",
                    "title": title,
                    "year": year,
                    "doi": doi,
                    "url": url,
                }

                findings["sources"]["crossref"].append(entry)
                findings["results"].append(entry)

        except Exception as exc:
            findings["sources"]["crossref"] = [{"error": str(exc)}]

    def _search_pubmed(self, query, findings):
        pubmed_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": 5,
            "retmode": "json",
            "sort": "relevance"
        }

        try:
            response = requests.get(pubmed_url, params=params, timeout=10)
            if response.status_code != 200:
                findings["sources"]["pubmed"] = [{"error": "PubMed request failed"}]
                return

            data = response.json()
            ids = data.get("esearchresult", {}).get("idlist", [])

            if not ids:
                findings["sources"]["pubmed"] = []
                return

            summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            summary_params = {
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "json"
            }

            summary_response = requests.get(summary_url, params=summary_params, timeout=10)
            if summary_response.status_code != 200:
                findings["sources"]["pubmed"] = [{"error": "PubMed summary request failed"}]
                return

            summary_data = summary_response.json()
            result = summary_data.get("result", {})

            for item_id, item in result.items():
                if item_id == "uids":
                    continue

                entry = {
                    "source": "pubmed",
                    "title": item.get("title"),
                    "year": item.get("pubdate", "")[:4] if item.get("pubdate") else None,
                    "authors": item.get("authors", []),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{item_id}/",
                }

                findings["sources"]["pubmed"].append(entry)
                findings["results"].append(entry)

        except Exception as exc:
            findings["sources"]["pubmed"] = [{"error": str(exc)}]

    def _search_wikipedia(self, query, findings):
        wiki_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
            "srlimit": 5
        }

        try:
            response = requests.get(wiki_url, params=params, timeout=10)
            if response.status_code != 200:
                findings["sources"]["wikipedia"] = [{"error": "Wikipedia request failed"}]
                return

            data = response.json()
            items = data.get("query", {}).get("search", [])

            for item in items:
                title = item.get("title")
                entry = {
                    "source": "wikipedia",
                    "title": title,
                    "snippet": item.get("snippet"),
                    "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                }

                findings["sources"]["wikipedia"].append(entry)
                findings["results"].append(entry)

        except Exception as exc:
            findings["sources"]["wikipedia"] = [{"error": str(exc)}]

    def _search_arxiv(self, query, findings):
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": 5,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                findings["sources"]["arxiv"] = [{"error": "arXiv request failed"}]
                return

            root = ET.fromstring(response.content)

            ns = {
                "a": "http://www.w3.org/2005/Atom"
            }

            entries = root.findall("a:entry", ns)

            for entry in entries:
                title = entry.find("a:title", ns)
                summary = entry.find("a:summary", ns)
                published = entry.find("a:published", ns)
                id_tag = entry.find("a:id", ns)

                item = {
                    "source": "arxiv",
                    "title": (title.text or "").strip().replace("\n", " "),
                    "summary": (summary.text or "").strip()[:300],
                    "published": (published.text or "")[:10] if published is not None else None,
                    "url": id_tag.text if id_tag is not None else None
                }

                findings["sources"]["arxiv"].append(item)
                findings["results"].append(item)

        except Exception as exc:
            findings["sources"]["arxiv"] = [{"error": str(exc)}]

    def compare_with_recent_research(self, extracted_info):
        findings = {
            "outdated_claims": [],
            "unverified_facts": [],
            "missing_recent_topics": []
        }

        for claim in extracted_info["claims"]:
            query = claim["text"]
            search_results = self.search_all_sources(query)

            if not search_results["results"]:
                findings["outdated_claims"].append({
                    "claim": query,
                    "reason": "No recent evidence found in the selected sources"
                })

        return findings