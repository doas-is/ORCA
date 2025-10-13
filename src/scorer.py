# compute bias, reliability, relevance, freshness, and strategic score, 
# domain authority (tld), commercial intent, named entity density, technical term density (based on domain/niche keywords), novelty vs previous headlines.

from textblob import TextBlob
from datetime import datetime
from src.utils import safe_truncate
import re
from collections import Counter
from urllib.parse import urlparse
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("RAPIDAPI_KEY")
API_HOST = os.getenv("RAPIDAPI_HOST")
MODEL_URL = os.getenv("MODEL_URL")

def compute_bias_score(text):
    # abs(polarity)= bias
    try:
        polarity = TextBlob(text).sentiment.polarity
    except:
        polarity = 0.0
    return min(abs(polarity), 1.0)

def compute_reliability_score(text, url):
    # longer, structured text -> higher reliability
    length_score = min(len(text) / 1000.0, 1.0)
    # tld heuristic: .gov/.edu higher
    try:
        hostname = urlparse(url).hostname or ""
        if hostname.endswith(".gov") or hostname.endswith(".edu"):
            tld_score = 1.0
        elif hostname.endswith(".org"):
            tld_score = 0.85
        else:
            tld_score = 0.7
    except:
        tld_score = 0.6
    return round(0.6 * length_score + 0.4 * tld_score, 3)

def compute_freshness_score(pub_date_str):
    if not pub_date_str:
        return 0.5
    try:
        # parse basic iso or yyyy-mm-dd
        pub_date = datetime.fromisoformat(pub_date_str)
        delta_days = (datetime.utcnow() - pub_date).days
        return max(0.0, 1.0 - min(delta_days, 30)/30.0)
    except:
        return 0.5

def named_entity_density(text):
    """The function tries to measure how much of the text consists of named entities (things like people, places, organizations)
      by counting capitalized word sequences (e.g., New York, Barack Obama, Google)"""
    if not text:
        return 0.0
    tokens = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*", text)
    den = len(tokens) / max(1, len(text.split()))
    return min(den, 1.0)


def generate_keywords(domain, niche):
    # Generate a list of technical keywords dynamically from domain and niche
    prompt = (
        f"""You are assisting in a strategic intelligence analysis project.
        The goal is to evaluate how professional, relevant, and insightful a given article is 
        within its field, and how valuable it might be for technological, competitive, and strategic watch (veille stratégique, technologique et concurrentielle). 
        To support this, generate 15 to 20 precise technical keywords that represent the main concepts, tools, methods, or innovations 
        commonly associated with the domain '{domain}' and the niche '{niche}'. 
        The keywords should serve as a reference map for detecting how strongly an article relates to this professional field. 
        Return only a simple comma-separated list of keywords — no explanations or extra text.
        
        Example:
        Domain: Artificial Intelligence
        Niche: Natural Language Processing
        Expected output: machine learning, neural networks, transformers, text mining, tokenization, sentiment analysis, 
        BERT, GPT, attention mechanism, deep learning, data annotation, language modeling, embeddings, corpus analysis, 
        contextual representation, model fine-tuning, AI ethics, linguistic feature extraction, zero-shot learning, prompt engineering.
        """
    )

    payload = {"text": prompt}
    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": API_HOST,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(MODEL_URL, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()

        # Extract keywords safely from response
        text = data.get("result", "")
        keywords = [kw.strip().lower() for kw in re.split(r"[,;]", text) if kw.strip()]
        return keywords
    except Exception as e:
        print("Keyword generation failed:", e)
        return (domain + " " + niche).lower().split()  # fallback

def technical_term_density(text, domain, niche):
    corpus = generate_keywords(domain, niche)  # dynamically generated keywords
    words = re.findall(r"\w+", text.lower())
    if not words:
        return 0.0
    c = Counter(words)
    hits = sum(c[w] for w in corpus if w in c)
    return min(hits / max(1, len(words)), 1.0)


def commercial_intent_score(text):
    # presence of pricing, buy, demo, sign up words -> higher commercial intent
    keywords = ["pricing", "price", "buy", "for sale", "subscribe", "signup", "demo", "trial", "launch", "pre-order", "order", "discount", "sale"]
    text_l = text.lower()
    hits = sum(1 for k in keywords if k in text_l)
    return min(hits / 3.0, 1.0)

def novelty_score(title, existing_titles):
    # measure how original a given title is compared to other existing titles.
    if not title:
        return 0.5
    tset = set(re.findall(r"\w+", title.lower())) # extracts seperate words from the title
    max_sim = 0.0
    for other in existing_titles:
        oset = set(re.findall(r"\w+", other.lower()))
        inter = tset & oset
        union = tset | oset if (tset | oset) else set(["a"]) #uses a dummy set {"a"} to avoid division by zero
        sim = len(inter)/len(union)
        if sim > max_sim:
            max_sim = sim
    return round(1.0 - max_sim, 3)

def compute_strategic_score(text, title, url, domain, niche, existing_titles):
    # combine signals into a strategic score (0..1)
    bias = compute_bias_score(text)
    reliability = compute_reliability_score(text, url)
    freshness = 0.5  # assume neutral if no date provided
    # compute other heuristics
    named = named_entity_density(text)
    tech = technical_term_density(text, domain, niche)
    commercial = commercial_intent_score(text)
    novelty = novelty_score(title, existing_titles)
    # weights tuned to favor relevance/commercial novelty
    score = (0.15 * reliability +
             0.10 * (1 - bias) +
             0.20 * tech +
             0.25 * commercial +
             0.15 * novelty +
             0.15 * named)
    # normalize
    score = max(0.0, min(score, 1.0))
    return {
        "bias_score": round(bias, 3),
        "reliability_score": round(reliability, 3),
        "technical_density": round(tech, 3),
        "commercial_intent": round(commercial, 3),
        "named_entity_density": round(named, 3),
        "originality_score": round(novelty, 3),
        "strategic_score": round(score, 3)
    }
