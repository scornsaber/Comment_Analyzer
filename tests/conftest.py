# tests/conftest.py
import sys
import types
import pandas as pd
import matplotlib.pyplot as plt
import pytest


@pytest.fixture(autouse=True)
def patch_external_modules(monkeypatch):
    """
    Autouse fixture: for every test, ensure that when app.py imports
    fetch_youtube, analyze, and openai, it gets our harmless test doubles.
    """

    # -------------------------
    # Dummy fetch_youtube module
    # -------------------------
    fetch_mod = types.ModuleType("fetch_youtube")

    def fake_extract_video_id(url: str) -> str:
        # keep it simple & deterministic
        return "dummy_video_id"

    def fake_fetch_comments(video_id: str, api_key: str,
                            order: str = "relevance", max_pages: int = 10) -> pd.DataFrame:
        # small deterministic DataFrame similar to what your app expects
        data = {
            "text": [
                "This video was awesome!",
                "I didn't like this at all...",
                "Kind of mid, but the editing was nice.",
            ],
            "likes": [10, 1, 3],
            "replies": [2, 0, 1],
        }
        return pd.DataFrame(data)

    fetch_mod.extract_video_id = fake_extract_video_id
    fetch_mod.fetch_comments = fake_fetch_comments
    sys.modules["fetch_youtube"] = fetch_mod

    # -------------------------
    # Dummy analyze module
    # -------------------------
    analyze_mod = types.ModuleType("analyze")

    def fake_analyze(df: pd.DataFrame):
        n = len(df)
        avg_len = float(df["text"].str.len().mean()) if n else 0.0
        return {
            "scalars": {
                "n_comments": n,
                "avg_text_len": avg_len,
            }
        }

    def fake_run_pre_models(df_top100: pd.DataFrame,
                            toxicity_threshold: float = 0.7,
                            max_items: int = 100):
        # just echo the df and return a simple summary
        df_res = df_top100.copy()
        df_res["toxicity"] = 0.1
        df_res["sentiment_label"] = "positive"
        df_res["sentiment_score"] = 0.9

        summary = {
            "n_scored": len(df_res),
            "n_toxic": 0,
            "avg_toxicity": 0.1,
            "sentiment_counts": {"positive": len(df_res)},
            "avg_sentiment_score": 0.9,
        }
        return df_res, summary

    def _dummy_fig(title: str) -> plt.Figure:
        fig, ax = plt.subplots()
        ax.set_title(title)
        ax.plot([0, 1], [0, 1])
        return fig

    def fake_fig_toxicity_distribution(df: pd.DataFrame) -> plt.Figure:
        return _dummy_fig("toxicity")

    def fake_fig_sentiment_distribution(df: pd.DataFrame) -> plt.Figure:
        return _dummy_fig("sentiment_dist")

    def fake_fig_sentiment_score_hist(df: pd.DataFrame) -> plt.Figure:
        return _dummy_fig("sentiment_hist")

    analyze_mod.analyze = fake_analyze
    analyze_mod.run_pre_models = fake_run_pre_models
    analyze_mod.fig_toxicity_distribution = fake_fig_toxicity_distribution
    analyze_mod.fig_sentiment_distribution = fake_fig_sentiment_distribution
    analyze_mod.fig_sentiment_score_hist = fake_fig_sentiment_score_hist

    sys.modules["analyze"] = analyze_mod

    # -------------------------
    # Dummy openai module
    # -------------------------
    openai_mod = types.ModuleType("openai")

    class FakeResponses:
        def create(self, model: str, input: str):
            # minimal fake Response object with output_text
            class Resp:
                pass

            resp = Resp()
            resp.output_text = f"[FAKE SUMMARY] model={model}, prompt_prefix={input[:40]!r}"
            return resp

    class FakeOpenAI:
        def __init__(self, api_key=None):
            self.api_key = api_key
            self.responses = FakeResponses()

    openai_mod.OpenAI = FakeOpenAI
    sys.modules["openai"] = openai_mod

    yield

    # (pytest will clean up monkeypatches automatically; sys.modules entries
    # are fine to leave in place during the test session.)
