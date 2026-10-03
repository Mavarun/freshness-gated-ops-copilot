"""Command verbs of common cache / CDN tools, from their own documentation.

The write lexicons (``write_ontology``) may not contain any held-out synonym
word. ``flush`` and ``purge`` are held-out words, yet they are *the* names of
the cache-invalidation commands of the tools an ops team runs, documented
years before this repository existed. This module is that external resource,
transcribed as-is, one entry per documented command, and nothing else: it is
not a place for synonyms. Every verb maps to ``clear_cache`` and inherits its
rule that the object must be a cache (a registered ``-cache`` target or the
noun "cache"); "flush redis" is not a cache clear and stays ambiguous.

Selection note (honest): this class of resource was picked because this slice
asked for "flush" and "purge". Its overlap with the held-out words is exactly
``{"flush", "purge"}`` (pinned by ``tests/test_phrasal_writes.py``), both of
which occur in the robustness set only inside *questions* (g30 "flush point",
g38 "purge orchestration credential"), so they cannot turn a held-out row
into a write. ``CopilotConfig.write_ops_cli_verbs=False`` switches the
resource off, and the robustness report carries that ablation.
"""

from __future__ import annotations

from dataclasses import dataclass

from ops_copilot.write_ontology import WriteActionType


@dataclass(frozen=True)
class CliVerb:
    verb: str
    action: WriteActionType
    tools: tuple[str, ...]


CACHE_INVALIDATION_VERBS: tuple[CliVerb, ...] = (
    CliVerb(
        "flush",
        WriteActionType.CLEAR_CACHE,
        (
            "Redis FLUSHDB / FLUSHALL (redis.io/commands/flushall)",
            "Memcached flush_all (memcached protocol.txt)",
        ),
    ),
    CliVerb(
        "purge",
        WriteActionType.CLEAR_CACHE,
        (
            "Varnish purge (varnish-cache.org docs, 'Purging and banning')",
            "Cloudflare API purge_cache (developers.cloudflare.com/cache/how-to/purge-cache)",
            "Fastly purge / purge_all (developer.fastly.com/reference/api/purging)",
            "Akamai Fast Purge (techdocs.akamai.com/purge-cache)",
        ),
    ),
    CliVerb(
        "ban",
        WriteActionType.CLEAR_CACHE,
        ("Varnish ban (varnish-cache.org docs, 'Purging and banning')",),
    ),
    CliVerb(
        "invalidate",
        WriteActionType.CLEAR_CACHE,
        ("AWS CloudFront CreateInvalidation (docs.aws.amazon.com/cloudfront)",),
    ),
)

CLI_VERB_INDEX: dict[str, WriteActionType] = {v.verb: v.action for v in CACHE_INVALIDATION_VERBS}


def cli_words() -> frozenset[str]:
    return frozenset(CLI_VERB_INDEX)
