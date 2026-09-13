"""Freshness-gated ops knowledge copilot.

Most RAG demos answer from whatever chunk ranks high. This package refuses
to answer when evidence fails a freshness SLA or a grounding check.
"""

from ops_copilot.config import CopilotConfig, EVAL_CLOCK
from ops_copilot.pipeline import Copilot, run_query
from ops_copilot.types import CopilotResult, Decision

__version__ = "0.1.0"
__all__ = [
    "Copilot",
    "CopilotConfig",
    "CopilotResult",
    "Decision",
    "EVAL_CLOCK",
    "run_query",
    "__version__",
]
