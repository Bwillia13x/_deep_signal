"""Integration tests for vector search endpoint."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.services.embeddings import EmbeddingService


def mock_db_session():
    """Create a mock database session."""
    mock_db = MagicMock()
    return mock_db


def mock_embedding_service():
    """Create a mock embedding service."""
    mock_service = MagicMock()
    mock_service.embed = MagicMock(return_value=[0.1] * 384)
    return mock_service


@pytest.fixture
def client():
    return TestClient(app)


def test_vector_search_with_text_query(client):
    """Test vector search using text query."""
    # Create mock database session
    mock_db = MagicMock()
    
    # Mock database execute result
    mock_result = [
        {"id": 1, "title": "Quantum Computing Advances", "similarity": 0.95},
        {"id": 2, "title": "Machine Learning in Quantum Systems", "similarity": 0.87},
        {"id": 3, "title": "Quantum Algorithms", "similarity": 0.82},
    ]
    mock_db.execute().mappings().all.return_value = mock_result
    
    # Override dependencies
    app.dependency_overrides[get_db] = lambda: mock_db
    
    # Mock embedding service
    with patch.object(EmbeddingService, 'get') as mock_get_service:
        mock_service = MagicMock()
        mock_service.embed = MagicMock(return_value=[0.1] * 384)
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.get("/papers/near?text_query=quantum computing&k=3")
        
        # Clear overrides
        app.dependency_overrides.clear()
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["id"] == 1
        assert data[0]["title"] == "Quantum Computing Advances"
        assert data[0]["similarity"] == 0.95
        assert data[1]["similarity"] >= data[2]["similarity"], "Results should be ordered by similarity"
        
        # Verify embedding service was called
        mock_service.embed.assert_called_once_with("quantum computing")


def test_vector_search_with_paper_id(client):
    """Test vector search using paper_id."""
    # Create mock database session
    mock_db = MagicMock()
    
    # Mock paper embedding lookup
    mock_paper_embedding = ([0.2] * 384,)
    mock_db.query().filter().first.return_value = mock_paper_embedding
    
    # Mock similar papers result
    mock_result = [
        {"id": 100, "title": "Similar Paper 1", "similarity": 0.99},
        {"id": 101, "title": "Similar Paper 2", "similarity": 0.91},
    ]
    mock_db.execute().mappings().all.return_value = mock_result
    
    # Override dependencies
    app.dependency_overrides[get_db] = lambda: mock_db
    
    # Make request
    response = client.get("/papers/near?paper_id=100&k=2")
    
    # Clear overrides
    app.dependency_overrides.clear()
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all("similarity" in item for item in data)
    assert data[0]["similarity"] >= data[1]["similarity"]


def test_vector_search_missing_parameters(client):
    """Test vector search without required parameters."""
    # No mock needed for this test
    response = client.get("/papers/near")
    assert response.status_code == 400
    assert "Provide text_query or paper_id" in response.json()["detail"]


def test_vector_search_paper_not_found(client):
    """Test vector search with non-existent paper_id."""
    # Create mock database session
    mock_db = MagicMock()
    
    # Mock paper not found
    mock_db.query().filter().first.return_value = None
    
    # Override dependencies
    app.dependency_overrides[get_db] = lambda: mock_db
    
    response = client.get("/papers/near?paper_id=99999")
    
    # Clear overrides
    app.dependency_overrides.clear()
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_vector_search_paper_no_embedding(client):
    """Test vector search with paper that has no embedding."""
    # Create mock database session
    mock_db = MagicMock()
    
    # Mock paper exists but has no embedding
    mock_db.query().filter().first.return_value = (None,)
    
    # Override dependencies
    app.dependency_overrides[get_db] = lambda: mock_db
    
    response = client.get("/papers/near?paper_id=123")
    
    # Clear overrides
    app.dependency_overrides.clear()
    
    assert response.status_code == 404
    assert "no embedding" in response.json()["detail"]


def test_vector_search_k_parameter_bounds(client):
    """Test vector search with different k values."""
    # Create mock database session
    mock_db = MagicMock()
    mock_db.execute().mappings().all.return_value = []
    
    # Override dependencies
    app.dependency_overrides[get_db] = lambda: mock_db
    
    # Mock embedding service
    with patch.object(EmbeddingService, 'get') as mock_get_service:
        mock_service = MagicMock()
        mock_service.embed = MagicMock(return_value=[0.1] * 384)
        mock_get_service.return_value = mock_service
        
        # Valid k values
        for k in [1, 10, 50]:
            response = client.get(f"/papers/near?text_query=test&k={k}")
            assert response.status_code == 200, f"k={k} should be valid"
        
        # Invalid k values
        for k in [0, -1, 51, 100]:
            response = client.get(f"/papers/near?text_query=test&k={k}")
            assert response.status_code == 422, f"k={k} should be invalid"
    
    # Clear overrides
    app.dependency_overrides.clear()
