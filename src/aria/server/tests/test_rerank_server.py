"""Tests for the sentence-transformers rerank micro-server in server/rerank.py."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_app(model_name: str = "BAAI/bge-reranker-v2-m3"):
    """Create a test app with a mocked CrossEncoder."""
    mock_model = MagicMock()
    mock_model.predict.return_value = [0.9, 0.3, 0.7]

    with patch("sentence_transformers.CrossEncoder", return_value=mock_model):
        from aria.server.rerank import create_app

        app = create_app(model_name)

    return app, mock_model


class TestCreateApp:
    """Tests for create_app()."""

    def test_app_has_rerank_endpoint(self):
        """App must register a POST /rerank route."""
        app, _ = _make_app()
        routes = [getattr(r, "path", "") for r in app.routes]
        assert "/rerank" in routes

    def test_app_has_health_endpoint(self):
        """App must register a GET /health route."""
        app, _ = _make_app()
        routes = [getattr(r, "path", "") for r in app.routes]
        assert "/health" in routes


class TestRerankEndpoint:
    """Tests for POST /rerank."""

    def setup_method(self):
        self.app, self.mock_model = _make_app()
        self.client = TestClient(self.app)

    def test_returns_200_with_ranked_results(self):
        """Valid request should return 200 with sorted results."""
        self.mock_model.predict.return_value = [0.3, 0.9, 0.7]

        response = self.client.post(
            "/rerank",
            json={
                "query": "What is AI?",
                "documents": ["doc A", "doc B", "doc C"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 3
        # Results should be sorted by relevance_score descending
        scores = [r["relevance_score"] for r in data["results"]]
        assert scores == sorted(scores, reverse=True)

    def test_top_n_limits_results(self):
        """top_n parameter should limit the number of returned results."""
        self.mock_model.predict.return_value = [0.3, 0.9, 0.7]

        response = self.client.post(
            "/rerank",
            json={
                "query": "What is AI?",
                "documents": ["doc A", "doc B", "doc C"],
                "top_n": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2

    def test_result_contains_index_and_score(self):
        """Each result must have index, relevance_score, and document fields."""
        self.mock_model.predict.return_value = [0.8]

        response = self.client.post(
            "/rerank",
            json={
                "query": "query",
                "documents": ["only doc"],
            },
        )

        assert response.status_code == 200
        result = response.json()["results"][0]
        assert "index" in result
        assert "relevance_score" in result
        assert "document" in result

    def test_passes_query_doc_pairs_to_model(self):
        """Model.predict should be called with (query, doc) pairs."""
        self.mock_model.predict.return_value = [0.5, 0.5]
        docs = ["first", "second"]

        self.client.post(
            "/rerank",
            json={"query": "my query", "documents": docs},
        )

        expected_pairs = [("my query", "first"), ("my query", "second")]
        self.mock_model.predict.assert_called_once_with(expected_pairs)

    def test_empty_documents_returns_empty_results(self):
        """Empty document list should return empty results."""
        self.mock_model.predict.return_value = []

        response = self.client.post(
            "/rerank",
            json={"query": "query", "documents": []},
        )

        assert response.status_code == 200
        assert response.json()["results"] == []


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self):
        """Health endpoint should return HTTP 200."""
        app, _ = _make_app()
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
