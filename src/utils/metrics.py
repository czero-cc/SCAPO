from prometheus_client import Counter, Histogram, Gauge, Info

# API metrics
api_request_counter = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"],
)

api_request_duration = Histogram(
    "api_request_duration_seconds",
    "API request duration",
    ["method", "endpoint"],
)

# Scraper metrics
scraper_runs_counter = Counter(
    "scraper_runs_total",
    "Total scraper runs",
    ["source", "status"],
)

scraper_posts_processed = Counter(
    "scraper_posts_processed_total",
    "Total posts processed by scrapers",
    ["source"],
)

scraper_practices_extracted = Counter(
    "scraper_practices_extracted_total",
    "Total practices extracted",
    ["source", "type"],
)

scraper_last_run = Gauge(
    "scraper_last_run_timestamp",
    "Timestamp of last scraper run",
    ["source"],
)

# Model metrics
models_total = Gauge(
    "models_total",
    "Total number of models in the system",
    ["category"],
)

model_queries_counter = Counter(
    "model_queries_total",
    "Total model queries",
    ["model_id", "query_type"],
)

# System info
system_info = Info(
    "sota_practices_info",
    "System information",
)


def setup_metrics():
    """Initialize system metrics."""
    system_info.info({
        "version": "0.1.0",
        "service": "sota-practices",
        "organization": "Fiefworks",
    })