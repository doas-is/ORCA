# generate high-quality news search queries using few-shot prompts,
# then score + improve them if needed using a second model.
# all prompts and examples are inside the function so the model gets context.


# pip install openai
# pip install anthropic
import openai
from anthropic import Anthropic
import os
from src.utils import get_env_var

openai.api_key = get_env_var("OPENAI_API_KEY", "")

# model names taken from .env so you can switch easily
QUERY_MODEL = get_env_var("OPENAI_QUERY_MODEL")
SCORER_MODEL = get_env_var("OPENAI_SCORER_MODEL")
PROMPT_MIN_SCORE = int(get_env_var("PROMPT_MIN_SCORE"))

def _build_few_shot_prompt(domain, niche, num=8):
    example_input = {
        "domain": "renewable energy",
        "niche": "solar policy in north africa"
    }
    example_output = [
        "latest news renewable energy 2025",
        "latest solar policy updates north africa 2025 site:reuters.com OR site:bbc.com",
        "solar farm projects north africa 2025 financing",
        "north africa green hydrogen partnerships 2025 announcement",
        "government renewable energy regulation egypt 2025 site:gov.eg",
        "wind and solar capacity expansion north africa 2025"
    ]

    prompt = f"""
        you are a professional news query generator for strategic monitoring.

        goal:
        - produce short, precise search queries that return factual, recent news for a specified domain and niche.
        - prefer queries that will expose official announcements, press releases, industry publications, and mainstream media reporting.
        - avoid generic blog/opinion noise; prefer site:reuters.com OR site:bbc.com style qualifiers when relevant.
        - output should be a simple json list of query strings, nothing else.

        here's an example:
        input:
        domain: {example_input['domain']}
        niche: {example_input['niche']}

        example output:
        {example_output}

        now generate {num} queries for:
        domain: {domain}
        niche: {niche}

        requirements:
        - each query should be 3-8 words ideally.
        - include explicit year or 'recent' if relevant.
        - if suitable, include site: qualifiers for high credibility.
        - return only a json array (e.g. [\"query1\",\"query2\",...]).
            """
    return prompt

def _score_queries_with_model(queries, domain, niche):
    # we're gon ask another model to score each query 0-100 for precision, reliability and novelty
    prompt = f"you are a senior prompting engineer. domain: {domain}. niche: {niche}.\nscore each of these search queries 0-100 for expected precision and reliability (higher is better) and provide one-line feedback and an overall score for the list. respond as json: {{'scores': [[query,score,feedback], ...], 'overall': <0-100>}}\nqueries:\n" + "\n".join(queries)
    resp = openai.ChatCompletion.create(
        model=SCORER_MODEL, 
        messages=[{"role":"user","content":prompt}], 
        temperature=0.0 
        )
    text = resp.choices[0].message.content
    # try to parse numbers naively; if parsing fails, return default high scores
    results = []
    try:
        # model is asked to return json so try to parse it
        import json
        parsed = json.loads(text)
        for item in parsed.get("scores", []):
            q, score, feedback = item
            results.append({"query": q, "score": int(score), "feedback": feedback})
        overall = int(parsed.get("overall", 100))
    except Exception:
        # fallback: give 80 to all
        for q in queries:
            results.append({"query": q, "score": 80, "feedback": "score fallback"})
        overall = 80
    return results, overall

def _improve_query(query, domain, niche):
    # ask model to rewrite the query for higher precision
    prompt = f"as a professional search query generator, rewrite the following search query to be more precise and likely to return factual news for domain '{domain}' and niche '{niche}'. keep it short (max 8 words). original: {query}"
    resp = openai.ChatCompletion.create(
        model=QUERY_MODEL,
        messages=[{"role":"user","content":prompt}],
        temperature=0.2
    )
    text = resp.choices[0].message.content.strip()
    # cleanup
    return text.splitlines()[0].strip('"').strip()

def generate_queries(domain, niche, num_queries=8):
    prompt = _build_few_shot_prompt(domain, niche, num_queries)
    resp = openai.ChatCompletion.create(
        model=QUERY_MODEL,
        messages=[{"role":"user","content":prompt}],
        temperature=0.2
    )
    raw = resp.choices[0].message.content.strip()
    # try to parse json array first
    import json
    queries = []
    try:
        queries = json.loads(raw)
        queries = [q.strip() for q in queries if isinstance(q, str) and q.strip()]
    except Exception:
        # fallback: split by lines and clean
        queries = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]

    # score queries with the scorer model
    scored, overall = _score_queries_with_model(queries, domain, niche)

    # if any query is below threshold, try to improve it once
    improved = []
    for item in scored:
        q = item["query"]
        score = item["score"]
        if score < PROMPT_MIN_SCORE:
            improved_q = _improve_query(q, domain, niche)
            improved.append({"original": q, "improved": improved_q, "score_before": score})
        else:
            improved.append({"original": q, "improved": q, "score_before": score})
    final_queries = [it["improved"] for it in improved]
    # remove duplicates while preserving the original order of a list.
    seen = set()
    uniq = []
    for q in final_queries:
        if q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq
