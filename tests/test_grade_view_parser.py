"""
Grade view parser tests over hand-built markup.

The grade view has a structural quirk worth pinning down: the per-course detail
response nests the statistics and marks tables *inside* a cell of the outer
grade table, so a naive "find the table containing X" picks the wrapper. The
parser must select the innermost (leaf) tables.
"""

from vitap_vtop_client.parsers.grade_view_parser import (
    parse_grade_view,
    parse_grade_view_detail,
)


def _row(cells: list[str], tag: str = "td") -> str:
    return "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"


TILES_HEADER = _row(
    [
        "Sl.No.", "Course Code", "Course Title", "Course Type",
        "Grading Type", "Grand Total", "Grade", "View Mark",
    ],
    tag="th",
)


def _tile_row(sl, code, title, ctype, gtype, total, grade, course_id):
    view = (
        f'<button onclick="javascript:getGradeViewDetails(\'{course_id}\');">'
        "<span>+</span></button>"
    )
    return _row([sl, code, title, ctype, gtype, total, grade, view])


def test_grade_view_lists_courses_with_ids():
    html = (
        '<table class="table table-hover table-bordered">'
        + TILES_HEADER
        + _tile_row("1", "CSE1008", "Theory of Computation", "Theory Only",
                    "RG", "63", "B", "AM_CSE1008_00200")
        + _tile_row("2", "CSE4004", "Web Technologies", "Embedded Theory and Lab",
                    "RG", "90", "S", "AM_CSE4004_00400")
        + "</table>"
    )

    courses = parse_grade_view(html)

    assert len(courses) == 2
    assert courses[0].course_code == "CSE1008"
    assert courses[0].grade == "B"
    assert courses[0].grand_total == "63"
    # The id, needed for the detail lookup, comes from the View Mark button.
    assert courses[0].course_id == "AM_CSE1008_00200"
    assert courses[1].course_id == "AM_CSE4004_00400"


def test_grade_view_skips_non_data_rows():
    html = (
        "<table>"
        + TILES_HEADER
        + _row([])  # spacer
        + _tile_row("1", "CSE1008", "TOC", "Theory Only", "RG", "63", "B", "AM_X")
        + "</table>"
    )

    assert len(parse_grade_view(html)) == 1


# The detail response: an outer grade table whose last cell holds the nested
# statistics and marks tables. This mirrors what live VTOP returns.
_STATS_TABLE = (
    '<table class="table table-striped table-bordered">'
    + _row(["Class Strength", "Grading Strength", "Mean", "SD", "Range of Grades"], tag="th")
    + _row(["S", "A", "B", "C", "D", "E", "F"])
    + _row(["71", "62", "60.4", "13.71", ">=81#", ">=67 and <81", ">=54 and <67",
            ">=47 and <54", ">=40 and <47", ">=33 and <40", "<33"])
    + _row(["# As Per 'S' Grade Policy"])
    + "</table>"
)

_MARKS_TABLE = (
    '<table class="table table-striped table-bordered">'
    + _row(["Class Number : AP2025264000388", "Course Type : Theory Only"])
    + _row(["Sl.No.", "Mark Title", "Max. Mark", "Weightage %", "Status",
            "Scored Mark", "Weightage Mark"], tag="th")
    + _row(["1", "CAT1", "50", "15", "Present", "16.0", "4.8"])
    + _row(["2", "FAT", "100", "40", "Present", "67.0", "26.8"])
    + _row(["Total", "63"])
    + "</table>"
)

_DETAIL_HTML = (
    '<table class="table table-hover table-bordered">'
    + TILES_HEADER
    + _tile_row("1", "CSE1008", "TOC", "Theory Only", "RG", "63", "B", "AM_X")
    + "<tr><td>" + _STATS_TABLE + _MARKS_TABLE + "</td></tr>"
    + "</table>"
)


def test_detail_reads_marks_from_the_nested_leaf_table():
    """Must not pick the outer wrapper, which also 'contains' Mark Title."""
    detail = parse_grade_view_detail(_DETAIL_HTML)

    assert detail.class_number == "AP2025264000388"
    assert detail.course_type == "Theory Only"
    assert detail.total == "63"
    titles = [m.mark_title for m in detail.marks]
    # Only real components, not the tile row's course code.
    assert titles == ["CAT1", "FAT"]
    assert detail.marks[0].scored_mark == "16.0"
    assert detail.marks[1].max_mark == "100"


def test_detail_reads_class_statistics():
    stats = parse_grade_view_detail(_DETAIL_HTML).statistics

    assert stats.class_strength == "71"
    assert stats.grading_strength == "62"
    assert stats.mean == "60.4"
    assert stats.sd == "13.71"
    ranges = {g.grade: g.range for g in stats.grade_ranges}
    assert ranges["S"] == ">=81#"
    assert ranges["F"] == "<33"


def test_detail_is_empty_when_nothing_rendered():
    detail = parse_grade_view_detail("<html><body>no data</body></html>")

    assert detail.marks == []
    assert detail.total == ""
    assert detail.statistics.grade_ranges == []
