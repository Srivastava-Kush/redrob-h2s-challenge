
import argparse
import csv
import json
import math
import re
import sys
from datetime import date, datetime




def _rx(words):
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(words) + r")(?![a-z0-9])")

CONCEPTS = {
    # The four "absolutely need" pillars from the JD.
    "retrieval_ranking": (3.0, _rx([
        "retrieval", "ranking", "re[- ]?rank[a-z0-9_]*", "learning[- ]to[- ]rank",
        "ltr", "recommendation[a-z0-9_]*", "recommender[a-z0-9_]*", "personali[sz]ation",
        "search relevance", "semantic search", "hybrid search", "bm25",
        "information retrieval", "query understanding", "candidate matching",
        "matching engine", "search engine", "search infrastructure",
        "relevance", "two[- ]tower", "collaborative filtering",
    ])),
    "embeddings": (2.5, _rx([
        "embedding[a-z0-9_]*", "sentence[- ]transformers?", "bge", "e5",
        "dense retrieval", "vector representation[a-z0-9_]*", "representation learning",
        "siamese", "bi[- ]encoder", "cross[- ]encoder",
    ])),
    "vector_infra": (2.5, _rx([
        "vector (?:database[a-z0-9_]*|db[a-z0-9_]*|search|index[a-z0-9_]*|store[a-z0-9_]*)", "faiss",
        "pinecone", "weaviate", "qdrant", "milvus", "opensearch",
        "elasticsearch", "elastic search", "vespa", "annoy", "hnsw",
        "approximate nearest neighbo[a-z0-9_]*", "ann index[a-z0-9_]*", "pgvector", "solr",
        "lucene",
    ])),
    "eval_frameworks": (2.5, _rx([
        "ndcg", "mrr", "mean reciprocal rank", "map@[0-9]+",
        "mean average precision", "a/b test[a-z0-9_]*", "ab test[a-z0-9_]*",
        "offline (?:eval[a-z0-9_]*|metric[a-z0-9_]*|benchmark[a-z0-9_]*)", "online metric[a-z0-9_]*",
        "eval(?:uation)? (?:framework[a-z0-9_]*|harness[a-z0-9_]*|pipeline[a-z0-9_]*|suite[a-z0-9_]*|infra[a-z0-9_]*)",
        "relevance judgment[a-z0-9_]*", "golden set[a-z0-9_]*", "interleaving",
        "recall@[0-9]+", "precision@[0-9]+", "click[- ]through",
    ])),
    # Nice-to-haves / supporting evidence.
    "llm_work": (1.5, _rx([
        "llm[a-z0-9_]*", "large language model[a-z0-9_]*", "fine[- ]?tun[a-z0-9_]*", "lora",
        "qlora", "peft", "rag", "retrieval[- ]augmented", "prompt[a-z0-9_]*",
        "gpt[- ]?[0-9]", "transformer[a-z0-9_]*", "bert", "instruction[- ]tun[a-z0-9_]*",
        "distillation", "quantization", "gguf", "vllm",
    ])),
    "nlp_ir": (1.2, _rx([
        "nlp", "natural language", "text classification", "named entity",
        "ner", "tokeni[sz][a-z0-9_]*", "topic model[a-z0-9_]*", "tf[- ]?idf",
        "word2vec", "glove", "text mining", "language model[a-z0-9_]*",
        "spacy", "question answering",
    ])),
    "ml_production": (1.5, _rx([
        "(?:deploy[a-z0-9_]*|shipp?[a-z0-9_]*|launch[a-z0-9_]*|serv[a-z0-9_]*|product[a-z0-9_]*) .{0,60}(?:model[a-z0-9_]*|ml |machine learning|pipeline[a-z0-9_]*)",
        "model[a-z0-9_]* (?:in|to|into) production", "ml (?:pipeline[a-z0-9_]*|platform[a-z0-9_]*|infra[a-z0-9_]*|system[a-z0-9_]*|service[a-z0-9_]*)",
        "mlops", "model serving", "inference (?:service[a-z0-9_]*|latency|optimization|at scale)",
        "feature store[a-z0-9_]*", "real[- ]time inference", "model monitoring",
        "drift", "retrain[a-z0-9_]*", "xgboost", "lightgbm", "pytorch", "tensorflow",
        "scikit[- ]learn", "sklearn",
    ])),
    "scale_systems": (0.8, _rx([
        "at scale", "millions of (?:users|queries|requests|documents|records|candidates)",
        "low[- ]latency", "high[- ]throughput", "distributed system[a-z0-9_]*",
        "kafka", "spark", "latency", "qps", "horizontally",
    ])),
    "python": (0.6, _rx(["python", "pytest", "fastapi", "django", "flask"])),
    "opensource": (0.6, _rx([
        "open[- ]source", "github", "maintainer", "contributor[a-z0-9_]*",
        "published (?:paper[a-z0-9_]*|talk[a-z0-9_]*)", "conference talk[a-z0-9_]*", "pypi",
        "blog[a-z0-9_]*", "kaggle",
    ])),
}

