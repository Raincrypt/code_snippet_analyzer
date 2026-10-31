"""Facts and findings read from Python code with the standard `ast` module. No AI involved.

Rules like these are precise: when one fires, it is true of the code. They cover the classic
mistakes a model often overlooks (SQL built from strings, mutable defaults, unclosed files,
exponential recursion) and recognise a few well-known algorithms by their structure.

Nothing here guesses. A rule that is not sure simply does not fire.
"""

import ast
import re
from dataclasses import dataclass, field

from app.schemas import Category, Confidence, Effort, Severity

LOOPS = (ast.For, ast.While, ast.AsyncFor)
COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
NESTING = (ast.If, ast.For, ast.While, ast.AsyncFor, ast.Try, ast.With, ast.AsyncWith, ast.Match)
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
# Names that say nothing about *which* collection a loop walks over.
GENERIC_NAMES = {
    "range", "len", "enumerate", "reversed", "zip", "sorted", "list", "set", "dict", "tuple",
    "iter", "map", "filter", "items", "keys", "values", "min", "max", "sum", "int",
}  # fmt: skip
CACHE_DECORATORS = {"cache", "lru_cache"}
MEMO_NAMES = ("memo", "cache", "dp", "table")


@dataclass(frozen=True)
class StaticFinding:
    rule: str
    line: int
    end_line: int | None
    severity: Severity
    category: Category
    title: str
    explanation: str
    impact: str
    confidence: Confidence
    effort: Effort
    fix_description: str | None = None
    fix_after: str | None = None


@dataclass(frozen=True)
class StaticAlgorithm:
    key: str  # a key of algorithm_catalog.CATALOG
    start_line: int
    end_line: int
    function: str


@dataclass(frozen=True)
class FunctionInfo:
    name: str
    start_line: int
    end_line: int
    loop_depth: int
    self_calls: int
    has_calls: bool  # calls anything other than itself
    has_docstring: bool = False


@dataclass
class StaticAnalysis:
    parsed: bool = False
    syntax_error: tuple[int, str] | None = None
    functions: list[FunctionInfo] = field(default_factory=list)
    findings: list[StaticFinding] = field(default_factory=list)
    algorithms: list[StaticAlgorithm] = field(default_factory=list)
    longest_function_lines: int | None = None
    max_nesting_depth: int | None = None
    has_memoization: bool = False
    # Code with nothing to loop over or call at module level except definitions.
    only_definitions: bool = False


# ---- small helpers ---------------------------------------------------------------------------


def _walk_own(node: ast.AST) -> list[ast.AST]:
    """All nodes inside `node`, without descending into nested function or class definitions."""
    found: list[ast.AST] = []
    stack = list(ast.iter_child_nodes(node))
    while stack:
        current = stack.pop()
        found.append(current)
        if isinstance(current, (*FUNCTIONS, ast.ClassDef, ast.Lambda)):
            continue
        stack.extend(ast.iter_child_nodes(current))
    return found


def _loop_depth(node: ast.AST) -> int:
    """The deepest nesting of loops and comprehensions, not counting nested definitions."""
    deepest = 0
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (*FUNCTIONS, ast.ClassDef, ast.Lambda)):
            continue
        own = 0
        if isinstance(child, LOOPS):
            own = 1
        elif isinstance(child, COMPREHENSIONS):
            own = len(child.generators)
        deepest = max(deepest, own + _loop_depth(child))
    return deepest


def _nesting_depth(node: ast.AST, depth: int = 0) -> int:
    deepest = depth
    for child in ast.iter_child_nodes(node):
        deeper = depth + 1 if isinstance(child, NESTING) else depth
        deepest = max(deepest, _nesting_depth(child, deeper))
    return deepest


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _names_in(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)} - GENERIC_NAMES


def _is_const_str_free(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant)


def _decorator_names(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names = set()
    for d in fn.decorator_list:
        target = d.func if isinstance(d, ast.Call) else d
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Attribute):
            names.add(target.attr)
    return names


def _halves(node: ast.AST) -> bool:
    """Does the expression divide something by two (x // 2)?"""
    return any(
        isinstance(n, ast.BinOp)
        and isinstance(n.op, ast.FloorDiv)
        and isinstance(n.right, ast.Constant)
        and n.right.value == 2
        for n in ast.walk(node)
    )


def _source_line(lines: list[str], number: int) -> str:
    return lines[number - 1].strip() if 1 <= number <= len(lines) else ""


# ---- findings --------------------------------------------------------------------------------


MUTATORS = {"append", "extend", "add", "update", "insert", "setdefault", "pop", "remove", "clear"}


