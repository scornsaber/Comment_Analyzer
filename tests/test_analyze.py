import pytest
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from unittest.mock import Mock, patch, MagicMock

from analyze import (
    analyze,
    _device,
    _batch,
    run_pre_models,
    fig_toxicity_distribution,
    fig_sentiment_distribution,
    fig_sentiment_score_hist,
)


class TestAnalyze:
    """Tests for the basic analyze function."""
    
    def test_analyze_empty_dataframe(self):
        """Test analyze with empty DataFrame."""
        df = pd.DataFrame(columns=["text"])
        result = analyze(df)
        
        assert result["scalars"]["n_comments"] == 0
        assert result["scalars"]["avg_text_len"] == 0.0
        assert result["bins"] == {}
    
    def test_analyze_with_data(self):
        """Test analyze with sample data."""
        df = pd.DataFrame({
            "text": ["Hello", "World", "Test message"]
        })
        result = analyze(df)
        
        assert result["scalars"]["n_comments"] == 3
        assert result["scalars"]["avg_text_len"] > 0
        assert isinstance(result["scalars"]["avg_text_len"], float)
    
    def test_analyze_average_length_calculation(self):
        """Test that average length is calculated correctly."""
        df = pd.DataFrame({
            "text": ["ab", "abcd", "abcdef"]  # lengths: 2, 4, 6
        })
        result = analyze(df)
        
        expected_avg = (2 + 4 + 6) / 3
        assert result["scalars"]["avg_text_len"] == expected_avg


class TestDevice:
    """Tests for device detection."""
    
    @patch('analyze.torch', None)
    def test_device_no_torch(self):
        """Test device returns 'cpu' when torch is not available."""
        # Clear the cache
        _device.cache_clear()
        result = _device()
        assert result == "cpu"
    
    @patch('analyze.torch')
    def test_device_cuda_available(self, mock_torch):
        """Test device returns 'cuda' when CUDA is available."""
        mock_torch.cuda.is_available.return_value = True
        _device.cache_clear()
        result = _device()
        assert result == "cuda"
    
    @patch('analyze.torch')
    def test_device_cuda_not_available(self, mock_torch):
        """Test device returns 'cpu' when CUDA is not available."""
        mock_torch.cuda.is_available.return_value = False
        _device.cache_clear()
        result = _device()
        assert result == "cpu"


class TestBatch:
    """Tests for the batch generator function."""
    
    def test_batch_empty_list(self):
        """Test batching an empty list."""
        result = list(_batch([], size=16))
        assert result == []
    
    def test_batch_single_batch(self):
        """Test batching with items less than batch size."""
        items = ["a", "b", "c"]
        result = list(_batch(items, size=16))
        
        assert len(result) == 1
        assert result[0] == ["a", "b", "c"]
    
    def test_batch_multiple_batches(self):
        """Test batching with items requiring multiple batches."""
        items = list(range(10))
        result = list(_batch(items, size=3))
        
        assert len(result) == 4
        assert result[0] == [0, 1, 2]
        assert result[1] == [3, 4, 5]
        assert result[2] == [6, 7, 8]
        assert result[3] == [9]
    
    def test_batch_exact_size(self):
        """Test batching when items exactly match batch size."""
        items = list(range(6))
        result = list(_batch(items, size=3))
        
        assert len(result) == 2
        assert result[0] == [0, 1, 2]
        assert result[1] == [3, 4, 5]


