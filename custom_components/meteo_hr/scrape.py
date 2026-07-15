"""Small, dependency-free HTML table/select scraping helpers for meteo.hr pages.

These pages are plain server-rendered HTML tables (no JSON/XML API for this data),
so we extract what we need with regexes rather than pulling in a full HTML parser
dependency. Kept intentionally narrow: strip tags per cell, split rows on <tr>.
"""
from __future__ import annotations

import re

_OPTION_RE = re.compile(r'<option value="([^"]*)"[^>]*>([^<]*)</option>')
_SELECT_RE_TEMPLATE = r'<select[^>]*id="{}"[^>]*>(.*?)</select>'
_TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_TH_RE = re.compile(r"<th[^>]*>(.*?)</th>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def _cell_text(cell_html: str) -> str:
    text = _TAG_RE.sub("", cell_html)
    text = text.replace("&nbsp;", " ")
    return " ".join(text.split())


def parse_table_rows(html: str, cell_re: re.Pattern = _TD_RE) -> list[list[str]]:
    """Parse an HTML table into a list of cell-text rows, skipping empty-first-cell rows."""
    rows = []
    for tr_html in _TR_RE.findall(html):
        cells = [_cell_text(cell) for cell in cell_re.findall(tr_html)]
        if cells and cells[0]:
            rows.append(cells)
    return rows


def parse_table_header(html: str) -> list[str]:
    """Parse the first <thead>...</thead> row into cell text (th cells)."""
    head_start = html.find("<thead")
    head_end = html.find("</thead>", head_start)
    if head_start == -1 or head_end == -1:
        return []
    head_html = html[head_start:head_end]
    rows = parse_table_rows(head_html, cell_re=_TH_RE)
    return rows[0] if rows else []


def table_body_html(html: str) -> str:
    """Return the substring from the first <thead> to the following </table>."""
    start = html.find("<thead")
    if start == -1:
        return html
    end = html.find("</table>", start)
    return html[start:end] if end != -1 else html[start:]


def parse_select_options(html: str, select_id: str) -> list[tuple[str, str]]:
    """Parse <option value="...">label</option> pairs out of a specific <select id="...">."""
    match = re.search(_SELECT_RE_TEMPLATE.format(re.escape(select_id)), html, re.S)
    if not match:
        return []
    return [
        (value.strip(), _cell_text(label))
        for value, label in _OPTION_RE.findall(match.group(1))
    ]


def normalize_station_name(name: str) -> str:
    """Case/whitespace/dash-insensitive key for matching the same station across pages."""
    return re.sub(r"[\s\-]+", "", name.strip().lower())


def find_station_row(rows: list[list[str]], station_name: str) -> list[str] | None:
    """Return the first row whose first cell matches station_name (normalized substring)."""
    target = normalize_station_name(station_name)
    for row in rows:
        if normalize_station_name(row[0]).startswith(target):
            return row
    return None