def _mutates(fn: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    """Does the function change the object bound to `name` (append, item assignment, +=)?"""
    for n in _walk_own(fn):
        if (
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr in MUTATORS
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id == name
        ):
            return True
        if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id == name:
            return True
        targets = n.targets if isinstance(n, ast.Assign) else []
        if any(
            isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id == name
            for t in targets
        ):
            return True
    return False


def _mutable_defaults(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[StaticFinding]:
    out = []
    args = fn.args
    positional = args.posonlyargs + args.args
    pairs = list(
        zip(positional[len(positional) - len(args.defaults) :], args.defaults, strict=True)
    )
    pairs += [
        (a, d) for a, d in zip(args.kwonlyargs, args.kw_defaults, strict=True) if d is not None
    ]
    for arg, default in pairs:
        mutable = isinstance(default, (ast.List, ast.Dict, ast.Set)) or (
            isinstance(default, ast.Call)
            and isinstance(default.func, ast.Name)
            and default.func.id in {"list", "dict", "set"}
            and not default.args
        )
        if not mutable:
            continue
        empty = ast.unparse(default)
        changed = _mutates(fn, arg.arg)
        out.append(
            StaticFinding(
                rule="mutable-default",
                line=default.lineno,
                end_line=None,
                severity="error" if changed else "warning",
                category="bug",
                title=f"Mutable default argument '{arg.arg}'",
                explanation=(
                    f"The default value `{empty}` for '{arg.arg}' is created once, when the "
                    "function is defined, and shared by every call that omits the argument."
                ),
                impact=(
                    "Changes made in one call leak into later calls, which gives results that "
                    "depend on how often the function ran before."
                ),
                confidence="high",
                effort="quick",
                fix_description=(
                    f"Use None as the default and create a fresh {empty} inside the function."
                ),
                fix_after=(
                    f"def {fn.name}(..., {arg.arg}=None):\n"
                    f"    if {arg.arg} is None:\n"
                    f"        {arg.arg} = {empty}\n"
                    "    ..."
                ),
            )
        )
    return out


def _built_sql(call: ast.Call) -> bool:
    """Is the first argument of an execute() call text assembled from variables?"""
    if _call_name(call) not in {"execute", "executemany"} or not call.args:
        return False
    query = call.args[0]
    if isinstance(query, ast.JoinedStr):
        return any(isinstance(v, ast.FormattedValue) for v in query.values)
    if isinstance(query, ast.BinOp) and isinstance(query.op, (ast.Add, ast.Mod)):
        return any(
            not _is_const_str_free(n)
            for n in ast.walk(query)
            if isinstance(n, (ast.Name, ast.Attribute, ast.Call, ast.Subscript))
        )
    return (
        isinstance(query, ast.Call)
        and isinstance(query.func, ast.Attribute)
        and query.func.attr == "format"
        and isinstance(query.func.value, ast.Constant)
    )


def _call_findings(call: ast.Call) -> list[StaticFinding]:
    name = _call_name(call)
    if _built_sql(call):
        return [
            StaticFinding(
                rule="sql-injection",
                line=call.lineno,
                end_line=call.end_lineno if call.end_lineno != call.lineno else None,
                severity="error",
                category="security",
                title="SQL query built from strings (SQL injection)",
                explanation=(
                    "The query text is assembled by joining or formatting strings, so any value "
                    "that contains SQL syntax becomes part of the command."
                ),
                impact=(
                    "An attacker who controls that value can read, change or delete data, "
                    "for example by entering ' OR '1'='1."
                ),
                confidence="high",
                effort="quick",
                fix_description=(
                    "Pass values as parameters so the driver escapes them. Use the placeholder "
                    "your driver expects: ? for sqlite3, %s for psycopg and MySQL drivers."
                ),
                fix_after='cursor.execute("SELECT * FROM users WHERE name = ?", (name,))',
            )
        ]
    if (
        isinstance(call.func, ast.Name)
        and call.func.id in {"eval", "exec"}
        and call.args
        and not isinstance(call.args[0], ast.Constant)
    ):
        return [
            StaticFinding(
                rule="eval-exec",
                line=call.lineno,
                end_line=None,
                severity="error",
                category="security",
                title=f"{call.func.id}() runs text as code",
                explanation=f"`{call.func.id}` executes whatever string it is given.",
                impact="If any part of that string comes from a user, they can run their own code.",
                confidence="high",
                effort="moderate",
                fix_description=(
                    "Parse the data instead: ast.literal_eval for Python literals, json.loads "
                    "for JSON, or an explicit lookup table of allowed operations."
                ),
                fix_after="value = ast.literal_eval(text)",
            )
        ]
    if name in {"run", "call", "Popen", "check_output", "check_call"} and any(
        k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True
        for k in call.keywords
    ):
        return [
            StaticFinding(
                rule="shell-true",
                line=call.lineno,
                end_line=None,
                severity="warning",
                category="security",
                title="shell=True can run injected commands",
                explanation="With shell=True the command goes through the system shell.",
                impact=(
                    "If any part of the command comes from outside, special characters in it "
                    "can run extra commands."
                ),
                confidence="medium",
                effort="quick",
                fix_description="Pass the command as a list and leave shell off.",
                fix_after='subprocess.run(["ls", "-l", path], check=True)',
            )
        ]
    return []


def _unclosed_files(scope: ast.AST) -> list[StaticFinding]:
    """`f = open(...)` outside `with`, where f is never closed and does not escape."""
    out = []
    nodes = _walk_own(scope)
    for node in nodes:
        if not (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "open"
        ):
            continue
        name = node.targets[0].id
        closed = False
        escapes = False
        for other in nodes:
            if (
                isinstance(other, ast.Call)
                and isinstance(other.func, ast.Attribute)
                and other.func.attr == "close"
                and isinstance(other.func.value, ast.Name)
                and other.func.value.id == name
            ):
                closed = True
        # Passing the file object on (return, argument, attribute) hands over the duty to close.
        method_uses = {
            id(n.value)
            for n in nodes
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == name
        }
        for other in nodes:
            if (
                isinstance(other, ast.Name)
                and other.id == name
                and isinstance(other.ctx, ast.Load)
                and id(other) not in method_uses
            ):
                escapes = True
        if closed or escapes:
            continue
        call_text = ast.unparse(node.value)
        out.append(
            StaticFinding(
                rule="unclosed-file",
                line=node.lineno,
                end_line=None,
                severity="warning",
                category="best-practice",
                title="File is opened but never closed",
                explanation=(
                    f"`{name}` is opened with open() but `{name}.close()` is never called, and "
                    "it is not used in a `with` block."
                ),
                impact=(
                    "The file handle stays open until the program ends or the object is "
                    "collected, which can exhaust file handles or lose buffered writes."
                ),
                confidence="high",
                effort="quick",
                fix_description="Open the file in a `with` block, which closes it automatically.",
                fix_after=f"with {call_text} as {name}:\n    ...  # use {name} here",
            )
        )
    return out


def _exponential_recursion(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> StaticFinding | None:
    """f(n - 1) + f(n - 2): the same subproblems solved again and again."""
    if _decorator_names(fn) & CACHE_DECORATORS:
        return None
    calls = [
        n
        for n in _walk_own(fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == fn.name
    ]
    shrinking = [
        c
        for c in calls
        if len(c.args) == 1
        and not c.keywords
        and isinstance(c.args[0], ast.BinOp)
        and isinstance(c.args[0].op, ast.Sub)
        and isinstance(c.args[0].right, ast.Constant)
    ]
    if len(shrinking) < 2:
        return None
    first = min(shrinking, key=lambda c: c.lineno)
    return StaticFinding(
        rule="exponential-recursion",
        line=first.lineno,
        end_line=None,
        severity="warning",
        category="performance",
        title="Exponential time: recursion recomputes the same values",
        explanation=(
            f"`{fn.name}` calls itself {len(shrinking)} times with a slightly smaller input and "
            "keeps no record of earlier results, so the same sub-problems are solved over and "
            "over. The number of calls roughly doubles with each step."
        ),
        impact="Time grows as O(2^n): a modest input such as n = 40 can take minutes.",
        confidence="high",
        effort="quick",
        fix_description=(
            "Cache the results (functools.cache) so each value is computed once, giving O(n), "
            "or compute it with a loop."
        ),
        fix_after=f"from functools import cache\n\n@cache\ndef {fn.name}(n):\n    ...",
    )


def _collections(it: ast.AST) -> set[str]:
    """The collections a loop walks over: its iterable, or the X in range(len(X))."""
    if isinstance(it, (ast.Name, ast.Attribute, ast.Subscript)):
        return {ast.unparse(it)}
    if isinstance(it, ast.Call):
        name = _call_name(it)
        if name == "range":
            return {
                ast.unparse(c.args[0])
                for c in ast.walk(it)
                if isinstance(c, ast.Call) and _call_name(c) == "len" and c.args
            }
        if name in {"enumerate", "reversed", "sorted", "list", "set", "tuple", "iter", "zip"}:
            found: set[str] = set()
            for arg in it.args:
                found |= _collections(arg)
            return found
        if name in {"items", "keys", "values"} and isinstance(it.func, ast.Attribute):
            return {ast.unparse(it.func.value)}
    return set()


def _nested_loops_same_collection(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
) -> StaticFinding | None:
    for outer in _walk_own(fn):
        if not isinstance(outer, (ast.For, ast.AsyncFor)):
            continue
        outer_names = _collections(outer.iter)
        for inner in ast.walk(outer):
            if inner is outer or not isinstance(inner, (ast.For, ast.AsyncFor)):
                continue
            shared = outer_names & _collections(inner.iter)
            if not shared:
                continue
            compares = any(
                isinstance(n, ast.Compare)
                and any(isinstance(o, (ast.Eq, ast.NotEq)) for o in n.ops)
                for n in ast.walk(inner)
            )
            collection = sorted(shared)[0]
            return StaticFinding(
                rule="nested-loops",
                line=outer.lineno,
                end_line=inner.lineno,
                severity="warning" if compares else "info",
                category="performance",
                title=f"Nested loops over '{collection}' take quadratic time",
                explanation=(
                    f"The inner loop walks over `{collection}` again for every item of the "
                    "outer loop, so the work grows with the square of its size."
                ),
                impact="Time grows as O(n^2): 10 times the data takes about 100 times longer.",
                confidence="medium",
                effort="moderate",
                fix_description=(
                    "If the inner loop is looking for matches or repeats, a set or dict lookup "
                    "can replace it and bring the time down to O(n)."
                    if compares
                    else "Check whether the inner loop can be replaced by a set or dict lookup."
                ),
            )
    return None


def _bare_excepts(tree: ast.AST) -> list[StaticFinding]:
    return [
        StaticFinding(
            rule="bare-except",
            line=n.lineno,
            end_line=None,
            severity="warning",
            category="best-practice",
            title="Bare except hides every error",
            explanation=(
                "`except:` with no exception type also catches KeyboardInterrupt and "
                "SystemExit, and silently swallows bugs."
            ),
            impact="Real problems are hidden, which makes failures hard to diagnose.",
            confidence="high",
            effort="quick",
            fix_description="Catch only the exceptions you expect, such as ValueError.",
            fix_after="except ValueError as error:\n    ...",
        )
        for n in ast.walk(tree)
        if isinstance(n, ast.ExceptHandler) and n.type is None
    ]


# ---- bad practices ---------------------------------------------------------------------------

SECRET_NAME = re.compile(
    r"(password|passwd|pwd|secret|secret_key|api_?key|token|private_key|access_key|auth_key)$",
    re.IGNORECASE,
)
SECRETISH = re.compile(r"pass|pwd|secret|token", re.IGNORECASE)
HTTP_VERBS = {"get", "post", "put", "delete", "head", "patch", "request"}
BUILTINS_NOT_TO_SHADOW = {
    "list", "dict", "set", "str", "int", "float", "bool", "tuple", "bytes", "max", "min", "sum",
    "len", "sorted", "filter", "map", "all", "any", "range", "open", "print", "zip", "round", "abs",
}  # fmt: skip
LIST_MUTATORS = {"remove", "append", "insert", "pop", "extend", "clear"}
DEEP_NESTING = 5


def _finding(
    rule: str,
    node: ast.AST,
    *,
    severity: Severity,
    category: Category,
    title: str,
    explanation: str,
    impact: str,
    confidence: Confidence,
    effort: Effort,
    fix_description: str | None = None,
    fix_after: str | None = None,
    end_line: int | None = None,
    line: int | None = None,
) -> StaticFinding:
    return StaticFinding(
        rule=rule,
        line=line if line is not None else getattr(node, "lineno", 1),
        end_line=end_line,
        severity=severity,
        category=category,
        title=title,
        explanation=explanation,
        impact=impact,
        confidence=confidence,
        effort=effort,
        fix_description=fix_description,
        fix_after=fix_after,
    )


def _func_path(call: ast.Call) -> str:
    """'os.system' for os.system(...), 'eval' for eval(...), '' for anything more complex."""
    parts: list[str] = []
    node: ast.AST = call.func
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return ""
    return ".".join([node.id, *reversed(parts)])


def _assembled_text(node: ast.AST) -> bool:
    """Text built from pieces: "a" + b, f"a{b}", "a%s" % b, "a{}".format(b)."""
    if isinstance(node, ast.JoinedStr):
        return any(isinstance(v, ast.FormattedValue) for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return not (isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant))
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "format"
        and isinstance(node.func.value, ast.Constant)
    )


def _tar_names(nodes: list[ast.AST]) -> set[str]:
    """Names bound to an open tar archive in these nodes."""
    names: set[str] = set()
    for n in nodes:
        if isinstance(n, ast.With):
            for item in n.items:
                if (
                    isinstance(item.context_expr, ast.Call)
                    and _func_path(item.context_expr).startswith("tarfile.")
                    and isinstance(item.optional_vars, ast.Name)
                ):
                    names.add(item.optional_vars.id)
        elif (
            isinstance(n, ast.Assign)
            and isinstance(n.value, ast.Call)
            and _func_path(n.value).startswith("tarfile.")
        ):
            names.update(t.id for t in n.targets if isinstance(t, ast.Name))
    return names


def _security_call(call: ast.Call, scope_name: str, tar_names: set[str]) -> list[StaticFinding]:
    path = _func_path(call)
    keywords = {k.arg: k.value for k in call.keywords if k.arg}
    first = call.args[0] if call.args else None
    out: list[StaticFinding] = []

    if path in {"pickle.loads", "pickle.load", "cPickle.loads", "dill.loads", "dill.load"} and (
        first is not None and not isinstance(first, ast.Constant)
    ):
        out.append(
            _finding(
                "unsafe-deserialization",
                call,
                severity="warning",
                category="security",
                title=f"{path}() can run arbitrary code",
                explanation=(
                    "Unpickling data builds objects by running code stored in the data, so a "
                    "crafted payload executes whatever its author chose."
                ),
                impact="If the bytes ever come from a user, a file or a network, an attacker "
                "can run commands on your machine.",
                confidence="high",
                effort="moderate",
                fix_description=(
                    "Use a data-only format such as JSON for anything that crosses a trust "
                    "boundary. Keep pickle for data you wrote yourself and can authenticate."
                ),
                fix_after="data = json.loads(raw_bytes)",
            )
        )
    if path == "yaml.load":
        loader = keywords.get("Loader") or (call.args[1] if len(call.args) > 1 else None)
        unsafe = loader is None or ast.unparse(loader).split(".")[-1] in {
            "Loader",
            "UnsafeLoader",
            "FullLoader",
        }
        if unsafe:
            out.append(
                _finding(
                    "yaml-load",
                    call,
                    severity="warning",
                    category="security",
                    title="yaml.load() without a safe loader",
                    explanation=(
                        "yaml.load can construct arbitrary Python objects from the document, "
                        "which can run code while the YAML is being read."
                    ),
                    impact="A malicious YAML file or string can execute commands.",
                    confidence="high",
                    effort="quick",
                    fix_description="Use yaml.safe_load, which only builds plain data.",
                    fix_after="config = yaml.safe_load(text)",
                )
            )
    verify = keywords.get("verify")
    if isinstance(verify, ast.Constant) and verify.value is False:
        out.append(
            _finding(
                "tls-verify-off",
                call,
                severity="warning",
                category="security",
                title="TLS certificate checking is turned off",
                explanation=(
                    "verify=False makes the client accept any certificate, including a forged "
                    "one, so it no longer checks who it is talking to."
                ),
                impact="Anyone on the network path can read or change the traffic "
                "(a man-in-the-middle attack).",
                confidence="high",
                effort="quick",
                fix_description=(
                    "Remove verify=False. If the server uses a private CA, pass the path of its "
                    "certificate bundle instead: verify='/path/to/ca.pem'."
                ),
                fix_after="response = requests.get(url, timeout=10)",
            )
        )
    if (
        path.startswith("requests.")
        and path.split(".")[-1] in HTTP_VERBS
        and "timeout" not in keywords
        and not any(k.arg is None for k in call.keywords)
    ):
        out.append(
            _finding(
                "http-no-timeout",
                call,
                severity="info",
                category="best-practice",
                title="HTTP request without a timeout",
                explanation=(
                    "requests waits forever by default when the server accepts the connection "
                    "but never answers."
                ),
                impact="One unresponsive server can freeze the calling thread or worker.",
                confidence="high",
                effort="quick",
                fix_description="Pass a timeout in seconds.",
                fix_after=f"{path}(..., timeout=10)",
            )
        )
    if path in {"os.system", "os.popen"} and first is not None:
        assembled = _assembled_text(first)
        if assembled or not isinstance(first, ast.Constant):
            out.append(
                _finding(
                    "os-system",
                    call,
                    severity="error" if assembled else "warning",
                    category="security",
                    title=f"{path}() runs a command built at run time (command injection)",
                    explanation=(
                        f"{path} passes its argument to the system shell, so shell characters "
                        "such as ; & | and $( ) in a value become extra commands."
                    ),
                    impact="If any part of the command comes from outside, an attacker can run "
                    "their own commands with your program's permissions.",
                    confidence="high" if assembled else "medium",
                    effort="quick",
                    fix_description=(
                        "Call subprocess.run with a list of arguments and no shell, so every "
                        "value stays a single argument."
                    ),
                    fix_after='subprocess.run(["ping", "-c", "1", host], check=True)',
                )
            )
    if path == "tempfile.mktemp":
        out.append(
            _finding(
                "mktemp",
                call,
                severity="warning",
                category="security",
                title="tempfile.mktemp() is open to a race condition",
                explanation=(
                    "mktemp only returns a name; the file is created later. Between those two "
                    "moments another process can create or link a file with that name."
                ),
                impact="An attacker who can guess the name may make the program write to, or "
                "read from, a file of their choosing.",
                confidence="high",
                effort="quick",
                fix_description="Use tempfile.NamedTemporaryFile or mkstemp, which create the "
                "file atomically.",
                fix_after='with tempfile.NamedTemporaryFile("w", delete=False) as f:\n    ...',
            )
        )
    debug = keywords.get("debug")
    if (
        isinstance(call.func, ast.Attribute)
        and call.func.attr == "run"
        and isinstance(debug, ast.Constant)
        and debug.value is True
    ):
        host = keywords.get("host")
        public = isinstance(host, ast.Constant) and host.value == "0.0.0.0"  # noqa: S104
        out.append(
            _finding(
                "debug-server",
                call,
                severity="error" if public else "warning",
                category="security",
                title="Debug mode is on for a web server",
                explanation=(
                    "debug=True starts Flask's interactive debugger, which lets anyone who can "
                    "reach the page run Python on the server"
                    + (
                        ", and host='0.0.0.0' makes it reachable from the network."
                        if public
                        else "."
                    )
                ),
                impact="Remote code execution if this runs anywhere other than a developer "
                "machine.",
                confidence="high",
                effort="quick",
                fix_description="Turn debug off, or read it from an environment variable that "
                "is only set on development machines.",
                fix_after='app.run(debug=os.environ.get("APP_DEBUG") == "1")',
            )
        )
    if (
        isinstance(call.func, ast.Attribute)
        and call.func.attr == "extractall"
        and "filter" not in keywords
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id in tar_names
    ):
        out.append(
            _finding(
                "tar-extractall",
                call,
                severity="warning",
                category="security",
                title="Archive extracted without checking file paths",
                explanation=(
                    "A tar file can contain names like ../../etc/cron.d/job or absolute paths. "
                    "extractall() without a filter writes them wherever they point (before "
                    "Python 3.14 this is the default)."
                ),
                impact="An untrusted archive can overwrite files outside the target folder "
                "(path traversal).",
                confidence="medium",
                effort="quick",
                fix_description="Pass filter='data' (Python 3.12+), or check every member's "
                "path before extracting.",
                fix_after="tar.extractall(target, filter='data')",
            )
        )
    if (
        path in {"hashlib.md5", "hashlib.sha1"}
        and "usedforsecurity" not in keywords
        and SECRETISH.search(f"{scope_name} {ast.unparse(call)}")
    ):
        algorithm = path.split(".")[-1].upper()
        out.append(
            _finding(
                "weak-hash",
                call,
                severity="warning",
                category="security",
                title=f"{algorithm} is not safe for passwords or secrets",
                explanation=(
                    f"{algorithm} is broken for security use and, being very fast, lets an "
                    "attacker test billions of guesses per second. It also has no salt here, so "
                    "equal passwords give equal hashes."
                ),
                impact="If the stored hashes leak, most passwords can be recovered quickly.",
                confidence="high",
                effort="moderate",
                fix_description=(
                    "Use a slow, salted password hash: bcrypt, argon2 or hashlib.scrypt."
                ),
                fix_after="hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())",
            )
        )
    return out


def _hardcoded_secrets(nodes: list[ast.AST]) -> list[StaticFinding]:
    out = []
    for n in nodes:
        pairs: list[tuple[str, ast.AST, ast.AST]] = []
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    pairs.append((t.id, n.value, n))
                elif isinstance(t, ast.Attribute):
                    pairs.append((t.attr, n.value, n))
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value:
            pairs.append((n.target.id, n.value, n))
        elif isinstance(n, ast.Call):
            pairs.extend((k.arg, k.value, k.value) for k in n.keywords if k.arg)
        for name, value, at in pairs:
            if not (
                SECRET_NAME.search(name)
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
                and len(value.value) >= 4
                and not re.search(r"\s|^<|^\$\{|^\{\{", value.value)
            ):
                continue
            out.append(
                _finding(
                    "hardcoded-secret",
                    at,
                    severity="warning",
                    category="security",
                    title=f"Secret '{name}' is written into the source code",
                    explanation=(
                        f"The value of '{name}' is a fixed string in the code. Anyone who can "
                        "read the code, its repository or its history can read the secret."
                    ),
                    impact="A leaked repository or build means leaked credentials, and changing "
                    "the secret requires a code change and a deploy.",
                    confidence="high",
                    effort="quick",
                    fix_description="Read it from the environment or a secrets manager, and "
                    "rotate the value that was committed.",
                    fix_after=f'{name} = os.environ["{name}"]',
                )
            )
    return out


def _blocks(node: ast.AST) -> list[list[ast.stmt]]:
    """The statement lists directly inside a compound statement."""
    out: list[list[ast.stmt]] = []
    for name in ("body", "orelse", "finalbody"):
        block = getattr(node, name, None)
        if isinstance(block, list) and block and isinstance(block[0], ast.stmt):
            out.append(block)
    out.extend(h.body for h in getattr(node, "handlers", []))
    out.extend(case.body for case in getattr(node, "cases", []))
    return out


def _mutations_in(block: list[ast.stmt], name: str) -> list[ast.stmt]:
    """Statements that change `name`, except ones straight followed by break or return."""
    found: list[ast.stmt] = []
    for index, stmt in enumerate(block):
        if isinstance(stmt, (*FUNCTIONS, ast.ClassDef)):
            continue
        leaves = index + 1 < len(block) and isinstance(block[index + 1], (ast.Break, ast.Return))
        direct = (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Attribute)
            and stmt.value.func.attr in LIST_MUTATORS
            and isinstance(stmt.value.func.value, ast.Name)
            and stmt.value.func.value.id == name
        ) or (
            isinstance(stmt, ast.Delete)
            and any(
                isinstance(t, ast.Subscript)
                and isinstance(t.value, ast.Name)
                and t.value.id == name
                for t in stmt.targets
            )
        )
        if direct and not leaves:
            found.append(stmt)
        for inner in _blocks(stmt):
            found.extend(_mutations_in(inner, name))
    return found


def _iterated_name(loop: ast.For | ast.AsyncFor) -> str | None:
    it = loop.iter
    if isinstance(it, ast.Name):
        return it.id
    if (
        isinstance(it, ast.Call)
        and isinstance(it.func, ast.Attribute)
        and it.func.attr in {"items", "keys", "values"}
        and isinstance(it.func.value, ast.Name)
    ):
        return it.func.value.id
    return None


def _mutating_while_iterating(nodes: list[ast.AST]) -> list[StaticFinding]:
    out = []
    for loop in nodes:
        if not isinstance(loop, (ast.For, ast.AsyncFor)):
            continue
        name = _iterated_name(loop)
        if name is None:
            continue
        for stmt in _mutations_in(loop.body, name):
            out.append(
                _finding(
                    "mutate-while-iterating",
                    stmt,
                    severity="error",
                    category="bug",
                    title=f"'{name}' is changed while the loop is walking over it",
                    explanation=(
                        f"The loop on line {loop.lineno} iterates over `{name}`, and this "
                        "statement adds or removes items of the same collection. The loop's "
                        "position then no longer matches the data, so items are skipped (or "
                        "a dict or set raises RuntimeError)."
                    ),
                    impact="Some elements are never processed, and the result depends on the "
                    "order of the data.",
                    confidence="high",
                    effort="quick",
                    fix_description=(
                        "Iterate over a copy, or build the new collection instead of editing "
                        "the old one."
                    ),
                    fix_after=f"{name} = [x for x in {name} if keep(x)]",
                )
            )
    return out


def _pop_front_in_loop(nodes: list[ast.AST]) -> list[StaticFinding]:
    out: list[StaticFinding] = []
    seen: set[int] = set()
    for loop in nodes:
        if not isinstance(loop, LOOPS):
            continue
        for call in ast.walk(loop):
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "pop"
                and len(call.args) == 1
                and isinstance(call.args[0], ast.Constant)
                and call.args[0].value == 0
                and id(call) not in seen
            ):
                seen.add(id(call))
                out.append(
                    _finding(
                        "pop-front",
                        call,
                        severity="info",
                        category="performance",
                        title="list.pop(0) in a loop shifts every remaining item",
                        explanation=(
                            "Removing the first item of a list moves all the others one place "
                            "left, which costs O(n) each time, so draining a list this way "
                            "takes O(n^2) overall."
                        ),
                        impact="Slow for long lists; 100,000 items already means billions of "
                        "moves.",
                        confidence="high",
                        effort="quick",
                        fix_description="Use collections.deque and popleft(), which is O(1).",
                        fix_after="queue = deque(queue)\nitem = queue.popleft()",
                    )
                )
    return out


def _list_membership_in_loop(scope: ast.AST, nodes: list[ast.AST]) -> list[StaticFinding]:
    """`x in seen` where `seen` is a list that the same loop keeps appending to."""
    lists: set[str] = set()
    for n in nodes:
        if (
            isinstance(n, ast.Assign)
            and len(n.targets) == 1
            and isinstance(n.targets[0], ast.Name)
            and (
                (isinstance(n.value, ast.List) and not n.value.elts)
                or (
                    isinstance(n.value, ast.Call)
                    and isinstance(n.value.func, ast.Name)
                    and n.value.func.id == "list"
                    and not n.value.args
                )
            )
        ):
            lists.add(n.targets[0].id)
    out: list[StaticFinding] = []
    seen: set[int] = set()
    for loop in nodes:
        if not isinstance(loop, LOOPS):
            continue
        inside = list(ast.walk(loop))
        grown = {
            c.func.value.id
            for c in inside
            if isinstance(c, ast.Call)
            and isinstance(c.func, ast.Attribute)
            and c.func.attr in {"append", "extend", "insert"}
            and isinstance(c.func.value, ast.Name)
        }
        for cmp in inside:
            if not (isinstance(cmp, ast.Compare) and id(cmp) not in seen):
                continue
            for op, right in zip(cmp.ops, cmp.comparators, strict=True):
                if (
                    isinstance(op, (ast.In, ast.NotIn))
                    and isinstance(right, ast.Name)
                    and right.id in lists & grown
                ):
                    seen.add(id(cmp))
                    out.append(
                        _finding(
                            "list-membership",
                            cmp,
                            severity="warning",
                            category="performance",
                            title=f"Searching the list '{right.id}' on every loop pass",
                            explanation=(
                                f"`in` on a list compares against its items one by one, and "
                                f"`{right.id}` grows inside the loop, so the loop takes "
                                "O(n^2) in total."
                            ),
                            impact="Fine for tens of items, painfully slow for tens of thousands.",
                            confidence="medium",
                            effort="quick",
                            fix_description=(
                                "Keep a set next to (or instead of) the list: set lookups are "
                                "O(1) on average."
                            ),
                            fix_after=f"{right.id}_set = set()\n# test: x in {right.id}_set",
                        )
                    )
    del scope  # the scope is only here to keep the call sites uniform
    return out


def _deepest(stmts: list[ast.stmt], depth: int) -> tuple[int, int]:
    """(deepest nesting, line of the statement there). An `elif` does not count as a new level."""
    best = (depth, stmts[0].lineno if stmts else 0)
    for stmt in stmts:
        if isinstance(stmt, (*FUNCTIONS, ast.ClassDef)) or not isinstance(stmt, NESTING):
            continue
        for block in _blocks(stmt):
            is_elif = (
                isinstance(stmt, ast.If)
                and block is stmt.orelse
                and len(block) == 1
                and isinstance(block[0], ast.If)
            )
            candidate = _deepest(block, depth if is_elif else depth + 1)
            if candidate[0] > best[0]:
                best = candidate
    return best


def _deep_nesting(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> StaticFinding | None:
    depth, line = _deepest(fn.body, 0)
    if depth < DEEP_NESTING:
        return None
    return _finding(
        "deep-nesting",
        fn,
        severity="warning" if depth > DEEP_NESTING else "info",
        category="best-practice",
        title=f"'{fn.name}' nests {depth} levels deep",
        explanation=(
            f"The innermost statement (line {line}) sits inside {depth} nested if, loop, try or "
            "with blocks. Each level adds a condition the reader must keep in mind."
        ),
        impact="Hard to read, to test and to change without breaking a branch.",
        confidence="high",
        effort="moderate",
        end_line=line if line > fn.lineno else None,
        fix_description=(
            "Return early for the failing cases (guard clauses) and move inner loops into "
            "small helper functions."
        ),
        fix_after="if not order:\n    return 0\nif not order.items:\n    return 0\n...",
    )


def _global_writes(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[StaticFinding]:
    own = _walk_own(fn)
    out = []
    for n in own:
        if not isinstance(n, ast.Global):
            continue
        written = [
            name
            for name in n.names
            if any(
                (isinstance(m, ast.Name) and m.id == name and isinstance(m.ctx, ast.Store))
                or (
                    isinstance(m, ast.AugAssign)
                    and isinstance(m.target, ast.Name)
                    and m.target.id == name
                )
                for m in own
            )
        ]
        if not written:
            continue
        names = ", ".join(f"'{w}'" for w in written)
        out.append(
            _finding(
                "global-state",
                n,
                severity="info",
                category="best-practice",
                title=f"Function changes global state ({names})",
                explanation=(
                    f"`global` lets '{fn.name}' rebind module-level variables. Every caller now "
                    "depends on, and can break, shared hidden state."
                ),
                impact="Hard to test, and not safe when several threads or requests run at "
                "once: two calls can read the same value.",
                confidence="high",
                effort="moderate",
                fix_description="Keep the state in an object (a class instance) or pass it in "
                "and return the new value. For ids, itertools.count() works.",
                fix_after="import itertools\n_ids = itertools.count(1)\n\ndef next_id():\n"
                "    return next(_ids)",
            )
        )
    return out


def _shadowed_builtins(scope: ast.AST, nodes: list[ast.AST]) -> StaticFinding | None:
    found: dict[str, int] = {}
    if isinstance(scope, FUNCTIONS):
        args = scope.args
        for a in [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg]:
            if a is not None and a.arg in BUILTINS_NOT_TO_SHADOW:
                found.setdefault(a.arg, a.lineno)
    for n in nodes:
        if (
            isinstance(n, ast.Name)
            and isinstance(n.ctx, ast.Store)
            and n.id in BUILTINS_NOT_TO_SHADOW
        ):
            found.setdefault(n.id, n.lineno)
    if not found:
        return None
    names = sorted(found, key=lambda k: found[k])
    listed = ", ".join(f"'{n}'" for n in names)
    return _finding(
        "shadow-builtin",
        scope,
        line=min(found.values()),
        severity="info",
        category="best-practice",
        title=f"{listed} hide{'s' if len(names) == 1 else ''} a built-in name",
        explanation=(
            f"Naming a variable or parameter {listed} replaces the built-in of the same name "
            "inside this scope, so calls such as list(...) or max(...) later in it fail or "
            "misbehave."
        ),
        impact="A confusing TypeError appears the first time the built-in is needed again.",
        confidence="high",
        effort="quick",
        fix_description=f"Rename it, for example '{names[0]}_' or a more descriptive name.",
    )


def _none_comparisons(tree: ast.AST) -> list[StaticFinding]:
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Compare):
            continue
        operands = [n.left, *n.comparators]
        for i, op in enumerate(n.ops):
            pair = (operands[i], operands[i + 1])
            if isinstance(op, (ast.Eq, ast.NotEq)) and any(
                isinstance(side, ast.Constant) and side.value is None for side in pair
            ):
                word, wrong = ("is", "==") if isinstance(op, ast.Eq) else ("is not", "!=")
                out.append(
                    _finding(
                        "none-equality",
                        n,
                        severity="info",
                        category="best-practice",
                        title=f"Compare with None using `{word}`, not `{wrong}`",
                        explanation=(
                            "None is a single object, so identity (`is`) is the correct test. "
                            "`==` calls the object's own __eq__, which a class may define to "
                            "return True for None."
                        ),
                        impact="Usually harmless, but it misbehaves with objects such as numpy "
                        "arrays and trips linters.",
                        confidence="high",
                        effort="quick",
                        fix_description=f"Write `x {word} None`.",
                        fix_after=f"if value {word} None:",
                    )
                )
                break
    return out


def _swallowed_exceptions(tree: ast.AST) -> list[StaticFinding]:
    out = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.ExceptHandler) and n.type is not None):
            continue
        broad = {"Exception", "BaseException"}
        types = n.type.elts if isinstance(n.type, ast.Tuple) else [n.type]
        if not any(isinstance(t, ast.Name) and t.id in broad for t in types):
            continue
        if all(
            isinstance(s, ast.Pass)
            or (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
            for s in n.body
        ):
            out.append(
                _finding(
                    "swallowed-exception",
                    n,
                    severity="warning",
                    category="best-practice",
                    title="Every error is caught and silently ignored",
                    explanation=(
                        f"`except {ast.unparse(n.type)}` catches almost any failure and the "
                        "handler does nothing, so the program carries on as if it had worked."
                    ),
                    impact="Failures (a full disk, a bug, a lost connection) vanish without a "
                    "trace and data is lost without anyone knowing.",
                    confidence="high",
                    effort="quick",
                    end_line=n.body[-1].end_lineno if n.body else None,
                    fix_description=(
                        "Catch only the specific errors you can handle, and log or re-raise "
                        "the rest."
                    ),
                    fix_after=(
                        "except sqlite3.IntegrityError:\n"
                        "    logger.warning('duplicate record', exc_info=True)"
                    ),
                )
            )
    return out


def _practice_findings(
    tree: ast.AST, functions: list[ast.FunctionDef | ast.AsyncFunctionDef]
) -> list[StaticFinding]:
    out: list[StaticFinding] = []
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    for scope in [tree, *classes, *functions]:
        nodes = _walk_own(scope)
        scope_name = getattr(scope, "name", "")
        tar_names = _tar_names(nodes)
        for node in nodes:
            if isinstance(node, ast.Call):
                out.extend(_security_call(node, scope_name, tar_names))
        out.extend(_hardcoded_secrets(nodes))
        out.extend(_mutating_while_iterating(nodes))
        out.extend(_pop_front_in_loop(nodes))
        out.extend(_list_membership_in_loop(scope, nodes))
        if (shadow := _shadowed_builtins(scope, nodes)) is not None:
            out.append(shadow)
    for fn in functions:
        if (deep := _deep_nesting(fn)) is not None:
            out.append(deep)
        out.extend(_global_writes(fn))
    out.extend(_none_comparisons(tree))
    out.extend(_swallowed_exceptions(tree))
    return out


# ---- algorithms ------------------------------------------------------------------------------


def _backtracks(fn: ast.FunctionDef | ast.AsyncFunctionDef, nodes: list[ast.AST]) -> bool:
    """Recursion inside a loop followed by an undo step (pop, remove, discard, del)."""
    for loop in nodes:
        if not isinstance(loop, LOOPS):
            continue
        inside = list(ast.walk(loop))
        calls_at = [
            n.lineno
            for n in inside
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == fn.name
        ]
        undo_at = [
            n.lineno
            for n in inside
            if isinstance(n, ast.Delete)
            or (
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr in {"pop", "remove", "discard"}
            )
        ]
        if calls_at and any(u > min(calls_at) for u in undo_at):
            return True
    return False


def _swaps_subscripts(n: ast.AST) -> bool:
    return (
        isinstance(n, ast.Assign)
        and len(n.targets) == 1
        and isinstance(n.targets[0], ast.Tuple)
        and len(n.targets[0].elts) == 2
        and all(isinstance(e, ast.Subscript) for e in n.targets[0].elts)
    )


def _kadane_step(call: ast.Call) -> bool:
    """max(x, running + x): extend the run or start again at x."""
    if len(call.args) != 2:
        return False
    for a, b in (call.args, call.args[::-1]):
        if (
            isinstance(a, ast.Name)
            and isinstance(b, ast.BinOp)
            and isinstance(b.op, ast.Add)
            and any(isinstance(m, ast.Name) and m.id == a.id for m in ast.walk(b))
        ):
            return True
    return False


def _more_algorithms(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    nodes: list[ast.AST],
    self_calls: int,
    found: list[str],
) -> None:
    whiles = [n for n in nodes if isinstance(n, ast.While)]
    fors = [n for n in nodes if isinstance(n, ast.For)]
    calls = [n for n in nodes if isinstance(n, ast.Call)]
    method_names = {c.func.attr for c in calls if isinstance(c.func, ast.Attribute)}

    # Dijkstra: pop the nearest node from a heap, then relax edges: push a summed distance.
    if whiles and any(_call_name(c) == "heappop" for c in calls):
        for loop in fors:
            inside = list(ast.walk(loop))
            if (
                any(
                    isinstance(c, ast.Call)
                    and _call_name(c) == "heappush"
                    and len(c.args) == 2
                    and isinstance(c.args[1], ast.Tuple)
                    for c in inside
                )
                and any(isinstance(b, ast.BinOp) and isinstance(b.op, ast.Add) for b in inside)
                and any(
                    isinstance(c, ast.Compare)
                    and any(isinstance(o, (ast.Lt, ast.Gt, ast.LtE, ast.GtE)) for o in c.ops)
                    for c in inside
                )
            ):
                found.append("dijkstra")
                break

    # Quicksort: recursion on the parts either side of a pivot.
    if self_calls >= 2:
        against: dict[str, int] = {}
        for comp in nodes:
            if isinstance(comp, ast.ListComp):
                for gen in comp.generators:
                    for cond in gen.ifs:
                        if isinstance(cond, ast.Compare) and isinstance(
                            cond.comparators[0], ast.Name
                        ):
                            name = cond.comparators[0].id
                            against[name] = against.get(name, 0) + 1
        in_place = (
            any(_swaps_subscripts(n) for n in nodes)
            and any(isinstance(n, ast.Name) and "pivot" in n.id for n in nodes)
            and not _halves(fn)
        )
        if any(count >= 2 for count in against.values()) or in_place:
            found.append("quicksort")

    # Kahn's topological sort: a queue of nodes whose in-degree counter reached zero.
    counts_down = any(
        isinstance(n, ast.AugAssign)
        and isinstance(n.op, ast.Sub)
        and isinstance(n.target, ast.Subscript)
        and isinstance(n.value, ast.Constant)
        and n.value.value == 1
        for n in nodes
    )
    reaches_zero = any(
        isinstance(n, ast.Compare)
        and any(isinstance(o, ast.Eq) for o in n.ops)
        and any(isinstance(c, ast.Constant) and c.value == 0 for c in n.comparators)
        for n in nodes
    )
    if (
        whiles
        and counts_down
        and reaches_zero
        and ({"popleft", "pop"} & method_names)
        and ({"append", "extend"} & method_names)
    ):
        found[:] = [k for k in found if k not in {"bfs", "dfs"}]
        found.append("topological_sort")

    # Sieve of Eratosthenes: [True] * (n + 1), then strike out multiples with a stepped range.
    flags = any(
        isinstance(n, ast.BinOp)
        and isinstance(n.op, ast.Mult)
        and isinstance(n.left, ast.List)
        and len(n.left.elts) == 1
        and isinstance(n.left.elts[0], ast.Constant)
        and n.left.elts[0].value is True
        for n in nodes
    )
    if flags:
        for outer in fors:
            if any(
                isinstance(inner, ast.For)
                and inner is not outer
                and isinstance(inner.iter, ast.Call)
                and _call_name(inner.iter) == "range"
                and len(inner.iter.args) == 3
                and any(
                    isinstance(a, ast.Assign)
                    and isinstance(a.value, ast.Constant)
                    and a.value.value is False
                    and any(isinstance(t, ast.Subscript) for t in a.targets)
                    for a in ast.walk(inner)
                )
                for inner in ast.walk(outer)
            ):
                found.append("sieve")
                break

    # Kadane: inside a loop, max(x, run + x) and a running best.
    for loop in fors:
        maxes = [c for c in ast.walk(loop) if isinstance(c, ast.Call) and _call_name(c) == "max"]
        if len(maxes) >= 2 and any(_kadane_step(c) for c in maxes):
            found.append("kadane")
            break

    if _loop_depth(fn) >= 3:
        for n in nodes:
            if (
                isinstance(n, ast.AugAssign)
                and isinstance(n.op, ast.Add)
                and isinstance(n.target, ast.Subscript)
                and isinstance(n.value, ast.BinOp)
                and isinstance(n.value.op, ast.Mult)
                and isinstance(n.value.left, ast.Subscript)
                and isinstance(n.value.right, ast.Subscript)
            ):
                found.append("matrix_multiplication")
                break
        for n in nodes:
            if (
                isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Subscript) for t in n.targets)
                and isinstance(n.value, ast.Call)
                and _call_name(n.value) == "min"
                and any(
                    isinstance(b, ast.BinOp)
                    and isinstance(b.op, ast.Add)
                    and isinstance(b.left, ast.Subscript)
                    and isinstance(b.right, ast.Subscript)
                    for b in n.value.args
                )
            ):
                found.append("floyd_warshall")
                break


