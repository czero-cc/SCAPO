"""SCAPO - Stay Calm and Prompt On"""

import warnings

# Suppress pydantic V2 migration warnings from third-party libraries (specifically litellm)
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=".*Valid config keys have changed in V2.*",
    module="pydantic._internal._config"
)

warnings.filterwarnings(
    "ignore", 
    category=DeprecationWarning,
    message=".*Support for class-based `config` is deprecated.*",
    module="pydantic.warnings"
)