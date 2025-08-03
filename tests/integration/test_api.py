import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.core.models import ModelBestPractices, ModelCategory


class TestAPI:
    """Integration tests for API endpoints."""

    def test_root_endpoint(self, test_client: TestClient):
        """Test root endpoint."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "SOTA Practices API"
        assert "endpoints" in data

    def test_health_endpoint(self, test_client: TestClient):
        """Test health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_metrics_endpoint(self, test_client: TestClient):
        """Test metrics endpoint."""
        response = test_client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

    def test_api_authentication(self, test_client: TestClient):
        """Test API key authentication."""
        # Without API key
        response = test_client.get("/api/v1/models/")
        assert response.status_code == 403
        
        # With wrong API key
        response = test_client.get(
            "/api/v1/models/",
            headers={"X-API-Key": "wrong_key"}
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_models(self, test_client: TestClient, api_headers: dict):
        """Test listing models endpoint."""
        with patch("src.services.model_service.ModelService.list_models") as mock_list:
            mock_list.return_value = {
                "text": ["gpt-4", "claude-3"],
                "image": ["stable-diffusion", "dalle-3"],
            }
            
            response = test_client.get("/api/v1/models/", headers=api_headers)
            assert response.status_code == 200
            data = response.json()
            assert "text" in data
            assert "gpt-4" in data["text"]

    @pytest.mark.asyncio
    async def test_list_models_by_category(self, test_client: TestClient, api_headers: dict):
        """Test listing models filtered by category."""
        with patch("src.services.model_service.ModelService.list_models") as mock_list:
            mock_list.return_value = {
                "text": ["gpt-4", "claude-3"],
            }
            
            response = test_client.get(
                "/api/v1/models/?category=text",
                headers=api_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert "text" in data
            assert "image" not in data

    @pytest.mark.asyncio
    async def test_search_models(self, test_client: TestClient, api_headers: dict):
        """Test model search endpoint."""
        with patch("src.services.model_service.ModelService.search_models") as mock_search:
            mock_search.return_value = [
                {
                    "model_id": "gpt-4",
                    "category": "text",
                    "match_type": "name",
                    "score": 1.0,
                }
            ]
            
            response = test_client.get(
                "/api/v1/models/search?q=gpt",
                headers=api_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["model_id"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_get_model_practices(self, test_client: TestClient, api_headers: dict, sample_model_data):
        """Test getting all practices for a model."""
        with patch("src.services.model_service.ModelService.get_model_practices") as mock_get:
            mock_get.return_value = ModelBestPractices(**sample_model_data)
            
            response = test_client.get(
                "/api/v1/models/text/test-model/all",
                headers=api_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["model_id"] == "test-model"
            assert data["category"] == "text"

    @pytest.mark.asyncio
    async def test_get_model_prompting(self, test_client: TestClient, api_headers: dict, sample_model_data):
        """Test getting prompting guide."""
        with patch("src.services.model_service.ModelService.get_model_practices") as mock_get:
            mock_get.return_value = ModelBestPractices(**sample_model_data)
            
            response = test_client.get(
                "/api/v1/models/text/test-model/prompting",
                headers=api_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert "prompt_structure" in data
            assert "prompt_examples" in data

    @pytest.mark.asyncio
    async def test_get_model_parameters(self, test_client: TestClient, api_headers: dict, sample_model_data):
        """Test getting model parameters."""
        with patch("src.services.model_service.ModelService.get_model_practices") as mock_get:
            mock_get.return_value = ModelBestPractices(**sample_model_data)
            
            response = test_client.get(
                "/api/v1/models/text/test-model/parameters",
                headers=api_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert "parameters" in data
            assert len(data["parameters"]) == 1
            assert data["parameters"][0]["name"] == "temperature"

    @pytest.mark.asyncio
    async def test_get_model_pitfalls(self, test_client: TestClient, api_headers: dict, sample_model_data):
        """Test getting model pitfalls."""
        with patch("src.services.model_service.ModelService.get_model_practices") as mock_get:
            mock_get.return_value = ModelBestPractices(**sample_model_data)
            
            response = test_client.get(
                "/api/v1/models/text/test-model/pitfalls",
                headers=api_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert "pitfalls" in data
            assert len(data["pitfalls"]) == 1

    @pytest.mark.asyncio
    async def test_run_scraper(self, test_client: TestClient, api_headers: dict):
        """Test running a scraper."""
        with patch("src.services.scraper_service.ScraperService.run_scraper") as mock_run:
            mock_run.return_value = {
                "status": "success",
                "source": "reddit",
                "posts_scraped": 10,
                "practices_extracted": 5,
            }
            
            response = test_client.post(
                "/api/v1/scrapers/run?source=reddit&limit=10",
                headers=api_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["posts_scraped"] == 10

    @pytest.mark.asyncio
    async def test_scraper_status(self, test_client: TestClient, api_headers: dict):
        """Test getting scraper status."""
        with patch("src.services.scraper_service.ScraperService.get_status") as mock_status:
            mock_status.return_value = {
                "scrapers": {
                    "reddit": {
                        "status": "idle",
                        "last_run": None,
                        "total_posts": 0,
                    }
                },
                "total_scrapers": 1,
                "active_scrapers": 0,
            }
            
            response = test_client.get(
                "/api/v1/scrapers/status",
                headers=api_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert "scrapers" in data
            assert "reddit" in data["scrapers"]

    def test_error_handling(self, test_client: TestClient, api_headers: dict):
        """Test API error handling."""
        # Test 404
        response = test_client.get(
            "/api/v1/models/text/non-existent/all",
            headers=api_headers
        )
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == 404