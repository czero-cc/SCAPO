from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import FileResponse, JSONResponse

from src.core.logging import get_logger
from src.core.models import ModelBestPractices, ModelCategory
from src.services.model_service import ModelService
from src.services.scraper_service import ScraperService

logger = get_logger(__name__)

# Initialize services
model_service = ModelService()
scraper_service = ScraperService()

# Routers
practices_router = APIRouter()
scraper_router = APIRouter()


@practices_router.get("/", response_model=Dict[str, List[str]])
async def list_models(
    category: Optional[ModelCategory] = Query(None, description="Filter by category"),
) -> Dict[str, List[str]]:
    """List all available models, optionally filtered by category."""
    try:
        models = await model_service.list_models(category=category)
        return models
    except Exception as e:
        logger.error("Error listing models", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list models")


@practices_router.get("/search", response_model=List[Dict[str, Any]])
async def search_models(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results"),
) -> List[Dict[str, Any]]:
    """Search for models by name, tags, or content."""
    try:
        results = await model_service.search_models(query=q, limit=limit)
        return results
    except Exception as e:
        logger.error("Error searching models", query=q, error=str(e))
        raise HTTPException(status_code=500, detail="Search failed")


@practices_router.get("/{category}/{model_id}/all", response_model=ModelBestPractices)
async def get_model_all_practices(
    category: ModelCategory = Path(..., description="Model category"),
    model_id: str = Path(..., description="Model ID"),
) -> ModelBestPractices:
    """Get all best practices for a specific model."""
    try:
        practices = await model_service.get_model_practices(
            category=category,
            model_id=model_id,
        )
        if not practices:
            raise HTTPException(
                status_code=404,
                detail=f"Model {model_id} not found in category {category}",
            )
        return practices
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error getting model practices",
            category=category,
            model_id=model_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to get model practices")


@practices_router.get("/{category}/{model_id}/prompting")
async def get_model_prompting(
    category: ModelCategory = Path(..., description="Model category"),
    model_id: str = Path(..., description="Model ID"),
    format: str = Query("json", description="Response format (json or markdown)"),
) -> Any:
    """Get prompting best practices for a model."""
    try:
        if format == "markdown":
            file_path = await model_service.get_prompting_file(
                category=category,
                model_id=model_id,
            )
            if not file_path:
                raise HTTPException(status_code=404, detail="Prompting guide not found")
            return FileResponse(file_path, media_type="text/markdown")
        else:
            practices = await model_service.get_model_practices(
                category=category,
                model_id=model_id,
            )
            if not practices:
                raise HTTPException(status_code=404, detail="Model not found")
            
            return {
                "model_id": model_id,
                "prompt_structure": practices.prompt_structure,
                "prompt_examples": practices.prompt_examples,
                "prompt_tips": practices.prompt_tips,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting prompting guide", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get prompting guide")


@practices_router.get("/{category}/{model_id}/parameters")
async def get_model_parameters(
    category: ModelCategory = Path(..., description="Model category"),
    model_id: str = Path(..., description="Model ID"),
) -> Dict[str, Any]:
    """Get parameter recommendations for a model."""
    try:
        practices = await model_service.get_model_practices(
            category=category,
            model_id=model_id,
        )
        if not practices:
            raise HTTPException(status_code=404, detail="Model not found")
        
        return {
            "model_id": model_id,
            "parameters": [param.model_dump() for param in practices.parameters],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting parameters", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get parameters")


@practices_router.get("/{category}/{model_id}/pitfalls")
async def get_model_pitfalls(
    category: ModelCategory = Path(..., description="Model category"),
    model_id: str = Path(..., description="Model ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
) -> Dict[str, Any]:
    """Get common pitfalls and mistakes for a model."""
    try:
        practices = await model_service.get_model_practices(
            category=category,
            model_id=model_id,
        )
        if not practices:
            raise HTTPException(status_code=404, detail="Model not found")
        
        pitfalls = practices.pitfalls
        if severity:
            pitfalls = [p for p in pitfalls if p.severity == severity]
        
        return {
            "model_id": model_id,
            "pitfalls": [p.model_dump() for p in pitfalls],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting pitfalls", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get pitfalls")


@practices_router.get("/{category}/{model_id}/metadata")
async def get_model_metadata(
    category: ModelCategory = Path(..., description="Model category"),
    model_id: str = Path(..., description="Model ID"),
) -> Dict[str, Any]:
    """Get metadata about model best practices."""
    try:
        metadata = await model_service.get_model_metadata(
            category=category,
            model_id=model_id,
        )
        if not metadata:
            raise HTTPException(status_code=404, detail="Model metadata not found")
        return metadata.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting metadata", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get metadata")


# Scraper endpoints

@scraper_router.post("/run")
async def run_scraper(
    source: str = Query(..., description="Source to scrape (reddit, discord, etc.)"),
    target: Optional[str] = Query(None, description="Specific target (subreddit, channel)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum posts to scrape"),
    llm_max_chars: Optional[int] = Query(None, ge=100, le=50000, description="Maximum characters to send to LLM processor"),
) -> Dict[str, Any]:
    """Trigger a scraping run for a specific source."""
    try:
        result = await scraper_service.run_scraper(
            source=source,
            target=target,
            limit=limit,
            llm_max_chars=llm_max_chars,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error running scraper", source=source, error=str(e))
        raise HTTPException(status_code=500, detail="Scraping failed")


@scraper_router.get("/status")
async def get_scraper_status() -> Dict[str, Any]:
    """Get status of all scrapers."""
    try:
        status = await scraper_service.get_status()
        return status
    except Exception as e:
        logger.error("Error getting scraper status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get status")


@scraper_router.get("/sources")
async def list_sources() -> Dict[str, List[str]]:
    """List available scraping sources and their targets."""
    try:
        sources = await scraper_service.list_sources()
        return sources
    except Exception as e:
        logger.error("Error listing sources", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list sources")