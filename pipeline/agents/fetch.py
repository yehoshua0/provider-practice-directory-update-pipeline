import logging

from pipeline.sources.nppes import fetch_nppes
from pipeline.sources.cms import fetch_cms
from pipeline.sources.board.florida import fetch_florida_board
from pipeline.sources.website import fetch_website
from pipeline.state import PipelineState

log = logging.getLogger(__name__)


def fetch_node(state: PipelineState) -> PipelineState:
    record = state["record"]
    npi = record["npi"]
    raw: dict[str, dict | None] = {}

    for source_name, fetcher, args in [
        ("nppes",   fetch_nppes,         (npi,)),
        ("cms",     fetch_cms,           (npi,)),
        ("board",   fetch_florida_board, (npi, record["provider_name"])),
        ("website", fetch_website,       (record["website"],)),
    ]:
        try:
            raw[source_name] = fetcher(*args)
        except Exception as e:
            log.warning("fetch_node: %s failed for %s: %s", source_name, npi, e)
            raw[source_name] = None

    return {**state, "raw_sources": raw}
