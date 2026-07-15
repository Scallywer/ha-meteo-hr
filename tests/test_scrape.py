"""Tests for the dependency-free HTML scraping helpers in scrape.py.

These are the most fragile part of the integration: DHMZ can change table
markup at any time and it would silently break parsing rather than raise
an import/type error, so it's worth pinning the exact expected behavior.
"""
from custom_components.meteo_hr import scrape

CONDITIONS_HTML = """
<table>
<thead>
<tr><th>Postaja</th><th>Smjer</th><th>Brzina</th><th>Temp</th><th>Vrijeme</th></tr>
</thead>
<tbody>
<tr><td>Zagreb-Maksimir</td><td>NE</td><td>2.1</td><td>24.3</td><td>Vedro</td></tr>
<tr><td>Osijek</td><td>E</td><td>1.5</td><td>26.0</td><td>Sun&nbsp;čano</td></tr>
</tbody>
</table>
"""

SELECT_HTML = """
<select id="mengrad" name="grad">
<option value="ZAGREB-MAKSIMIR">Zagreb-Maksimir</option>
<option value="OSIJEK" selected>Osijek</option>
</select>
"""


def test_parse_table_header_reads_thead_th_cells():
    assert scrape.parse_table_header(CONDITIONS_HTML) == [
        "Postaja",
        "Smjer",
        "Brzina",
        "Temp",
        "Vrijeme",
    ]


def test_parse_table_header_missing_thead_returns_empty():
    assert scrape.parse_table_header("<table><tbody></tbody></table>") == []


def test_table_body_html_spans_thead_to_table_end():
    html = "<html><body>preamble<table>\n<thead><tr><th>H</th></tr></thead>\n<tbody><tr><td>Osijek</td></tr></tbody>\n</table>trailer</body></html>"
    body = scrape.table_body_html(html)
    assert "preamble" not in body
    assert "trailer" not in body
    assert "Osijek" in body


def test_parse_table_rows_skips_header_row_and_strips_nbsp():
    rows = scrape.parse_table_rows(scrape.table_body_html(CONDITIONS_HTML))
    assert rows == [
        ["Zagreb-Maksimir", "NE", "2.1", "24.3", "Vedro"],
        ["Osijek", "E", "1.5", "26.0", "Sun čano"],
    ]


def test_parse_table_rows_skips_rows_with_empty_first_cell():
    html = "<tr><td></td><td>ignored</td></tr><tr><td>kept</td></tr>"
    assert scrape.parse_table_rows(html) == [["kept"]]


def test_parse_select_options_extracts_value_label_pairs():
    options = scrape.parse_select_options(SELECT_HTML, "mengrad")
    assert options == [
        ("ZAGREB-MAKSIMIR", "Zagreb-Maksimir"),
        ("OSIJEK", "Osijek"),
    ]


def test_parse_select_options_missing_select_id_returns_empty():
    assert scrape.parse_select_options(SELECT_HTML, "nonexistent") == []


def test_normalize_station_name_is_case_dash_whitespace_insensitive():
    assert scrape.normalize_station_name("Zagreb - Maksimir ") == "zagrebmaksimir"
    assert scrape.normalize_station_name("OSIJEK") == "osijek"


def test_find_station_row_matches_normalized_prefix():
    rows = scrape.parse_table_rows(scrape.table_body_html(CONDITIONS_HTML))
    row = scrape.find_station_row(rows, "Osijek")
    assert row is not None
    assert row[0] == "Osijek"


def test_find_station_row_no_match_returns_none():
    rows = scrape.parse_table_rows(scrape.table_body_html(CONDITIONS_HTML))
    assert scrape.find_station_row(rows, "Split-Marjan") is None