def _class_algorithms(cls: ast.ClassDef) -> list[str]:
    found: list[str] = []
    nodes = list(ast.walk(cls))
    methods = {n.name for n in cls.body if isinstance(n, FUNCTIONS)}
    calls = [n for n in nodes if isinstance(n, ast.Call)]
    names = {_call_name(c) for c in calls}

    # LRU cache: an ordered dict, entries moved to the end on use, oldest popped from the front.
    evicts_oldest = any(
        _call_name(c) == "popitem"
        and (
            any(
                k.arg == "last" and isinstance(k.value, ast.Constant) and k.value.value is False
                for k in c.keywords
            )
            or any(isinstance(a, ast.Constant) and a.value is False for a in c.args)
        )
        for c in calls
    )
    if "OrderedDict" in names and "move_to_end" in names and evicts_oldest:
        found.append("lru_cache")

    # Union-find: find + union, path compression on find, union by rank or size.
    compresses = any(
        isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Subscript) for t in n.targets)
        and (
            (isinstance(n.value, ast.Call) and _call_name(n.value) == "find")
            or (isinstance(n.value, ast.Subscript) and isinstance(n.value.value, ast.Subscript))
        )
        for n in nodes
    )
    by_rank = any(
        isinstance(n, ast.Attribute) and n.attr in {"rank", "ranks", "size", "sizes", "sz"}
        for n in nodes
    )
    if (
        "find" in methods
        and methods & {"union", "unite", "merge", "join"}
        and compresses
        and by_rank
    ):
        found.append("union_find")
    return found