# Negative-domain vocabulary (CV/speech/robotics without NLP/IR).
CV_SPEECH_RX = _rx([
    "computer vision", "image (?:classification|segmentation|detection)",
    "object detection", "opencv", "yolo[a-z0-9_]*", "speech recognition", "asr",
    "text[- ]to[- ]speech", "tts", "robotics", "slam", "autonomous (?:driving|vehicle[a-z0-9_]*)",
    "lidar", "3d reconstruction", "video analytics",
])

RESEARCH_RX = _rx([
    "research scientist", "research intern", "postdoc[a-z0-9_]*", "phd researcher",
    "research fellow", "academic", "professor", "lab\b",
])

CONSULTING_COS = {
    "tcs", "tata consultancy services", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "tech mahindra", "mindtree", "ltimindtree",
    "hcl", "hcltech", "mphasis", "ibm consulting", "deloitte", "genpact",
}

ENGINEER_TITLE_RX = re.compile(
    r"engineer|developer|scientist|architect|programmer|sde|swe|ml |mle|"
    r"machine learning|data science|ai |technical lead|tech lead|cto|"
    r"member of technical staff", re.I)

NON_IC_TITLE_RX = re.compile(
    r"\b(marketing|sales|account(?:ant|ing)?|hr |human resources|recruiter|"
    r"customer support|operations manager|business analyst|project manager|"
    r"product manager|graphic designer|finance|civil|mechanical|"
    r"office|admin)\b", re.I)

TIER1_CITIES = ("pune", "noida", "delhi", "gurgaon", "gurugram", "ghaziabad",
                "mumbai", "hyderabad", "bangalore", "bengaluru", "chennai",
                "kolkata", "faridabad", "new delhi")
PREFERRED_CITIES = ("pune", "noida", "delhi", "gurgaon", "gurugram",
                    "ghaziabad", "new delhi", "faridabad")

NOW = date(2026, 6, 1)  # dataset epoch (last_active dates run into mid-2026)


def parse_date(s):
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def months_between(d1, d2):
    return (d2.year - d1.year) * 12 + d2.month - d1.month



# Honeypot / consistency checks

def consistency_flags(c):
    """Return list of inconsistency flags. Any flag => candidate is suspect."""
    flags = []
    prof = c.get("profile", {})
    yoe = prof.get("years_of_experience") or 0
    career = c.get("career_history", []) or []
    skills = c.get("skills", []) or []

    career_months = 0
    earliest = None
    for job in career:
        sd, ed = parse_date(job.get("start_date") or ""), parse_date(job.get("end_date") or "") or NOW
        dur = job.get("duration_months") or 0
        career_months = max(career_months, 0)
        if sd:
            if earliest is None or sd < earliest:
                earliest = sd
            # stated duration vs date math
            actual = months_between(sd, ed)
            if abs(actual - dur) > 18:
                flags.append("job duration_months contradicts its start/end dates")
            if sd > NOW:
                flags.append("job starts in the future")
        career_months += dur

    # YoE vs dated career history (both directions are honeypot tells)
    span_m = months_between(earliest, NOW) if earliest else 0
    if earliest:
        if yoe > span_m / 12.0 + 2.5:
            flags.append("claimed years_of_experience exceeds entire dated career span")
        if yoe + 2.5 < career_months / 12.0:
            flags.append("stated years_of_experience far below documented employment history")

    # NOTE: skill duration_months in this dataset is noisy (7%+ of the pool
    # has a skill duration exceeding their dated career, and 760 candidates
    # "predate" a technology's existence) — those are NOT honeypot tells and
    # are deliberately not flagged here. The three date-math checks above and
    # the expert-with-zero-use check below each hit ~20-25 candidates,
    # matching the stated ~80 honeypots.
    expert_zero = 0
    for s in skills:
        if s.get("proficiency") == "expert" and (s.get("duration_months") or 0) <= 3:
            expert_zero += 1
    if expert_zero >= 3:
        flags.append("multiple 'expert' skills with ~zero months of use")
    return flags


# Core scoring

