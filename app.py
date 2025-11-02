# app.py
import os
import json
import pandas as pd
import streamlit as st
from fetch_youtube import extract_video_id, fetch_comments
from analyze import analyze
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

    # Save to session state so LLM can use later
    st.session_state["df"] = df
    st.session_state["result"] = result
    st.session_state["video_id"] = video_id

# Retrieve from session
df = st.session_state.get("df", pd.DataFrame())
result = st.session_state.get("result", {})
video_id = st.session_state.get("video_id", "video")

# ----------------------------
# Display results and downloads
# ----------------------------
if not df.empty:
    st.subheader("Summary")
    st.metric("Comments fetched", result["scalars"]["n_comments"])
    st.metric("Avg. text length", f"{result['scalars']['avg_text_len']:.1f}")

    st.subheader("Sample comments")
    st.dataframe(df.head(200))

    st.subheader("Downloads")
    st.download_button(
        "Download comments (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"{video_id}_comments.csv",
        mime="text/csv"
    )
    st.download_button(
        "Download comments (JSONL)",
        "\n".join(
            df.apply(lambda row: json.dumps(row.dropna().to_dict(), ensure_ascii=False), axis=1)
        ).encode("utf-8"),
        file_name=f"{video_id}_comments.jsonl",
        mime="application/json"
    )
    st.download_button(
        "Download analysis (JSON)",
        pd.Series(result).to_json(indent=2).encode("utf-8"),
        file_name=f"{video_id}_analysis.json",
        mime="application/json"
    )
else:
    st.info("No comments loaded yet. Enter a URL and click Analyze.")

# ----------------------------
# Helper: build LLM prompt
# ----------------------------
def _comments_to_prompt(df, top_by: str = "relevance") -> str:
    if top_by == "likes" and "likes" in df.columns:
        top = df.nlargest(100, "likes").copy()
    else:
        top = df.head(100).copy()

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
        "You are summarizing YouTube comments. Identify the main themes, opinions, "
        "and viewer sentiment (rough % positive/neutral/negative). "
        "Provide a brief, structured markdown summary."
    )
    return f"{instructions}\n\nCOMMENTS (top 100):\n{joined}"

# ----------------------------
# LLM Summarization Section
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
        prompt = _comments_to_prompt(df, top_by="likes" if top_by.endswith("likes") else "relevance")
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
                    except Exception as e:
                        st.error(f"LLM error: {e}")
