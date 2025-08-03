import pytest
from datetime import datetime

from src.core.models import (
    ModelBestPractices,
    ModelCategory,
    Parameter,
    Pitfall,
    PromptExample,
    ScrapedPost,
    SourceType,
)


class TestModelBestPractices:
    """Test ModelBestPractices model."""

    def test_model_creation(self, sample_model_data):
        """Test creating a ModelBestPractices instance."""
        model = ModelBestPractices(**sample_model_data)
        
        assert model.model_id == "test-model"
        assert model.category == ModelCategory.TEXT
        assert len(model.prompt_examples) == 1
        assert len(model.parameters) == 1
        assert len(model.pitfalls) == 1

    def test_model_id_validation(self):
        """Test model_id validation."""
        # Valid model IDs
        valid_ids = ["gpt-4", "stable_diffusion", "wan2.2", "claude-3"]
        for model_id in valid_ids:
            model = ModelBestPractices(
                model_id=model_id,
                model_name="Test",
                category=ModelCategory.TEXT,
                version="1.0.0",
                prompt_structure="Test",
            )
            assert model.model_id == model_id.lower()

        # Invalid model ID
        with pytest.raises(ValueError):
            ModelBestPractices(
                model_id="invalid model!",
                model_name="Test",
                category=ModelCategory.TEXT,
                version="1.0.0",
                prompt_structure="Test",
            )

    def test_model_defaults(self):
        """Test default values."""
        model = ModelBestPractices(
            model_id="test",
            model_name="Test",
            category=ModelCategory.TEXT,
            version="1.0.0",
            prompt_structure="Test",
        )
        
        assert model.prompt_examples == []
        assert model.parameters == []
        assert model.pitfalls == []
        assert model.tags == []
        assert model.related_models == []
        assert isinstance(model.last_updated, datetime)


class TestParameter:
    """Test Parameter model."""

    def test_parameter_creation(self):
        """Test creating a Parameter instance."""
        param = Parameter(
            name="temperature",
            type="float",
            default=0.7,
            recommended=0.3,
            range={"min": 0.0, "max": 1.0},
            description="Controls randomness",
            impact="Lower is more deterministic",
        )
        
        assert param.name == "temperature"
        assert param.type == "float"
        assert param.default == 0.7
        assert param.recommended == 0.3
        assert param.range["min"] == 0.0
        assert param.range["max"] == 1.0

    def test_parameter_without_range(self):
        """Test parameter without range."""
        param = Parameter(
            name="stop",
            type="array",
            default=None,
            recommended=["\\n"],
            description="Stop sequences",
            impact="Controls where generation stops",
        )
        
        assert param.range is None
        assert param.recommended == ["\\n"]


class TestPitfall:
    """Test Pitfall model."""

    def test_pitfall_creation(self):
        """Test creating a Pitfall instance."""
        pitfall = Pitfall(
            title="Test Pitfall",
            description="This is a test pitfall",
            example="Bad: test\nGood: test",
            solution="Do this instead",
            severity="high",
        )
        
        assert pitfall.title == "Test Pitfall"
        assert pitfall.severity == "high"
        assert pitfall.example is not None

    def test_pitfall_without_example(self):
        """Test pitfall without example."""
        pitfall = Pitfall(
            title="Test",
            description="Description",
            solution="Solution",
            severity="low",
        )
        
        assert pitfall.example is None
        assert pitfall.severity == "low"


class TestPromptExample:
    """Test PromptExample model."""

    def test_prompt_example_creation(self):
        """Test creating a PromptExample instance."""
        example = PromptExample(
            prompt="Test prompt",
            explanation="Why this works",
            output_preview="Expected output",
            tags=["test", "example"],
        )
        
        assert example.prompt == "Test prompt"
        assert example.explanation == "Why this works"
        assert example.output_preview == "Expected output"
        assert len(example.tags) == 2

    def test_prompt_example_minimal(self):
        """Test minimal prompt example."""
        example = PromptExample(
            prompt="Test",
            explanation="Explanation",
        )
        
        assert example.output_preview is None
        assert example.tags == []


class TestScrapedPost:
    """Test ScrapedPost model."""

    def test_scraped_post_creation(self, sample_scraped_post):
        """Test creating a ScrapedPost instance."""
        post = ScrapedPost(**sample_scraped_post)
        
        assert post.source_type == SourceType.REDDIT
        assert post.post_id == "test123"
        assert post.score == 100
        assert post.relevance_score == 0.8
        assert "tips" in post.extracted_practices
        assert post.metadata["subreddit"] == "test"

    def test_scraped_post_minimal(self):
        """Test minimal scraped post."""
        post = ScrapedPost(
            source_type=SourceType.REDDIT,
            post_id="123",
            url="https://example.com",
            content="Content",
            author="author",
            created_at=datetime.utcnow(),
            relevance_score=0.5,
        )
        
        assert post.title is None
        assert post.score == 0
        assert post.extracted_practices == {}
        assert post.metadata == {}