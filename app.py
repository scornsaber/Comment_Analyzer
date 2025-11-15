# app.py
import os
import json
import pandas as pd
import streamlit as st
from fetch_youtube import extract_video_id, fetch_comments
from analyze import (
    analyze,                      # simple scalar stats
    run_pre_models,               # Detoxify + Sentiment
    fig_toxicity_distribution,    # matplotlib Figure
    fig_sentiment_distribution,   # matplotlib Figure
    fig_sentiment_score_hist,     # matplotlib Figure
)
from openai import OpenAI

st.set_page_config(page_title="YouTube Comment Analyzer", layout="wide")
st.title("YouTube Comment Analyzer")

# ----------------------------
# API Key and Input
# ----------------------------
api_key = st.secrets.get("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_API_KEY", "")
url = st.text_input("YouTube URL or Video ID")

if not api_key:
    st.warning("No YouTube API key set. Add it in .streamlit/secrets.toml or as env var YOUTUBE_API_KEY.")

if st.button("Analyze") and url and api_key:
    video_id = extract_video_id(url)
    with st.spinner("Fetching comments by relevance…"):
        df = fetch_comments(video_id, api_key, order="relevance", max_pages=10)
    with st.spinner("Analyzing…"):
        result = analyze(df)

    # Save to session state so analytics and LLM can use later
    st.session_state["df"] = df
    st.session_state["result"] = result
    st.session_state["video_id"] = video_id

    # Reset ML results for this new dataset and set a cache key
    st.session_state.pop("merged_df_ml", None)
    st.session_state.pop("ml_summary", None)
    st.session_state["ml_cache_key"] = (video_id, len(df))

# Retrieve from session
df = st.session_state.get("df", pd.DataFrame())
result = st.session_state.get("result", {})
video_id = st.session_state.get("video_id", "video")

# ----------------------------
# Display results
# ----------------------------
if not df.empty:
    st.subheader("Summary")
    st.metric("Comments fetched", result["scalars"]["n_comments"])
    st.metric("Avg. text length", f"{result['scalars']['avg_text_len']:.1f}")

    st.subheader("Sample comments")
    st.dataframe(df.head(200))
else:
    st.info("No comments loaded yet. Enter a URL and click Analyze.")

# ----------------------------
# Auto-run pre-LLM analytics (ONLY top 100 most relevant)
# ----------------------------
if not df.empty:
    expected_key = (video_id, len(df))
    have_key = st.session_state.get("ml_cache_key")
    merged_df_ml = st.session_state.get("merged_df_ml")

    # Always compute on the first 100 rows of df (fetch is already by relevance)
    df_top100 = df.head(100).copy()

    if merged_df_ml is None or have_key != expected_key:
        with st.status("Running toxicity & sentiment models", expanded=False):
            try:
                merged_df_ml, ml_summary = run_pre_models(df_top100, toxicity_threshold=0.7, max_items=100)
                st.session_state["merged_df_ml"] = merged_df_ml
                st.session_state["ml_summary"] = ml_summary
                st.session_state["ml_cache_key"] = expected_key
                st.success(f"Scored {ml_summary['n_scored']} comments (top 100 by relevance).")
            except Exception as e:
                st.error(f"Analysis error: {e}")

# Show charts in dropdowns (expanders)
merged_df_ml = st.session_state.get("merged_df_ml")
ml_summary = st.session_state.get("ml_summary")

if isinstance(merged_df_ml, pd.DataFrame) and not merged_df_ml.empty:
    st.divider()
    st.subheader("Pre-LLM Analytics (toxicity + sentiment) — By relevance")
    with st.expander("Toxic vs Not Toxic"):
        st.pyplot(fig_toxicity_distribution(merged_df_ml))
    with st.expander("Sentiment label distribution"):
        st.pyplot(fig_sentiment_distribution(merged_df_ml))
    with st.expander("Sentiment score histogram"):
        st.pyplot(fig_sentiment_score_hist(merged_df_ml))

