import os
import streamlit as st
import pandas as pd
from fetch_youtube import extract_video_id, fetch_comments
from analyze import analyze
import json

st.set_page_config(page_title="YouTube Comment Analyzer", layout="wide")
st.title("YouTube Comment Analyzer")

# Use API key from secrets.toml or env var
api_key = st.secrets.get("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_API_KEY", "")

url = st.text_input("YouTube URL or Video ID")
if not api_key:
    st.warning("No YouTube API key set. Add it in .streamlit/secrets.toml or as env var YOUTUBE_API_KEY.")

if st.button("Analyze") and url and api_key:
    video_id = extract_video_id(url)
    with st.spinner("Fetching comments…"):
        df = fetch_comments(video_id, api_key, max_pages=10)
    with st.spinner("Analyzing…"):
        result = analyze(df)

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
        "\n".join(df.apply(lambda row: json.dumps(row.dropna().to_dict(), ensure_ascii=False), axis=1)).encode("utf-8"),
        file_name=f"{video_id}_comments.jsonl",
        mime="application/json"
    )
    st.download_button(
        "Download analysis (JSON)",
        pd.Series(result).to_json(indent=2).encode("utf-8"),
        file_name=f"{video_id}_analysis.json",
        mime="application/json"
    )