def score_candidate(c):
    prof = c.get("profile", {})
    career = c.get("career_history", []) or []
    skills = c.get("skills", []) or []
    sig = c.get("redrob_signals", {}) or {}

    yoe = float(prof.get("years_of_experience") or 0)
    cur_title = prof.get("current_title") or ""

    # text pools
    work_text = " ".join(
        f"{j.get('title','')} {j.get('description','')}" for j in career).lower()
    profile_text = f"{prof.get('headline','')} {prof.get('summary','')}".lower()
    skills_text = " ".join(s.get("name", "") for s in skills).lower()

    # concept evidence 
    fit = 0.0
    matched = {}
    core_work_hits = 0
    for name, (w, rx) in CONCEPTS.items():
        in_work = len(set(rx.findall(work_text)))
        in_prof = len(set(rx.findall(profile_text)))
        in_skill = len(set(rx.findall(skills_text)))
        pts = 0.0
        if in_work:
            pts += w * min(in_work, 3) * 1.0          # strongest: described in actual jobs
        if in_prof:
            pts += w * min(in_prof, 2) * 0.45         # summary/headline: medium
        if in_skill:
            # skills list only counts if corroborated anywhere in prose
            corro = 1.0 if (in_work or in_prof) else 0.15
            pts += w * min(in_skill, 3) * 0.25 * corro
        if pts:
            matched[name] = (pts, in_work, in_prof, in_skill)
            if in_work and name in ("retrieval_ranking", "embeddings",
                                    "vector_infra", "eval_frameworks"):
                core_work_hits += 1
        fit += pts

    # Bonus: multiple core pillars evidenced in real work history.
    fit *= (1.0 + 0.18 * core_work_hits)

    #experience band (JD: 5-9, ideal 6-8, soft outside)
    if 5 <= yoe <= 9:
        exp = 1.0 if 6 <= yoe <= 8 else 0.92
    elif 4 <= yoe < 5 or 9 < yoe <= 11:
        exp = 0.75
    elif 3 <= yoe < 4 or 11 < yoe <= 14:
        exp = 0.5
    else:
        exp = 0.25
    fit *= (0.55 + 0.45 * exp)

    # JD policy layer (disqualifiers / penalties)
    penalties = []

    # Non-engineering current role: hard down-weight (the Marketing Manager trap)
    if NON_IC_TITLE_RX.search(cur_title) and not ENGINEER_TITLE_RX.search(cur_title):
        fit *= 0.05
        penalties.append("current role is non-engineering")
    elif not ENGINEER_TITLE_RX.search(cur_title):
        fit *= 0.45
        penalties.append("current title is not clearly an engineering role")

    # Consulting-only career
    cos = [(j.get("company") or "").lower() for j in career]
    if cos and all(any(k in co for k in CONSULTING_COS) for co in cos):
        fit *= 0.3
        penalties.append("entire career at consulting/services firms")

    # Research-only career without production signals
    titles_all = " ".join(j.get("title", "") for j in career).lower()
    if RESEARCH_RX.search(titles_all):
        research_jobs = sum(1 for j in career if RESEARCH_RX.search((j.get("title") or "").lower()))
        if research_jobs == len(career) and "ml_production" not in matched:
            fit *= 0.15
            penalties.append("research-only career with no production deployment")

    # Title-chaser / job hopper: many jobs with short median tenure
    if len(career) >= 4:
        durs = sorted((j.get("duration_months") or 0) for j in career[:-0] or career)
        med = durs[len(durs) // 2]
        if med <= 18:
            fit *= 0.55
            penalties.append("frequent job switching (median tenure <= 18 months)")

    # Manager/architect who likely stopped coding
    if re.search(r"\b(architect|head of|director|vp|engineering manager)\b", cur_title, re.I):
        fit *= 0.5
        penalties.append("recent role looks non-hands-on")

    # CV/speech/robotics-dominant without NLP/IR
    cv_hits = len(set(CV_SPEECH_RX.findall(work_text + " " + profile_text)))
    nlp_signal = matched.get("nlp_ir", (0,))[0] + matched.get("retrieval_ranking", (0,))[0]
    if cv_hits >= 3 and nlp_signal < 1.0:
        fit *= 0.35
        penalties.append("primarily CV/speech/robotics with little NLP/IR exposure")

    # Keyword stuffing: rich AI skill list, zero prose corroboration
    ai_in_skills = sum(1 for n in ("llm_work", "embeddings", "vector_infra", "retrieval_ranking")
                       if matched.get(n) and matched[n][3] and not (matched[n][1] or matched[n][2]))
    if ai_in_skills >= 2:
        fit *= 0.4
        penalties.append("AI keywords in skills list not supported by work history")

    # consistency / honeypot 
    flags = consistency_flags(c)
    if flags:
        fit *= 0.02  # effectively eliminate
        penalties.append("profile internally inconsistent: " + flags[0])

    # behavioral multiplier (0.45 .. 1.15)
    behav = 1.0
    notes = []
    la = parse_date(sig.get("last_active_date") or "")
    if la:
        days = (NOW - la).days
        if days > 180:
            behav *= 0.55; notes.append(f"inactive for {days // 30} months")
        elif days > 90:
            behav *= 0.8; notes.append(f"last active ~{days // 30} months ago")
        elif days <= 21:
            behav *= 1.06
    rr = sig.get("recruiter_response_rate")
    if rr is not None:
        if rr < 0.15:
            behav *= 0.6; notes.append(f"{int(rr * 100)}% recruiter response rate")
        elif rr < 0.4:
            behav *= 0.85
        else:
            behav *= 1.05
    if sig.get("open_to_work_flag"):
        behav *= 1.07
    icr = sig.get("interview_completion_rate")
    if icr is not None and icr < 0.5:
        behav *= 0.75; notes.append("low interview completion rate")
    npd = sig.get("notice_period_days")
    if npd is not None:
        if npd <= 30:
            behav *= 1.05
        elif npd >= 75:
            behav *= 0.85; notes.append(f"{npd}-day notice period")
    gh = sig.get("github_activity_score", -1)
    if gh is not None and gh >= 60:
        behav *= 1.05

    # location
    loc = (prof.get("location") or "").lower()
    country = (prof.get("country") or "").lower()
    reloc = bool(sig.get("willing_to_relocate"))
    if country == "india":
        if any(city in loc for city in PREFERRED_CITIES):
            locm = 1.1
        elif any(city in loc for city in TIER1_CITIES):
            locm = 1.05
        else:
            locm = 1.0 if reloc else 0.85
            if not reloc:
                notes.append("outside Tier-1 cities and not willing to relocate")
    else:
        locm = 0.55 if reloc else 0.3   # no visa sponsorship
        notes.append("based outside India (no visa sponsorship)")

    final = fit * behav * locm
    return final, matched, penalties, notes, flags



CONCEPT_LABEL = {
    "retrieval_ranking": "search/ranking and recommendation work",
    "embeddings": "embeddings-based retrieval",
    "vector_infra": "vector/hybrid search infrastructure",
    "eval_frameworks": "ranking-evaluation experience (offline metrics/AB testing)",
    "llm_work": "LLM/fine-tuning exposure",
    "nlp_ir": "NLP/IR background",
    "ml_production": "production ML deployment",
    "scale_systems": "large-scale systems experience",
}


def make_reasoning(c, matched, penalties, notes, rank):
    prof = c.get("profile", {})
    yoe = prof.get("years_of_experience")
    title = prof.get("current_title", "candidate")
    company = prof.get("current_company", "")
    strengths = [CONCEPT_LABEL[k] for k, v in sorted(
        matched.items(), key=lambda kv: -kv[1][0]) if k in CONCEPT_LABEL and v[1] >= 1][:3]
    openers = [
        f"{title} at {company} with {yoe:g} yrs",
        f"{yoe:g} yrs of experience, currently {title} at {company}",
        f"Currently {title} ({company}), {yoe:g} yrs total",
    ]
    s = openers[rank % 3]
    if strengths:
        s += "; work history shows " + (", ".join(strengths[:-1]) + " and " + strengths[-1]
                                        if len(strengths) > 1 else strengths[0])
    else:
        s += "; adjacent technical profile rather than a direct retrieval/ranking match"
    s += "."
    concerns = (notes + penalties)[:2]
    if concerns:
        s += " Concern: " + "; ".join(concerns) + "."
    elif rank <= 10:
        loc = prof.get("location", "")
        s += f" Strong engagement signals and {loc} location align with the JD's logistics."
    return s



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default="./data/candidates.jsonl")
    ap.add_argument("--out", default="./submission.csv")
    args = ap.parse_args()

    scored = []
    n = 0
    with open(args.candidates, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            n += 1
            s, matched, pen, notes, flags = score_candidate(c)
            if s > 0:
                scored.append((s, c["candidate_id"], c, matched, pen, notes))
            if n % 20000 == 0:
                print(f"  processed {n} candidates...", file=sys.stderr)

    # deterministic: score desc, candidate_id asc
    scored.sort(key=lambda t: (-t[0], t[1]))
    top = scored[:100]

    smax = top[0][0] if top else 1.0
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["candidate_id", "rank", "score", "reasoning"])
        for i, (s, cid, c, matched, pen, notes) in enumerate(top, 1):
            w.writerow([cid, i, round(s / smax, 6),
                        make_reasoning(c, matched, pen, notes, i)])

    print(f"Done. {n} candidates scored; wrote top {len(top)} to {args.out}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