# ----------------------------
# Helper: build LLM prompt (with pre-analysis injected)
# ----------------------------
def _comments_to_prompt(df, top_by: str = "relevance", ml_summary=None) -> str:
    # Choose top 100 comments for the LLM summary (unchanged)
    if top_by == "likes" and "likes" in df.columns:
        top = df.nlargest(100, "likes").copy()
    else:
        top = df.head(100).copy()

    # Pre-analysis context from ml_summary 
    analytics_context = ""
    if ml_summary:
        n_scored = ml_summary.get("n_scored", 0)
        n_toxic = ml_summary.get("n_toxic", 0)
        toxicity_ratio = (n_toxic / max(1, n_scored))
        avg_tox = ml_summary.get("avg_toxicity", 0.0)
        sent_counts = ml_summary.get("sentiment_counts", {})
        avg_sent = ml_summary.get("avg_sentiment_score", 0.0)
        analytics_context = (
            f"\n\nPre-analysis (model-assisted on TOP 100 by relevance):\n"
            f"- Comments scored: {n_scored}\n"
            f"- Toxic: {n_toxic} ({toxicity_ratio:.1%}), Avg toxicity: {avg_tox:.2f}\n"
            f"- Sentiment counts: {sent_counts}\n"
            f"- Avg sentiment score: {avg_sent:.2f}\n"
            f"Use this as context but verify against the comments below.\n"
        )

    # Build comment list
    lines = []
    for _, r in top.iterrows():
        likes = int(r.get("likes", 0) or 0)
        repl = int(r.get("replies", 0) or 0)
        text = (r.get("text") or "").replace("\n", " ").strip()
        if len(text) > 600:
            text = text[:600] + "…"
        lines.append(f"- [{likes}👍 | {repl}↩] {text}")
    joined = "\n".join(lines)

    instructions = (
        "You are summarizing YouTube comments. Use the analytics context to help "
        "understand tone and sentiment, but verify by reading the comments. "
        "Identify the main themes, representative opinions, disagreements, and an estimate "
        "of positive/neutral/negative sentiment. Provide a concise, structured markdown summary." 
        "Finally, include two action plans: one for the content creator and one for the moderator."
        "For moderator do not be overly strict. If the comments are non toxi provide minimal feedback."
    )
    return f"{instructions}{analytics_context}\n\nCOMMENTS (top 100):\n{joined}"

# ----------------------------
# LLM Summarization Section (AFTER analytics)
# ----------------------------
st.divider()
st.subheader("LLM Summary")

col1, col2 = st.columns([2, 1])
with col1:
    top_by = st.radio("Choose comments to summarize:", ["Top 100 by relevance", "Top 100 by likes"], horizontal=True)
with col2:
    run_summary = st.button("Summarize Comments", type="primary")

if run_summary:
    if df.empty:
        st.warning("No comments loaded yet.")
    else:
        prompt = _comments_to_prompt(
            df,
            top_by="likes" if top_by.endswith("likes") else "relevance",
            ml_summary=ml_summary,
        )
        client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))
        if not client.api_key:
            st.error("Missing OPENAI_API_KEY in Streamlit secrets or environment.")
        else:
            with st.chat_message("assistant"):
                with st.status("Summarizing comments...", expanded=False):
                    try:
                        resp = client.responses.create(
                            model="gpt-4o",
                            input=prompt,
                        )
                        summary = getattr(resp, "output_text", None) or str(resp)
                        st.markdown(summary)

                        # Save for feedback
                        st.session_state["last_prompt"] = prompt

                    except Exception as e:
                        st.error(f"LLM error: {e}")


# -----------------------------------------
# Feedback buttons
# -----------------------------------------
if st.session_state.get("last_prompt"):
    st.divider()
    st.subheader("Was this summary helpful?")

    col1, col2 = st.columns(2)
    with col1:
        up = st.button("👍 Yes")
    with col2:
        down = st.button("👎 No — summarize again")

    if up:
        st.success("Thanks for your feedback!")

    if down:
        st.warning("Re-running analysis and summarizing again…")

        try:
            client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))

            # rebuild prompt (using current df + analytics)
            new_prompt = _comments_to_prompt(df, "relevance", ml_summary)

            resp = client.responses.create(
                model="gpt-4o",
                input=new_prompt,
            )
            new_summary = getattr(resp, "output_text", None) or str(resp)

            # ✅ Put updated summary inside a dropdown
            with st.expander("🔄 Updated summary (retry)", expanded=True):
                st.markdown(new_summary)

            # Update session state
            st.session_state["last_prompt"] = new_prompt
            st.session_state["last_summary"] = new_summary

        except Exception as e:
            st.error(f"Re-summary error: {e}")



# ----------------------------
# Downloads (bottom): analysis JSON
# ----------------------------
if result:
    st.divider()
    st.subheader("Downloads")
    st.download_button(
        "Download analysis (JSON)",
        pd.Series(result).to_json(indent=2).encode("utf-8"),
        file_name=f"{video_id}_analysis.json",
        mime="application/json"
    )
