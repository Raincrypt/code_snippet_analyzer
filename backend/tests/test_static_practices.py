"""Bad-practice rules and the harder algorithm detectors. Each rule has a case where it must fire
and a close lookalike where it must stay quiet: a rule that cries wolf is worse than none."""

import json
from pathlib import Path

import pytest

from app.services.static_python import analyse


def rules(code: str) -> list[str]:
    return [f.rule for f in analyse(code).findings]


def algorithms(code: str) -> list[str]:
    return [a.key for a in analyse(code).algorithms]


def line_of(code: str, rule: str) -> int:
    return next(f.line for f in analyse(code).findings if f.rule == rule)


# ---- security ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "rule"),
    [
        ('PASSWORD = "hunter2-prod"\n', "hardcoded-secret"),
        ('connect(user="a", api_key="sk-12345")\n', "hardcoded-secret"),
        ("import pickle\ndef f(b):\n    return pickle.loads(b)\n", "unsafe-deserialization"),
        ("import yaml\ndef f(t):\n    return yaml.load(t)\n", "yaml-load"),
        ("import requests\nrequests.get(u, verify=False, timeout=3)\n", "tls-verify-off"),
        ("import requests\nrequests.get(u)\n", "http-no-timeout"),
        ('import os\ndef f(h):\n    os.system("ping " + h)\n', "os-system"),
        ("import tempfile\np = tempfile.mktemp()\n", "mktemp"),
        ("app.run(debug=True)\n", "debug-server"),
        (
            "import tarfile\nwith tarfile.open(p) as t:\n    t.extractall(d)\n",
            "tar-extractall",
        ),
        (
            "import hashlib\ndef hash_password(p):\n    return hashlib.md5(p.encode()).hexdigest()\n",  # noqa: E501
            "weak-hash",
        ),
    ],
)
def test_security_rule_fires(code: str, rule: str) -> None:
    assert rule in rules(code)


@pytest.mark.parametrize(
    "code",
    [
        'PASSWORD = os.environ["PASSWORD"]\n',
        'PASSWORD_PROMPT = "Enter password: "\n',
        'TOKEN = ""\n',
        'LABEL = "hunter2-prod"\n',
        "import pickle\npickle.loads(b'abc')\n",
        "import yaml\nyaml.load(t, Loader=yaml.SafeLoader)\nyaml.safe_load(t)\n",
        "import requests\nrequests.get(u, timeout=3)\n",
        'import os\nos.system("clear")\n',
        "import tempfile\ntempfile.mkstemp()\n",
        "app.run(debug=False)\n",
        "import tarfile\nwith tarfile.open(p) as t:\n    t.extractall(d, filter='data')\n",
        "import zipfile\nwith zipfile.ZipFile(p) as z:\n    z.extractall(d)\n",
        "import hashlib\ndef etag(data):\n    return hashlib.md5(data).hexdigest()\n",
        "import hashlib\ndef f(p):\n    return hashlib.sha256(p).hexdigest()\n",
    ],
)
def test_security_rule_stays_quiet(code: str) -> None:
    assert rules(code) == []


def test_os_system_with_assembled_text_is_an_error_a_plain_variable_a_warning() -> None:
    assembled = analyse('import os\ndef f(h):\n    os.system(f"ping {h}")\n').findings[0]
    plain = analyse("import os\ndef f(c):\n    os.system(c)\n").findings[0]
    assert (assembled.severity, plain.severity) == ("error", "warning")


def test_debug_on_a_public_host_is_an_error() -> None:
    [finding] = analyse('app.run(host="0.0.0.0", debug=True)\n').findings
    assert finding.severity == "error"


# ---- mutation, performance, structure ----------------------------------------------------------


def test_mutating_the_list_being_iterated() -> None:
    code = "def f(xs):\n    for x in xs:\n        if x < 0:\n            xs.remove(x)\n"
    assert rules(code) == ["mutate-while-iterating"]
    assert line_of(code, "mutate-while-iterating") == 4


@pytest.mark.parametrize(
    "code",
    [
        "def f(xs):\n    for x in xs[:]:\n        xs.remove(x)\n",  # iterates a copy
        "def f(xs):\n    for x in list(xs):\n        xs.remove(x)\n",
        "def f(xs, t):\n    for x in xs:\n        if x == t:\n            xs.remove(x)\n            break\n",  # noqa: E501
        "def f(xs, ys):\n    for x in xs:\n        ys.append(x)\n",  # another list
    ],
)
def test_mutation_lookalikes_are_fine(code: str) -> None:
    assert "mutate-while-iterating" not in rules(code)


