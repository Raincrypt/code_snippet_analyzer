from app.services.static_python import analyse


def rules(code: str) -> list[str]:
    return [f.rule for f in analyse(code).findings]


def algorithms(code: str) -> list[str]:
    return [a.key for a in analyse(code).algorithms]


# ---- parsing ---------------------------------------------------------------------------------


def test_syntax_error_is_reported_with_its_line() -> None:
    result = analyse("def f(:\n    pass\n")
    assert result.syntax_error is not None and result.syntax_error[0] == 1
    assert not result.parsed and result.findings == []


def test_functions_and_metrics() -> None:
    code = (
        "def a():\n    for x in y:\n        if x:\n            pass\n\n\ndef b():\n    return 1\n"
    )
    result = analyse(code)
    assert [(f.name, f.start_line, f.end_line) for f in result.functions] == [
        ("a", 1, 4),
        ("b", 7, 8),
    ]
    assert result.longest_function_lines == 4
    assert result.max_nesting_depth == 2
    assert result.functions[0].loop_depth == 1
    assert result.only_definitions


# ---- SQL -------------------------------------------------------------------------------------


def test_sql_built_from_strings_is_flagged() -> None:
    for query in (
        '"SELECT * FROM t WHERE a = \'" + name + "\'"',
        'f"SELECT * FROM t WHERE a = {name}"',
        '"SELECT * FROM t WHERE a = %s" % name',
        '"SELECT * FROM t WHERE a = {}".format(name)',
    ):
        assert rules(f"def f(cur, name):\n    cur.execute({query})\n") == ["sql-injection"], query


def test_parameterised_or_constant_sql_is_not_flagged() -> None:
    assert rules('def f(cur, n):\n    cur.execute("SELECT 1 WHERE a = ?", (n,))\n') == []
    assert rules('def f(cur):\n    cur.execute("SELECT 1" + " FROM t")\n') == []
    assert rules('def f(cur):\n    cur.execute(f"SELECT 1")\n') == []


# ---- other security rules ----------------------------------------------------------------------


def test_eval_of_non_literal_is_flagged_but_constants_are_not() -> None:
    assert rules("def f(s):\n    return eval(s)\n") == ["eval-exec"]
    assert rules('def f():\n    return eval("1 + 1")\n') == []


def test_shell_true_is_flagged_only_when_true() -> None:
    assert rules("import subprocess\nsubprocess.run(cmd, shell=True)\n") == ["shell-true"]
    assert rules('import subprocess\nsubprocess.run(["ls"], shell=False)\n') == []


# ---- mutable defaults --------------------------------------------------------------------------


def test_mutable_default_severity_depends_on_mutation() -> None:
    changed = analyse("def f(x, items=[]):\n    items.append(x)\n    return items\n")
    assert [(f.rule, f.severity, f.line) for f in changed.findings] == [
        ("mutable-default", "error", 1)
    ]
    unchanged = analyse("def f(x, items=[]):\n    return len(items)\n")
    assert unchanged.findings[0].severity == "warning"


def test_other_mutable_defaults_and_safe_ones() -> None:
    assert rules("def f(a={}): pass\n") == ["mutable-default"]
    assert rules("def f(*, a=set()): pass\n") == ["mutable-default"]
    assert rules("def f(a=None, b=(), c=0, d='x'): pass\n") == []


# ---- files -------------------------------------------------------------------------------------


def test_unclosed_file() -> None:
    assert rules("def f(p):\n    h = open(p)\n    return h.read()\n") == ["unclosed-file"]


def test_closed_escaping_or_with_files_are_fine() -> None:
    assert (
        rules("def f(p):\n    h = open(p)\n    d = h.read()\n    h.close()\n    return d\n") == []
    )
    assert rules("def f(p):\n    with open(p) as h:\n        return h.read()\n") == []
    assert rules("def f(p):\n    h = open(p)\n    return h\n") == []  # the caller closes it
    assert rules("def f(p):\n    h = open(p)\n    use(h)\n") == []


# ---- recursion and loops -----------------------------------------------------------------------


def test_exponential_recursion() -> None:
    code = "def fib(n):\n    if n < 2:\n        return n\n    return fib(n - 1) + fib(n - 2)\n"
    found = analyse(code).findings
    assert [(f.rule, f.line) for f in found] == [("exponential-recursion", 4)]