def _detect_algorithms(fn: ast.FunctionDef | ast.AsyncFunctionDef, self_calls: int) -> list[str]:
    nodes = _walk_own(fn)
    whiles = [n for n in nodes if isinstance(n, ast.While)]
    calls = [n for n in nodes if isinstance(n, ast.Call)]
    method_names = {c.func.attr for c in calls if isinstance(c.func, ast.Attribute)}
    found: list[str] = []

    # Binary search: a while loop that moves one of two bounds around a halved midpoint.
    for loop in whiles:
        if not (
            isinstance(loop.test, ast.Compare)
            and len(loop.test.ops) == 1
            and isinstance(loop.test.left, ast.Name)
            and isinstance(loop.test.comparators[0], ast.Name)
        ):
            continue
        bounds = {loop.test.left.id, loop.test.comparators[0].id}
        mids = {
            t.id
            for n in ast.walk(loop)
            if isinstance(n, ast.Assign) and _halves(n.value)
            for t in n.targets
            if isinstance(t, ast.Name)
        }
        moves = any(
            isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id in bounds for t in n.targets)
            and any(isinstance(v, ast.Name) and v.id in mids for v in ast.walk(n.value))
            for n in ast.walk(loop)
        )
        if mids and moves:
            found.append("binary_search")
            break

    # Merge sort: recursion on two halves, then a while loop that merges with append.
    if self_calls >= 2 and _halves(fn) and "append" in method_names and whiles:
        found.append("merge_sort")

    # Breadth-first search: a queue drained from the front, and a visited check.
    pops_front = any(
        isinstance(c.func, ast.Attribute)
        and (
            c.func.attr == "popleft"
            or (
                c.func.attr == "pop"
                and c.args
                and isinstance(c.args[0], ast.Constant)
                and c.args[0].value == 0
            )
        )
        for c in calls
    )
    membership = any(
        isinstance(n, ast.Compare) and any(isinstance(o, (ast.In, ast.NotIn)) for o in n.ops)
        for n in nodes
    )
    if whiles and pops_front and membership and ({"append", "extend"} & method_names):
        found.append("bfs")
    else:
        # Depth-first search: a stack drained from the back with a visited check, or recursion
        # inside a loop that marks nodes as visited.
        pops_back = any(
            isinstance(c.func, ast.Attribute) and c.func.attr == "pop" and not c.args for c in calls
        )
        marks_visited = "add" in method_names or any(
            isinstance(n, ast.Subscript) and isinstance(n.ctx, ast.Store) for n in nodes
        )
        has_for = any(isinstance(n, ast.For) for n in nodes)
        if (
            membership
            and marks_visited
            and (
                (whiles and pops_back and ({"append", "extend"} & method_names))
                or (self_calls >= 1 and has_for)
            )
            and not _backtracks(fn, nodes)
        ):
            found.append("dfs")

    # Bubble sort: nested loops that swap neighbours, a[j], a[j + 1] = a[j + 1], a[j].
    if _loop_depth(fn) >= 2:
        for n in nodes:
            if (
                isinstance(n, ast.Assign)
                and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Tuple)
                and len(n.targets[0].elts) == 2
                and all(isinstance(e, ast.Subscript) for e in n.targets[0].elts)
                and any(
                    isinstance(e.slice, ast.BinOp) and isinstance(e.slice.op, ast.Add)  # type: ignore[attr-defined]
                    for e in n.targets[0].elts
                )
            ):
                found.append("bubble_sort")
                break

    # Euclid: while b: a, b = b, a % b
    for loop in whiles:
        for n in ast.walk(loop):
            if (
                isinstance(n, ast.Assign)
                and isinstance(n.targets[0], ast.Tuple)
                and isinstance(n.value, ast.Tuple)
                and any(
                    isinstance(v, ast.BinOp) and isinstance(v.op, ast.Mod) for v in n.value.elts
                )
            ):
                found.append("euclid_gcd")
                break
        else:
            continue
        break

    # Memoized recursion: a recursive function whose results are cached.
    if self_calls >= 1 and _decorator_names(fn) & CACHE_DECORATORS:
        found.append("memoized_recursion")
    _more_algorithms(fn, nodes, self_calls, found)
    return found


