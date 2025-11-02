# analyze.py
import pandas as pd
from typing import Dict, Tuple, Optional, List
from functools import lru_cache
import matplotlib.pyplot as plt

try:
    import torch
except Exception:
    torch = None

def analyze(df: pd.DataFrame) -> Dict:
    n = len(df)
    avg_len = df["text"].str.len().mean() if n else 0.0
    return {
        "scalars": {
            "n_comments": int(n),
            "avg_text_len": float(avg_len),
        },
        "bins": {},
    }

@lru_cache(maxsize=1)
def _device() -> str:
    if torch is not None and getattr(torch, "cuda", None) and torch.cuda.is_available():
        return "cuda"
    return "cpu"

@lru_cache(maxsize=1)
def _load_models() -> Tuple[object, object]:
    from detoxify import Detoxify
    from transformers import pipeline
    dev = _device()
    detoxify_device = dev                  # "cuda" or "cpu"
    pipeline_device = 0 if dev == "cuda" else -1
    tox = Detoxify("multilingual", device=detoxify_device)
    sent = pipeline("sentiment-analysis", device=pipeline_device)
    return tox, sent

def _batch(xs: List[str], size: int = 16):
    for i in range(0, len(xs), size):
        yield xs[i:i+size]

def run_pre_models(
    df: pd.DataFrame,
    toxicity_threshold: float = 0.7,
    max_items: Optional[int] = 1000,
) -> Tuple[pd.DataFrame, Dict]:
    if df.empty or "text" not in df.columns:
        return pd.DataFrame(), {"error": "No text column or empty DataFrame."}

    work = df.head(max_items) if max_items is not None else df
    texts = work["text"].fillna("").astype(str).tolist()

    tox_model, sent_model = _load_models()

    # Toxicity (batched)
    tox_parts = []
    for chunk in _batch(texts, 16):
        preds = tox_model.predict(chunk)   # dict of lists
        part = pd.DataFrame(preds)
        part.insert(0, "text", chunk)
        tox_parts.append(part)
    tox_df = pd.concat(tox_parts, ignore_index=True) if tox_parts else pd.DataFrame(columns=["text"])

    # Sentiment (batched)
    max_seq = 512
    trunc = [t[:max_seq] for t in texts]
    sent_recs = []
    for chunk in _batch(trunc, 32):
        out = sent_model(chunk)
        sent_recs.extend(out)
    sent_df = pd.DataFrame(
        [{"text": t, "sentiment": r.get("label"), "sentiment_score": float(r.get("score", 0.0))}
         for t, r in zip(texts, sent_recs)]
    )

    merged = pd.merge(tox_df, sent_df, on="text", how="inner")
    if "toxicity" not in merged.columns:
        tox_cols = [c for c in merged.columns if c not in ("text","sentiment","sentiment_score")]
        merged["toxicity"] = merged[tox_cols].mean(axis=1) if tox_cols else 0.0
    merged["is_toxic"] = merged["toxicity"] > toxicity_threshold

    summary = {
        "n_scored": int(len(merged)),
        "toxic_threshold": float(toxicity_threshold),
        "n_toxic": int(merged["is_toxic"].sum()),
        "n_nontoxic": int((~merged["is_toxic"]).sum()),
        "sentiment_counts": merged["sentiment"].value_counts(dropna=False).to_dict(),
        "avg_sentiment_score": float(merged["sentiment_score"].mean() if len(merged) else 0.0),
        "avg_toxicity": float(merged["toxicity"].mean() if len(merged) else 0.0),
    }
    return merged, summary

def fig_toxicity_distribution(merged_df: pd.DataFrame) -> plt.Figure:
    fig = plt.figure(figsize=(6,4))
    values = [int((~merged_df["is_toxic"]).sum()), int(merged_df["is_toxic"].sum())]
    plt.bar(["Not Toxic","Toxic"], values)
    plt.ylabel("Number of Comments")
    plt.title("Toxic vs Not Toxic")
    return fig

def fig_sentiment_distribution(merged_df: pd.DataFrame) -> plt.Figure:
    fig = plt.figure(figsize=(6,4))
    merged_df["sentiment"].value_counts(dropna=False).plot(kind="bar")
    plt.ylabel("Number of Comments")
    plt.title("Sentiment Label Distribution")
    plt.xticks(rotation=0)
    return fig

def fig_sentiment_score_hist(merged_df: pd.DataFrame) -> plt.Figure:
    fig = plt.figure(figsize=(7,4))
    plt.hist(merged_df["sentiment_score"], bins=20, edgecolor="black")
    plt.xlabel("Sentiment Score")
    plt.ylabel("Frequency")
    plt.title("Sentiment Score Histogram")
    return fig