def test_pop_front_in_a_loop() -> None:
    assert rules("def f(q):\n    while q:\n        q.pop(0)\n") == ["pop-front"]
    assert rules("def f(q):\n    q.pop(0)\n") == []  # once, not in a loop
    assert rules("def f(q):\n    while q:\n        q.pop()\n") == []


def test_list_membership_in_a_growing_list() -> None:
    code = "def u(xs):\n    s = []\n    for x in xs:\n        if x not in s:\n            s.append(x)\n"  # noqa: E501
    assert rules(code) == ["list-membership"]
    # a fixed lookup table, or a set, is fine
    assert rules("V = ['a', 'e']\ndef f(s):\n    return [c for c in s if c in V]\n") == []
    assert (
        rules(
            "def u(xs):\n    s = set()\n    for x in xs:\n        if x not in s:\n            s.add(x)\n"  # noqa: E501
        )
        == []
    )


def test_deep_nesting_counts_levels_and_ignores_elif() -> None:
    deep = (
        "def f(a):\n    if a:\n        for x in a:\n            if x:\n                if x > 1:\n"
        "                    if x > 2:\n                        return x\n"
    )
    assert rules(deep) == ["deep-nesting"]
    elif_chain = (
        "def f(a):\n    if a == 1:\n        return 1\n" + "    elif a == 2:\n        return 2\n" * 8
    )
    assert rules(elif_chain) == []
    shallow = "def f(a):\n    for x in a:\n        if x:\n            return x\n"
    assert rules(shallow) == []


def test_global_state_only_when_written() -> None:
    assert rules("n = 0\ndef f():\n    global n\n    n += 1\n") == ["global-state"]
    assert rules("n = 0\ndef f():\n    global n\n    return n\n") == []


def test_shadowed_builtins_are_listed_once_per_scope() -> None:
    found = analyse("def f(list, max=0):\n    max = 1\n    return list\n").findings
    assert [f.rule for f in found] == ["shadow-builtin"]
    assert "'list'" in found[0].title and "'max'" in found[0].title
    assert rules("def f(items, limit):\n    return items[:limit]\n") == []


def test_none_comparison() -> None:
    assert rules("def f(v):\n    return v == None\n") == ["none-equality"]
    assert rules("def f(v):\n    return v != None\n") == ["none-equality"]
    assert rules("def f(v):\n    return v is None\n") == []


def test_swallowed_exception_only_for_broad_handlers() -> None:
    assert rules("try:\n    x()\nexcept Exception:\n    pass\n") == ["swallowed-exception"]
    assert rules("try:\n    x()\nexcept (OSError, Exception):\n    pass\n") == [
        "swallowed-exception"
    ]
    assert rules("try:\n    x()\nexcept FileNotFoundError:\n    pass\n") == []
    assert rules("try:\n    x()\nexcept Exception:\n    log()\n") == []


# ---- tightened rules ---------------------------------------------------------------------------


def test_sieve_is_not_reported_as_nested_loops() -> None:
    code = (
        "def primes(limit):\n    p = [True] * (limit + 1)\n"
        "    for i in range(2, int(limit ** 0.5) + 1):\n        if p[i]:\n"
        "            for m in range(i * i, limit + 1, i):\n                p[m] = False\n"
        "    return [n for n, ok in enumerate(p) if ok]\n"
    )
    assert "nested-loops" not in rules(code)
    assert algorithms(code) == ["sieve"]


def test_backtracking_is_not_depth_first_search() -> None:
    code = (
        "def solve(n):\n    used = set()\n    path = []\n    def go(row):\n        if row == n:\n"
        "            return\n        for c in range(n):\n            if c in used:\n"
        "                continue\n            used.add(c)\n            path.append(c)\n"
        "            go(row + 1)\n            path.pop()\n            used.remove(c)\n    go(0)\n"
    )
    assert "dfs" not in algorithms(code)


def test_plain_dfs_is_still_detected() -> None:
    code = (
        "def dfs(g, v, seen=None):\n    if seen is None:\n        seen = set()\n    seen.add(v)\n"
        "    for w in g[v]:\n        if w not in seen:\n            dfs(g, w, seen)\n    return seen\n"  # noqa: E501
    )
    assert algorithms(code) == ["dfs"]


# ---- algorithms --------------------------------------------------------------------------------