class TestRunPreModels:
    """Tests for the run_pre_models function."""
    
    def test_run_pre_models_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result_df, summary = run_pre_models(df)
        
        assert result_df.empty
        assert "error" in summary
    
    def test_run_pre_models_no_text_column(self):
        """Test with DataFrame missing text column."""
        df = pd.DataFrame({"other": [1, 2, 3]})
        result_df, summary = run_pre_models(df)
        
        assert result_df.empty
        assert "error" in summary
    
    @patch('analyze._load_models')
    def test_run_pre_models_with_data(self, mock_load_models):
        """Test with valid data and mocked models."""
        # Setup mocks
        mock_tox = Mock()
        mock_tox.predict.return_value = {
            "toxicity": [0.1, 0.8],
            "severe_toxicity": [0.05, 0.7],
        }
        
        mock_sent = Mock()
        mock_sent.return_value = [
            {"label": "POSITIVE", "score": 0.9},
            {"label": "NEGATIVE", "score": 0.85},
        ]
        
        mock_load_models.return_value = (mock_tox, mock_sent)
        
        # Test data
        df = pd.DataFrame({"text": ["Nice comment", "Bad comment"]})
        result_df, summary = run_pre_models(df, toxicity_threshold=0.5)
        
        # Assertions
        assert len(result_df) == 2
        assert "is_toxic" in result_df.columns
        assert "sentiment" in result_df.columns
        assert summary["n_scored"] == 2
        assert "n_toxic" in summary
        assert "sentiment_counts" in summary
    
    @patch('analyze._load_models')
    def test_run_pre_models_max_items(self, mock_load_models):
        """Test that max_items limits processing."""
        mock_tox = Mock()
        def predict_side_effect(texts):
            return {"toxicity": [0.1] * len(texts)}
        mock_tox.predict.side_effect = predict_side_effect

        mock_sent = Mock()
        def sent_side_effect(texts):
            return [{"label": "POSITIVE", "score": 0.9} for _ in texts]
        mock_sent.side_effect = sent_side_effect

        mock_load_models.return_value = (mock_tox, mock_sent)

        # Use unique text values to avoid merge duplicates
        df = pd.DataFrame({"text": [f"text_{i}" for i in range(100)]})
        result_df, summary = run_pre_models(df, max_items=2)

        assert summary["n_scored"] == 2
        assert len(result_df) == 2
        
    @patch('analyze._load_models')
    def test_run_pre_models_toxicity_threshold(self, mock_load_models):
        """Test toxicity threshold classification."""
        mock_tox = Mock()
        mock_tox.predict.return_value = {
            "toxicity": [0.5, 0.9],
        }
        
        mock_sent = Mock()
        mock_sent.return_value = [
            {"label": "NEUTRAL", "score": 0.5},
            {"label": "NEGATIVE", "score": 0.9},
        ]
        
        mock_load_models.return_value = (mock_tox, mock_sent)
        
        df = pd.DataFrame({"text": ["Comment 1", "Comment 2"]})
        result_df, summary = run_pre_models(df, toxicity_threshold=0.7)
        
        assert summary["n_toxic"] == 1
        assert summary["n_nontoxic"] == 1


class TestFigures:
    """Tests for visualization functions."""
    
    def test_fig_toxicity_distribution(self):
        """Test toxicity distribution figure."""
        df = pd.DataFrame({
            "is_toxic": [True, False, False, True, False],
            "text": ["a", "b", "c", "d", "e"]
        })
        
        fig = fig_toxicity_distribution(df)
        
        assert isinstance(fig, plt.Figure)
        plt.close(fig)
    
    def test_fig_sentiment_distribution(self):
        """Test sentiment distribution figure."""
        df = pd.DataFrame({
            "sentiment": ["POSITIVE", "NEGATIVE", "POSITIVE", "NEUTRAL"],
            "text": ["a", "b", "c", "d"]
        })
        
        fig = fig_sentiment_distribution(df)
        
        assert isinstance(fig, plt.Figure)
        plt.close(fig)
    
    def test_fig_sentiment_score_hist(self):
        """Test sentiment score histogram."""
        df = pd.DataFrame({
            "sentiment_score": [0.1, 0.3, 0.5, 0.7, 0.9],
            "text": ["a", "b", "c", "d", "e"]
        })
        
        fig = fig_sentiment_score_hist(df)
        
        assert isinstance(fig, plt.Figure)
        plt.close(fig)
    
    def test_figures_with_empty_dataframe(self):
        """Test that figures handle empty DataFrames."""
        df = pd.DataFrame(columns=["is_toxic", "sentiment", "sentiment_score"])
        
        # These should not raise errors
        fig1 = fig_toxicity_distribution(df)
        fig2 = fig_sentiment_distribution(df)
        fig3 = fig_sentiment_score_hist(df)
        
        assert isinstance(fig1, plt.Figure)
        assert isinstance(fig2, plt.Figure)
        assert isinstance(fig3, plt.Figure)
        
        plt.close('all')


# Fixtures for common test data
@pytest.fixture
def sample_dataframe():
    """Fixture providing a sample DataFrame for testing."""
    return pd.DataFrame({
        "text": [
            "This is a great comment!",
            "Terrible and offensive",
            "Neutral statement here",
            "Another positive message",
        ]
    })


@pytest.fixture
def scored_dataframe():
    """Fixture providing a DataFrame with scores."""
    return pd.DataFrame({
        "text": ["Comment 1", "Comment 2", "Comment 3"],
        "toxicity": [0.2, 0.8, 0.3],
        "is_toxic": [False, True, False],
        "sentiment": ["POSITIVE", "NEGATIVE", "NEUTRAL"],
        "sentiment_score": [0.9, 0.85, 0.5],
    })