"""FastMCP server exposing Library of Congress search.

A thin presentation layer over :class:`LocClient`; all behaviour, caching and
pacing live there, so the MCP tools and the `locgov` CLI cannot drift apart in
what a search means.

The basic tool takes a query and nothing else. Filters are additive complexity in
a tool schema that sits in the model's context permanently, so they are hidden
behind `--enable-advanced-search` at install time, exactly as the sibling servers
do. The CLI always exposes everything.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from fastmcp import FastMCP

from .client import (
    DEFAULT_COLLECTION,
    DEFAULT_LEVEL,
    DEFAULT_PER_PAGE,
    DEFAULT_SORT,
    LocClient,
)

mcp: FastMCP = FastMCP("loc")
_client: LocClient | None = None


def client() -> LocClient:
    """The process-wide client, created on first use."""
    global _client
    if _client is None:
        _client = LocClient()
    return _client


@mcp.tool()
async def search_loc(query: str, page: int = 1) -> dict[str, Any]:
    """Search the Library of Congress historic newspaper full text.

    Searches the Chronicling America collection: American newspapers, 1736-1963,
    including a substantial German-language immigrant press.

    Bare words are ANDed and "quoted phrases" match exactly. There is no boolean
    OR and no NOT - those words, a leading minus, parentheses and | are all
    silently stripped - so each variant of a term needs its own search.

    Results resolve to individual pages. Each carries a `reference` that is both
    the citation URL and the argument for `snippets_loc` and `get_loc_text`.

    Args:
        query: Search terms
        page: Result page number, 1-indexed
    """
    return await client().search(query=query, page=page)


@mcp.tool()
async def snippets_loc(reference: str, query: str) -> dict[str, Any]:
    """Show a query in context on one newspaper page.

    The cheap way to judge a search result without downloading it: returns the
    matched terms in {braces} with the surrounding sentences, and a citation URL.
    Newspaper pages only - books expose full text but no snippet service.

    Args:
        reference: Page reference, as returned by `search_loc`
        query: Terms to locate within the page
    """
    snippets = await client().get_snippets(reference=reference, query=query)
    return {"reference": reference, "query": query, "snippets": snippets}


@mcp.tool()
async def get_loc_text(reference: str) -> dict[str, Any]:
    """Download a page's OCR text, returning the path to the cached file.

    Use when snippets are not enough and the whole page has to be read or
    grepped. Hyphenation broken across line ends is rejoined, so the cached text
    greps the way the search index matched.

    Args:
        reference: Page reference, as returned by `search_loc`
    """
    path = await client().download_text(reference=reference)
    return {"reference": reference, "path": str(path)}


def register_advanced_search() -> None:
    """Add the filtered search tool. Called only when enabled at install time."""

    @mcp.tool()
    async def advanced_search_loc(
        query: str = "",
        page: int = 1,
        per_page: int = DEFAULT_PER_PAGE,
        collection: str = DEFAULT_COLLECTION,
        all_loc: bool = False,
        level: str = DEFAULT_LEVEL,
        from_year: int | None = None,
        to_year: int | None = None,
        language: str | None = None,
        state: str | None = None,
        title: str | None = None,
        sort: str = DEFAULT_SORT,
        include_unreadable: bool = False,
    ) -> dict[str, Any]:
        """Search the Library of Congress with filters.

        Totals here are true match counts rather than a relevance tail, so a
        total may be quoted as a count and `date_asc` is safe on any query.

        Args:
            query: Search terms; may be empty when filtering alone
            page: Result page number, 1-indexed
            per_page: Results per request, up to 150
            collection: Collection slug, default chronicling-america
            all_loc: Search the whole of loc.gov instead of one collection
            level: 'page' to resolve hits to newspaper pages, 'item' for items
            from_year: Earliest year, inclusive
            to_year: Latest year, inclusive
            language: Language facet, e.g. 'german'
            state: US state of publication, e.g. 'wisconsin'
            title: Exact newspaper title facet, copied from a result
            sort: 'relevance', 'date_asc' or 'date_desc'
            include_unreadable: Also return material with no retrievable text
        """
        return await client().search(
            query=query,
            page=page,
            per_page=per_page,
            collection=collection,
            all_loc=all_loc,
            level=level,
            from_year=from_year,
            to_year=to_year,
            language=language,
            state=state,
            title=title,
            sort=sort,
            readable_only=not include_unreadable,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Library of Congress MCP server")
    parser.add_argument(
        "--enable-advanced-search",
        action="store_true",
        help="expose the filtered search tool as well as the basic one",
    )
    args = parser.parse_args()

    if args.enable_advanced_search:
        register_advanced_search()

    try:
        mcp.run()
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