# ---- entry point -----------------------------------------------------------------------------


def analyse(code: str) -> StaticAnalysis:
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return StaticAnalysis(syntax_error=(error.lineno or 1, error.msg or "invalid syntax"))
    except (ValueError, RecursionError, MemoryError):
        return StaticAnalysis()  # could not be read; say nothing

    result = StaticAnalysis(parsed=True)
    result.max_nesting_depth = _nesting_depth(tree)
    result.only_definitions = all(
        isinstance(n, (*FUNCTIONS, ast.ClassDef, ast.Import, ast.ImportFrom))
        or (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
        for n in tree.body
    )

    functions = [n for n in ast.walk(tree) if isinstance(n, FUNCTIONS)]
    for fn in sorted(functions, key=lambda f: f.lineno):
        own = _walk_own(fn)
        self_calls = sum(
            1
            for n in own
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == fn.name
        )
        other_calls = any(
            isinstance(n, ast.Call) and not (isinstance(n.func, ast.Name) and n.func.id == fn.name)
            for n in own
        )
        end = fn.end_lineno or fn.lineno
        result.functions.append(
            FunctionInfo(
                fn.name,
                fn.lineno,
                end,
                _loop_depth(fn),
                self_calls,
                other_calls,
                ast.get_docstring(fn) is not None,
            )
        )
        if _decorator_names(fn) & CACHE_DECORATORS:
            result.has_memoization = True

        result.findings.extend(_mutable_defaults(fn))
        if (rec := _exponential_recursion(fn)) is not None:
            result.findings.append(rec)
        if (nested := _nested_loops_same_collection(fn)) is not None:
            result.findings.append(nested)
        for key in _detect_algorithms(fn, self_calls):
            result.algorithms.append(StaticAlgorithm(key, fn.lineno, end, fn.name))

    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        for key in _class_algorithms(cls):
            result.algorithms.append(
                StaticAlgorithm(key, cls.lineno, cls.end_lineno or cls.lineno, cls.name)
            )
    result.findings.extend(_practice_findings(tree, functions))
    for scope in [tree, *functions]:
        result.findings.extend(_unclosed_files(scope))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            result.findings.extend(_call_findings(node))
    result.findings.extend(_bare_excepts(tree))

    if result.functions:
        result.longest_function_lines = max(f.end_line - f.start_line + 1 for f in result.functions)
    return result
