"""Freshness-gated ops knowledge copilot.

Most RAG demos answer from whatever chunk ranks high. This package refuses
to answer when evidence fails a freshness SLA or a grounding check.
"""

from ops_copilot.config import CopilotConfig, EVAL_CLOCK

__version__ = "0.1.0"
__all__ = ["CopilotConfig", "EVAL_CLOCK", "__version__"]