DIJKSTRA = (
    "import heapq\ndef d(g, s):\n    dist = {s: 0}\n    h = [(0, s)]\n    while h:\n"
    "        x, n = heapq.heappop(h)\n        for m, w in g[n]:\n            nd = x + w\n"
    "            if nd < dist.get(m, 1e9):\n                dist[m] = nd\n"
    "                heapq.heappush(h, (nd, m))\n    return dist\n"
)
PRIM = (
    "import heapq\ndef p(g, s):\n    seen = {s}\n    h = list(g[s])\n    while h:\n"
    "        w, n = heapq.heappop(h)\n        if n in seen:\n            continue\n"
    "        seen.add(n)\n        for m, c in g[n]:\n            heapq.heappush(h, (c, m))\n"
)


def test_dijkstra_but_not_prim() -> None:
    assert algorithms(DIJKSTRA) == ["dijkstra"]
    assert algorithms(PRIM) == []


def test_quicksort_variants_but_not_merge_sort() -> None:
    comp = (
        "def q(a):\n    if len(a) < 2:\n        return a\n    p = a[0]\n"
        "    return q([x for x in a if x < p]) + [p] + q([x for x in a if x > p])\n"
    )
    assert algorithms(comp) == ["quicksort"]
    fib = "def f(n):\n    return n if n < 2 else f(n - 1) + f(n - 2)\n"
    assert algorithms(fib) == []


def test_topological_sort_is_not_bfs() -> None:
    code = (
        "from collections import deque\ndef t(g, deg):\n    q = deque(n for n in g if deg[n] == 0)\n"  # noqa: E501
        "    out = []\n    while q:\n        n = q.popleft()\n        out.append(n)\n"
        "        for m in g[n]:\n            deg[m] -= 1\n            if deg[m] == 0:\n"
        "                q.append(m)\n    return out\n"
    )
    assert algorithms(code) == ["topological_sort"]


def test_kadane() -> None:
    code = (
        "def k(a):\n    best = cur = a[0]\n    for x in a[1:]:\n        cur = max(x, cur + x)\n"
        "        best = max(best, cur)\n    return best\n"
    )
    assert algorithms(code) == ["kadane"]
    assert (
        algorithms("def m(a):\n    r = 0\n    for x in a:\n        r = max(r, x)\n    return r\n")
        == []
    )


def test_triple_loop_matrix_algorithms() -> None:
    matmul = (
        "def mm(a, b, n):\n    c = [[0] * n for _ in range(n)]\n    for i in range(n):\n"
        "        for j in range(n):\n            for k in range(n):\n"
        "                c[i][j] += a[i][k] * b[k][j]\n    return c\n"
    )
    floyd = (
        "def fw(d, n):\n    for k in range(n):\n        for i in range(n):\n"
        "            for j in range(n):\n"
        "                d[i][j] = min(d[i][j], d[i][k] + d[k][j])\n"
    )
    assert algorithms(matmul) == ["matrix_multiplication"]
    assert algorithms(floyd) == ["floyd_warshall"]


def test_lru_cache_and_union_find_classes() -> None:
    lru = (
        "from collections import OrderedDict\nclass C:\n    def __init__(self):\n"
        "        self.d = OrderedDict()\n    def get(self, k):\n        self.d.move_to_end(k)\n"
        "    def put(self, k, v):\n        self.d[k] = v\n        self.d.popitem(last=False)\n"
    )
    assert algorithms(lru) == ["lru_cache"]
    uf = (
        "class U:\n    def __init__(self, n):\n        self.parent = list(range(n))\n"
        "        self.rank = [0] * n\n    def find(self, x):\n        if self.parent[x] != x:\n"
        "            self.parent[x] = self.find(self.parent[x])\n        return self.parent[x]\n"
        "    def union(self, a, b):\n        pass\n"
    )
    assert algorithms(uf) == ["union_find"]
    without_rank = uf.replace("rank", "other")
    assert algorithms(without_rank) == []  # compression alone is not the full structure


# ---- the eval cases ----------------------------------------------------------------------------

CASES = json.loads((Path(__file__).parents[1] / "evals" / "cases.json").read_text())


def test_case_ids_are_unique_and_tagged() -> None:
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))
    assert all(c.get("tags") for c in CASES)
    assert {t for c in CASES for t in c["tags"]} == {"basic", "complex-algorithm", "bad-practice"}


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_python_cases_are_valid_python(case: dict[str, object]) -> None:
    if case["language"] != "python":
        pytest.skip("not python")
    result = analyse(str(case["code"]))
    assert result.parsed != (case["id"] == "syntax-error")


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_expected_lines_exist(case: dict[str, object]) -> None:
    lines = str(case["code"]).split("\n")
    expect = case["expect"]
    assert isinstance(expect, dict)
    assert all(1 <= n <= len(lines) for n in expect.get("issue_lines", []))
