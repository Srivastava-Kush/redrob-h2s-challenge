#: D

import csv
import io
import json

import streamlit as st

import rank  # the real ranker — same code path as the full submission

MAX_CANDIDATES = 100

st.set_page_config(page_title="Redrob Candidate Ranker — Sandbox", layout="wide")
st.title("Redrob Candidate Ranker — Sandbox")
st.caption(
    "Runs the exact `rank.py` scoring pipeline (evidence-based fit × JD policy "
    "× consistency checks × behavioral signals) on a sample of up to "
    f"{MAX_CANDIDATES} candidates. CPU-only, stdlib scoring, no network calls."
)

# input
uploaded = st.file_uploader(
    f"Upload a candidate sample (.jsonl or .json, ≤ {MAX_CANDIDATES} candidates)",
    type=["jsonl", "json"],
)


def load_candidates(file) -> list:
    raw = file.getvalue().decode("utf-8")
    stripped = raw.lstrip()
    if stripped.startswith("["):          # pretty-printed JSON array
        return json.loads(stripped)
    return [json.loads(l) for l in raw.splitlines() if l.strip()]  # JSONL


if uploaded is not None:
    candidates = load_candidates(uploaded)
    source = uploaded.name
else:
    try:
        with open("data/sample_candidates.json", encoding="utf-8") as f:
            candidates = json.load(f)
        source = "bundled sample_candidates.json (first 50 candidates of the pool)"
    except FileNotFoundError:
        st.warning("No file uploaded and no bundled sample found.")
        st.stop()

if len(candidates) > MAX_CANDIDATES:
    st.info(f"Input has {len(candidates)} candidates; using the first {MAX_CANDIDATES}.")
    candidates = candidates[:MAX_CANDIDATES]

st.write(f"**Input:** {source} — {len(candidates)} candidates")

#rank
if st.button("Run ranking", type="primary") or uploaded is None:
    scored = []
    for c in candidates:
        s, matched, pen, notes, flags = rank.score_candidate(c)
        scored.append((s, c["candidate_id"], c, matched, pen, notes))
    scored.sort(key=lambda t: (-t[0], t[1]))

    smax = scored[0][0] if scored and scored[0][0] > 0 else 1.0
    rows = []
    for i, (s, cid, c, matched, pen, notes) in enumerate(scored, 1):
        rows.append({
            "candidate_id": cid,
            "rank": i,
            "score": round(s / smax, 6),
            "reasoning": rank.make_reasoning(c, matched, pen, notes, i),
        })

    st.subheader("Ranked output")
    show = [{
        **r,
        "title": next(x for x in candidates if x["candidate_id"] == r["candidate_id"])["profile"]["current_title"],
        "yoe": next(x for x in candidates if x["candidate_id"] == r["candidate_id"])["profile"]["years_of_experience"],
    } for r in rows]
    st.dataframe(
        show,
        column_order=["rank", "candidate_id", "score", "title", "yoe", "reasoning"],
        width="stretch",
        hide_index=True,
    )

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["candidate_id", "rank", "score", "reasoning"])
    w.writeheader()
    w.writerows(rows)
    st.download_button(
        "Download ranked CSV (submission format)",
        buf.getvalue().encode("utf-8"),
        file_name="sandbox_ranking.csv",
        mime="text/csv",
    )

    with st.expander("Why these ranks? (per-candidate breakdown, top 10)"):
        for r in rows[:10]:
            st.markdown(f"**#{r['rank']} — {r['candidate_id']}** (score {r['score']})")
            st.write(r["reasoning"])
