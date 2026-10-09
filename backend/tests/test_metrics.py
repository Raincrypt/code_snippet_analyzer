from app.services.metrics import measure


def test_counts_code_comment_and_blank_lines() -> None:
    m = measure("# note\nx = 1\n\ny = 2\n")
    assert (m.total_lines, m.code_lines, m.comment_lines, m.blank_lines) == (4, 2, 1, 1)


def test_finds_the_longest_line() -> None:
    assert measure("ab\nabcdef\nabc").longest_line == 6


def test_empty_code_is_all_zero() -> None:
    m = measure("")
    assert (m.total_lines, m.code_lines, m.longest_line) == (0, 0, 0)


def test_parser_based_figures_are_not_invented() -> None:
    m = measure("def f():\n    pass\n")
    assert m.function_count is None and m.max_nesting_depth is None