def test_recursion_that_is_not_exponential_is_left_alone() -> None:
    cached = (
        "from functools import cache\n\n@cache\ndef fib(n):\n    return fib(n - 1) + fib(n - 2)\n"
    )
    assert rules(cached) == []
    assert rules("def fact(n):\n    return 1 if n < 2 else n * fact(n - 1)\n") == []
    hanoi = "def h(n, a, b, c):\n    if n:\n        h(n - 1, a, c, b)\n        h(n - 1, c, b, a)\n"
    assert rules(hanoi) == []


def test_nested_loops_over_the_same_collection() -> None:
    code = (
        "def dup(xs):\n    for i in range(len(xs)):\n        for j in range(i + 1, len(xs)):\n"
        "            if xs[i] == xs[j]:\n                return True\n    return False\n"
    )
    found = analyse(code).findings
    assert [(f.rule, f.severity, f.line, f.end_line) for f in found] == [
        ("nested-loops", "warning", 2, 3)
    ]


def test_nested_loops_over_different_collections_are_fine() -> None:
    assert rules("def f(a, b):\n    for x in a:\n        for y in b:\n            pass\n") == []


def test_bare_except() -> None:
    assert rules("try:\n    pass\nexcept:\n    pass\n") == ["bare-except"]
    assert rules("try:\n    pass\nexcept ValueError:\n    pass\n") == []


# ---- algorithms --------------------------------------------------------------------------------

BINARY = (
    "def s(xs, t):\n    lo, hi = 0, len(xs) - 1\n    while lo <= hi:\n"
    "        mid = (lo + hi) // 2\n"
    "        if xs[mid] == t:\n            return mid\n        if xs[mid] < t:\n"
    "            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1\n"
)


def test_binary_search_is_recognised() -> None:
    assert algorithms(BINARY) == ["binary_search"]


def test_a_while_loop_alone_is_not_binary_search() -> None:
    assert algorithms("def f(n):\n    while n > 0:\n        n -= 1\n") == []


def test_merge_sort_bfs_dfs_bubble_gcd_memo() -> None:
    merge = (
        "def m(xs):\n    if len(xs) <= 1:\n        return xs\n    mid = len(xs) // 2\n"
        "    a = m(xs[:mid])\n    b = m(xs[mid:])\n    out = []\n    while a and b:\n"
        "        out.append(a.pop(0) if a[0] < b[0] else b.pop(0))\n    return out + a + b\n"
    )
    assert algorithms(merge) == ["merge_sort"]
    bfs = (
        "from collections import deque\ndef b(g, s):\n    seen = {s}\n    q = deque([s])\n"
        "    while q:\n        n = q.popleft()\n        for x in g[n]:\n"
        "            if x not in seen:\n"
        "                seen.add(x)\n                q.append(x)\n"
    )
    assert algorithms(bfs) == ["bfs"]
    dfs = (
        "def d(g, n, seen):\n    seen.add(n)\n    for x in g[n]:\n        if x not in seen:\n"
        "            d(g, x, seen)\n"
    )
    assert algorithms(dfs) == ["dfs"]
    stack = (
        "def d(g, s):\n    seen = set()\n    st = [s]\n    while st:\n        n = st.pop()\n"
        "        if n not in seen:\n            seen.add(n)\n            st.extend(g[n])\n"
    )
    assert algorithms(stack) == ["dfs"]
    bubble = (
        "def b(a):\n    for i in range(len(a)):\n        for j in range(len(a) - i - 1):\n"
        "            if a[j] > a[j + 1]:\n                a[j], a[j + 1] = a[j + 1], a[j]\n"
    )
    assert algorithms(bubble) == ["bubble_sort"]
    assert algorithms("def g(a, b):\n    while b:\n        a, b = b, a % b\n    return a\n") == [
        "euclid_gcd"
    ]
    memo = (
        "from functools import cache\n@cache\ndef f(n):\n"
        "    return n if n < 2 else f(n-1) + f(n-2)\n"
    )
    assert algorithms(memo) == ["memoized_recursion"]
    assert analyse(memo).has_memoization


def test_plain_code_matches_no_algorithm() -> None:
    assert algorithms("def add(a, b):\n    return a + b\n") == []
    assert algorithms("def f(xs):\n    return [x * 2 for x in xs]\n") == []
