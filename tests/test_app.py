# tests/test_app_integration.py
import os
from pathlib import Path
import importlib.util
import sys

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def app_test():
    """
    Returns an AppTest instance for app.py, with dummy secrets injected.
    """
    # Ensure we run from the project root so "app.py" resolves correctly
    os.chdir(ROOT)

    at = AppTest.from_file("app.py")

    # Dummy secrets for the app (avoid real keys in tests)
    at.secrets["YOUTUBE_API_KEY"] = "fake-youtube-key"
    at.secrets["OPENAI_API_KEY"] = "fake-openai-key"

    return at


def _run_analyze_flow(at: AppTest):
    """
    Helper: run the app, set a URL, click Analyze, and return the rerun AppTest.
    """
    # Initial run: page renders inputs
    at.run()
    assert not at.exception

    # There should be exactly 1 text_input (the URL/ID field)
    assert len(at.text_input) == 1
    at.text_input[0].set_value("https://www.youtube.com/watch?v=dummy").run()
    assert at.text_input[0].value.endswith("dummy")

    # First button is the "Analyze" button (created before others in app.py)
    assert len(at.button) >= 1
    assert at.button[0].label == "Analyze"

    # Click Analyze and rerun
    at.button[0].click().run()
    assert not at.exception

    return at


def test_analyze_flow_populates_session_and_metrics(app_test: AppTest):
    """
    Integration test: “Analyze” fetches comments, runs analyze(), and shows metrics.
    """
    at = _run_analyze_flow(app_test)

    # Check session_state has df, result, video_id
    assert "df" in at.session_state
    assert "result" in at.session_state
    assert "video_id" in at.session_state

    df = at.session_state["df"]
    result = at.session_state["result"]

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "text" in df.columns

    # Our dummy analyze() returns these scalars
    assert result["scalars"]["n_comments"] == len(df)
    assert result["scalars"]["avg_text_len"] > 0

    # UI: there should be metrics shown for comments + avg length
    # (ordering: first metric is "Comments fetched")
    assert len(at.metric) >= 2
    assert at.metric[0].label == "Comments fetched"
    assert at.metric[1].label == "Avg. text length"

    # UI: dataframe with sample comments should be displayed
    assert len(at.dataframe) >= 1
    sample_df = at.dataframe[0].value
    assert isinstance(sample_df, pd.DataFrame)
    # Should be a subset of the fetched df
    assert not sample_df.empty
    assert all(col in sample_df.columns for col in ["text", "likes", "replies"])

    # Pre-LLM analytics: run_pre_models should have produced merged_df_ml & ml_summary
    assert "merged_df_ml" in at.session_state
    assert "ml_summary" in at.session_state
    merged_df_ml = at.session_state["merged_df_ml"]
    ml_summary = at.session_state["ml_summary"]

    assert isinstance(merged_df_ml, pd.DataFrame)
    assert not merged_df_ml.empty
    assert ml_summary["n_scored"] == len(merged_df_ml)
    assert ml_summary["avg_toxicity"] == pytest.approx(0.1)


def test_llm_summary_flow_uses_fake_openai_and_updates_state(app_test: AppTest):
    """
    Integration test: after Analyze, clicking “Summarize Comments” calls the
    fake OpenAI client and stores last_prompt / last_summary in session_state.
    """
    at = _run_analyze_flow(app_test)

    # At this point, df + ml_summary should exist from previous test path
    assert "df" in at.session_state
    assert "ml_summary" in at.session_state

    # There should now be a “Summarize Comments” button somewhere
    # By construction in app.py, it's the second st.button
    assert len(at.button) >= 2
    assert at.button[1].label == "Summarize Comments"

    # Click “Summarize Comments”
    at.button[1].click().run()
    assert not at.exception

    # Our fake OpenAI client returns a markdown summary via st.markdown(...)
    # Find any markdown element that contains the FAKE SUMMARY prefix.
    fake_markdowns = [
        m for m in at.markdown if "[FAKE SUMMARY]" in m.value
    ]
    assert fake_markdowns, "Expected a fake LLM summary to be rendered via st.markdown."

    # The app should store the prompt used for the summary
    assert "last_prompt" in at.session_state
    prompt = at.session_state["last_prompt"]
    assert "COMMENTS (top 100)" in prompt
    # It should include some of our dummy comment text
    assert "This video was awesome!" in prompt

    # After a successful summary, feedback controls should be shown.
    # There are two feedback buttons: 👍 Yes, 👎 No — summarize again
    labels = [b.label for b in at.button]
    assert "👍 Yes" in labels
    assert "👎 No — summarize again" in labels


def test_comments_to_prompt_includes_analytics_context(app_test: AppTest):
    """
    Integration-style test of the internal helper _comments_to_prompt:
    load app.py directly from disk and verify that ml_summary is injected
    into the prompt.
    """
    app_path = ROOT / "app.py"
    assert app_path.exists(), f"app.py not found at {app_path}"

    # Load app.py as a module without requiring it to be on sys.path
    spec = importlib.util.spec_from_file_location("app_module_for_tests", app_path)
    app_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = app_module
    spec.loader.exec_module(app_module)  # type: ignore[arg-type]

    # Build a small df similar to what the app uses
    df = pd.DataFrame(
        {
            "text": ["good", "bad", "okay"],
            "likes": [5, 0, 1],
            "replies": [0, 0, 1],
        }
    )
    ml_summary = {
        "n_scored": 3,
        "n_toxic": 1,
        "avg_toxicity": 0.2,
        "sentiment_counts": {"positive": 2, "negative": 1},
        "avg_sentiment_score": 0.1,
    }

    prompt = app_module._comments_to_prompt(df, top_by="likes", ml_summary=ml_summary)

    # Check that instructions are present
    assert "You are summarizing YouTube comments" in prompt

    # Check that analytics context was injected
    assert "Pre-analysis (model-assisted on TOP 100 by relevance)" in prompt
    assert "Comments scored: 3" in prompt
    assert "Toxic: 1" in prompt
    assert "Sentiment counts: {'positive': 2, 'negative': 1}" in prompt

    # Check that comment list lines are present with likes/replies
    assert "- [5👍 | 0↩] good" in prompt
    assert "- [0👍 | 0↩] bad" in prompt
    assert "- [1👍 | 1↩] okay" in prompt