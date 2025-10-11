"""Integration tests for evaluation API endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.api.app import app
from backend.config import get_settings
from backend.db.mongo_client import MongoDBClient
from backend.evaluator.service import EvaluatorService


@pytest.fixture(scope="module")
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture(scope="module")
def db_client():
    """MongoDB client for test setup/teardown."""
    settings = get_settings()
    return MongoDBClient(settings)


@pytest.fixture(scope="module")
def test_pipeline_ids(db_client):
    """Create test pipeline data and return IDs for cleanup."""
    evaluator = EvaluatorService(db_client)
    
    # Create test JSON pipeline
    json_id = "test-json-integration"
    evaluator.evaluate_and_store_handoff(
        pipeline_id=json_id,
        handoff_id=f"{json_id}-h1",
        agent_from="TestAgent1",
        agent_to="TestAgent2",
        context_sent='{"test": "data"}',
        context_received='{"test": "data"}',
        metadata={"format": "json"},
        use_llm_judge=False
    )
    evaluator.finalize_pipeline(json_id)
    
    # Create test Markdown pipeline
    md_id = "test-md-integration"
    evaluator.evaluate_and_store_handoff(
        pipeline_id=md_id,
        handoff_id=f"{md_id}-h1",
        agent_from="TestAgent1",
        agent_to="TestAgent2",
        context_sent="Test data in markdown",
        context_received="Test data",
        metadata={"format": "markdown"},
        use_llm_judge=False
    )
    evaluator.finalize_pipeline(md_id)
    
    yield {"json": json_id, "markdown": md_id}
    
    # Cleanup
    handoffs_coll = db_client.get_collection("eval_handoffs")
    pipelines_coll = db_client.get_collection("eval_pipelines")
    
    handoffs_coll.delete_many({"pipeline_id": {"$in": [json_id, md_id]}})
    pipelines_coll.delete_many({"pipeline_id": {"$in": [json_id, md_id]}})


class TestPipelinesEndpoint:
    """Tests for /api/evaluations/pipelines endpoint."""
    
    def test_list_pipelines_success(self, client, test_pipeline_ids):
        """Test listing pipelines returns data."""
        response = client.get("/api/evaluations/pipelines")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Should include our test pipelines
        pipeline_ids = [p["pipeline_id"] for p in data]
        assert test_pipeline_ids["json"] in pipeline_ids or test_pipeline_ids["markdown"] in pipeline_ids
    
    def test_list_pipelines_with_pagination(self, client):
        """Test pagination parameters."""
        response = client.get("/api/evaluations/pipelines?limit=5&skip=0")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
    
    def test_list_pipelines_with_format_filter(self, client, test_pipeline_ids):
        """Test filtering by format."""
        response = client.get("/api/evaluations/pipelines?format=json")
        assert response.status_code == 200
        
        data = response.json()
        # All results should be JSON pipelines
        for pipeline in data:
            assert pipeline["format"] == "json"
    
    def test_get_pipeline_detail_success(self, client, test_pipeline_ids):
        """Test getting pipeline details."""
        pipeline_id = test_pipeline_ids["json"]
        response = client.get(f"/api/evaluations/pipelines/{pipeline_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pipeline_id"] == pipeline_id
        assert "handoffs" in data
        assert "overall_pipeline_score" in data
    
    def test_get_pipeline_detail_not_found(self, client):
        """Test 404 for non-existent pipeline."""
        response = client.get("/api/evaluations/pipelines/nonexistent-id")
        assert response.status_code == 404


class TestHandoffsEndpoint:
    """Tests for /api/evaluations/handoffs endpoint."""
    
    def test_list_handoffs_success(self, client, test_pipeline_ids):
        """Test listing handoffs."""
        response = client.get("/api/evaluations/handoffs")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Verify structure
        if data:
            handoff = data[0]
            assert "handoff_id" in handoff
            assert "pipeline_id" in handoff
            assert "agent_from" in handoff
            assert "agent_to" in handoff
            assert "eval_scores" in handoff
    
    def test_list_handoffs_by_pipeline(self, client, test_pipeline_ids):
        """Test filtering handoffs by pipeline ID."""
        pipeline_id = test_pipeline_ids["json"]
        response = client.get(f"/api/evaluations/handoffs?pipeline_id={pipeline_id}")
        assert response.status_code == 200
        
        data = response.json()
        # All handoffs should belong to the specified pipeline
        for handoff in data:
            assert handoff["pipeline_id"] == pipeline_id
    
    def test_list_handoffs_pagination(self, client):
        """Test handoff pagination."""
        response = client.get("/api/evaluations/handoffs?limit=10&skip=0")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) <= 10


class TestComparisonEndpoint:
    """Tests for /api/evaluations/comparison endpoint."""
    
    def test_get_latest_comparison_success(self, client, test_pipeline_ids):
        """Test getting latest comparison."""
        response = client.get("/api/evaluations/comparison/latest")
        
        # May not have comparison data if no json/md pairs exist
        if response.status_code == 200:
            data = response.json()
            assert "json_pipeline" in data
            assert "markdown_pipeline" in data
            assert "fidelity_delta" in data
            assert "drift_delta" in data
            assert "compression_delta" in data
            assert "winner" in data
            assert data["winner"] in ["json", "markdown", "tie"]
        elif response.status_code == 404:
            # Acceptable if no comparison data exists
            assert "No comparison available" in response.json()["detail"]
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")


class TestStatsEndpoints:
    """Tests for statistics endpoints."""
    
    def test_get_stats_by_format(self, client, test_pipeline_ids):
        """Test format statistics aggregation."""
        response = client.get("/api/evaluations/stats/by-format")
        assert response.status_code == 200
        
        data = response.json()
        assert "formats" in data
        assert "count" in data
        assert isinstance(data["formats"], list)
    
    def test_get_evaluation_summary(self, client, test_pipeline_ids):
        """Test overall evaluation summary."""
        response = client.get("/api/evaluations/stats/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_handoffs" in data
        assert "total_pipelines" in data
        assert "overall_stats" in data
        
        stats = data["overall_stats"]
        assert "avg_fidelity" in stats
        assert "avg_drift" in stats
        assert "avg_compression" in stats
        assert "min_fidelity" in stats
        assert "max_fidelity" in stats
        
        # Validate ranges
        assert 0 <= stats["avg_fidelity"] <= 1
        assert 0 <= stats["avg_drift"] <= 1
        assert 0 <= stats["min_fidelity"] <= 1
        assert 0 <= stats["max_fidelity"] <= 1


class TestDeletePipelineEndpoint:
    """Tests for pipeline deletion endpoint."""
    
    def test_delete_pipeline_success(self, client, db_client):
        """Test deleting a pipeline and its handoffs."""
        # Create temporary pipeline for deletion test
        evaluator = EvaluatorService(db_client)
        temp_id = "test-delete-temp"
        
        evaluator.evaluate_and_store_handoff(
            pipeline_id=temp_id,
            handoff_id=f"{temp_id}-h1",
            agent_from="A",
            agent_to="B",
            context_sent="test",
            context_received="test",
            metadata={},
            use_llm_judge=False
        )
        evaluator.finalize_pipeline(temp_id)
        
        # Delete it
        response = client.delete(f"/api/evaluations/pipelines/{temp_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["deleted_pipeline"] == temp_id
        assert data["deleted_handoffs"] >= 1
        
        # Verify deletion
        verify_response = client.get(f"/api/evaluations/pipelines/{temp_id}")
        assert verify_response.status_code == 404
    
    def test_delete_pipeline_not_found(self, client):
        """Test 404 when deleting non-existent pipeline."""
        response = client.delete("/api/evaluations/pipelines/nonexistent-pipeline")
        assert response.status_code == 404


class TestAPIRobustness:
    """Tests for API robustness and error handling."""
    
    def test_invalid_pagination_params(self, client):
        """Test validation of pagination parameters."""
        # Negative skip
        response = client.get("/api/evaluations/pipelines?skip=-1")
        assert response.status_code == 422
        
        # Limit exceeds maximum
        response = client.get("/api/evaluations/pipelines?limit=1000")
        assert response.status_code == 422
    
    def test_health_check(self, client):
        """Test that health endpoint still works."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
    
    def test_api_documentation_accessible(self, client):
        """Test that API docs are accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        
        # OpenAPI spec should be available
        openapi_response = client.get("/openapi.json")
        assert openapi_response.status_code == 200
        
        spec = openapi_response.json()
        assert "paths" in spec
        # Verify evaluation endpoints are documented
        assert "/api/evaluations/pipelines" in spec["paths"]
        assert "/api/evaluations/comparison/latest" in spec["paths"]


@pytest.mark.parametrize("endpoint,method", [
    ("/api/evaluations/pipelines", "GET"),
    ("/api/evaluations/handoffs", "GET"),
    ("/api/evaluations/comparison/latest", "GET"),
    ("/api/evaluations/stats/by-format", "GET"),
    ("/api/evaluations/stats/summary", "GET"),
])
def test_endpoint_availability(client, endpoint, method):
    """Test that all evaluation endpoints are accessible."""
    if method == "GET":
        response = client.get(endpoint)
        # Should not be 500 (internal error) or 404 (not found route)
        assert response.status_code not in [500, 404]
