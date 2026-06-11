# Redrob Hackathon — Intelligent Candidate Discovery & Ranking

Ranks the 100,000-candidate pool against the **Senior AI Engineer — Founding Team** JD
and produces the top-100 submission CSV.

## Reproduce

```bash
python rank.py --candidates ./data/candidates.jsonl --out ./submission.csv
python data/validate_submission.py submission.csv
```

- **Dependencies:** none — Python 3.10+ standard library only.
- **Runtime:** ~2.5–4 min single-threaded on a laptop CPU (within the 5-min budget).
- **Memory:** well under 16 GB (streaming line-by-line over the JSONL).
- **Network:** none. No LLM calls, no GPU, no pre-computation step.

## Sandbox / demo (submission_spec §10.5)

[app.py](app.py) is a Streamlit app that runs the **exact same** `rank.py` code
path on a sample of ≤100 candidates (upload a `.jsonl`/`.json`, or it falls back
to the bundled `data/sample_candidates.json`) and produces a downloadable CSV in
the submission format.

```bash
pip install -r requirements.txt   # streamlit is needed only for the sandbox UI
streamlit run app.py
```
