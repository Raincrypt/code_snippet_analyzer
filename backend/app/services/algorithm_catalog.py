"""Facts about well-known algorithms, written by hand.

When the code is recognised as one of these (by `static_python.py`, or because the model names it),
the standard figures and wording from here are used, not whatever the model remembered. A model
often gets these wrong; a table does not.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Alternative:
    name: str
    time: str
    space: str
    tradeoff: str


@dataclass(frozen=True)
class CatalogEntry:
    key: str
    name: str
    category: str
    time: str  # worst case
    space: str
    summary: str
    assessment: str
    alternatives: tuple[Alternative, ...] = ()
    aliases: tuple[str, ...] = ()


CATALOG: dict[str, CatalogEntry] = {
    e.key: e
    for e in (
        CatalogEntry(
            key="binary_search",
            name="Binary search",
            category="searching",
            time="O(log n)",
            space="O(1)",
            summary=(
                "Repeatedly halves a sorted range by comparing the target with the middle "
                "element, discarding the half that cannot contain it."
            ),
            assessment=(
                "The right choice for lookups in sorted, indexable data. It gives wrong "
                "answers if the input is not sorted."
            ),
            alternatives=(
                Alternative(
                    "Linear scan",
                    "O(n)",
                    "O(1)",
                    "Works on unsorted data and is simpler, but slow for large inputs.",
                ),
                Alternative(
                    "Hash set or dict lookup",
                    "O(1)",
                    "O(n)",
                    "Faster per lookup, but needs extra memory and gives no ordering.",
                ),
            ),
            aliases=("binary search", "bisection"),
        ),
        CatalogEntry(
            key="merge_sort",
            name="Merge sort",
            category="sorting",
            time="O(n log n)",
            space="O(n)",
            summary=(
                "Splits the list in half, sorts each half recursively, then merges the two "
                "sorted halves into one."
            ),
            assessment=(
                "Reliable O(n log n) in every case and stable, at the cost of extra memory. "
                "In Python, the built-in sorted() is faster and should be preferred unless "
                "this is an exercise."
            ),
            alternatives=(
                Alternative(
                    "Built-in sorted()",
                    "O(n log n)",
                    "O(n)",
                    "Written in C and tuned for real data; no code to maintain.",
                ),
                Alternative(
                    "Quicksort (in place)",
                    "O(n^2)",
                    "O(log n)",
                    "Usually faster in practice and uses little memory, but has a bad worst case.",
                ),
            ),
            aliases=("merge sort", "mergesort"),
        ),
        CatalogEntry(
            key="bfs",
            name="Breadth-first search",
            category="graph traversal",
            time="O(V + E)",
            space="O(V)",
            summary=(
                "Visits a graph level by level using a queue, remembering visited nodes so "
                "none is processed twice."
            ),
            assessment=(
                "Correct for shortest paths in unweighted graphs and for visiting everything "
                "reachable. Using a deque keeps each queue step O(1)."
            ),
            alternatives=(
                Alternative(
                    "Depth-first search",
                    "O(V + E)",
                    "O(V)",
                    "Simpler to write recursively and good for exploring all paths, but it does "
                    "not find shortest paths.",
                ),
                Alternative(
                    "Dijkstra's algorithm",
                    "O((V + E) log V)",
                    "O(V)",
                    "Needed when edges have different weights.",
                ),
            ),
            aliases=("breadth-first search", "breadth first search", "bfs"),
        ),
        CatalogEntry(
            key="dfs",
            name="Depth-first search",
            category="graph traversal",
            time="O(V + E)",
            space="O(V)",
            summary=(
                "Follows each path as deep as it goes before backing up, remembering visited "
                "nodes so none is processed twice."
            ),
            assessment=(
                "Good for reachability, cycle detection and exploring all paths. Recursive "
                "versions can hit Python's recursion limit on deep graphs."
            ),
            alternatives=(
                Alternative(
                    "Breadth-first search",
                    "O(V + E)",
                    "O(V)",
                    "Finds shortest paths in unweighted graphs, but can hold a wide frontier "
                    "in memory.",
                ),
            ),
            aliases=("depth-first search", "depth first search", "dfs"),
        ),
        CatalogEntry(
            key="bubble_sort",
            name="Bubble sort",
            category="sorting",
            time="O(n^2)",
            space="O(1)",
            summary=(
                "Repeatedly walks the list swapping neighbouring items that are out of order, "
                "until a pass makes no swaps."
            ),
            assessment=(
                "Fine for learning or tiny inputs, but too slow for real data: the work grows "
                "with the square of the input size."
            ),
            alternatives=(
                Alternative(
                    "Built-in sorted()",
                    "O(n log n)",
                    "O(n)",
                    "Much faster and already written.",
                ),
                Alternative(
                    "Insertion sort",
                    "O(n^2)",
                    "O(1)",
                    "Same worst case, but faster on nearly sorted data.",
                ),
            ),
            aliases=("bubble sort",),
        ),
        CatalogEntry(
            key="euclid_gcd",
            name="Euclidean algorithm",
            category="number theory",
            time="O(log n)",
            space="O(1)",
            summary=(
                "Finds the greatest common divisor by repeatedly replacing the pair (a, b) "
                "with (b, a mod b) until b is zero."
            ),
            assessment="The standard, efficient way to compute a GCD (also available as math.gcd).",
            alternatives=(
                Alternative(
                    "math.gcd",
                    "O(log n)",
                    "O(1)",
                    "Same algorithm, built in and tested.",
                ),
            ),
            aliases=("euclidean algorithm", "euclid", "gcd"),
        ),
        CatalogEntry(
            key="memoized_recursion",
            name="Memoized recursion",
            category="dynamic programming",
            time="O(n)",
            space="O(n)",
            summary=(
                "A recursive function whose results are cached, so each distinct input is "
                "computed only once."
            ),
            assessment=(
                "Turns an exponential recursion into a linear one. Deep inputs can still hit "
                "the recursion limit; an iterative loop avoids that."
            ),
            alternatives=(
                Alternative(
                    "Iterative bottom-up loop",
                    "O(n)",
                    "O(1)",
                    "No recursion limit and often less memory, but the code is less direct.",
                ),
            ),
            aliases=("memoization", "memoized recursion", "dynamic programming"),
        ),
        CatalogEntry(
            key="dijkstra",
            name="Dijkstra's shortest path",
            category="graph",
            time="O((V + E) log V)",
            space="O(V)",
            summary=(
                "Finds the cheapest path from one node to all others by always expanding the "
                "closest unvisited node, kept in a priority queue (heap)."
            ),
            assessment=(
                "The standard choice for shortest paths with non-negative weights. It gives "
                "wrong answers if any edge weight is negative."
            ),
            alternatives=(
                Alternative(
                    "Bellman-Ford",
                    "O(V * E)",
                    "O(V)",
                    "Handles negative weights, but is much slower.",
                ),
                Alternative(
                    "Breadth-first search",
                    "O(V + E)",
                    "O(V)",
                    "Faster, but only correct when every edge costs the same.",
                ),
            ),
            aliases=("dijkstra", "dijkstra's algorithm"),
        ),
        CatalogEntry(
            key="quicksort",
            name="Quick sort",
            category="sorting",
            time="O(n^2)",
            space="O(n)",
            summary=(
                "Picks a pivot, splits the items into those smaller, equal and larger, and "
                "sorts the smaller and larger parts recursively."
            ),
            assessment=(
                "O(n log n) on average, but O(n^2) when pivots split badly (for example "
                "an already sorted list with a first-item pivot). Building new lists costs "
                "O(n) extra memory; an in-place version needs only O(log n). In Python, "
                "sorted() is faster and preferable."
            ),
            alternatives=(
                Alternative(
                    "Built-in sorted()",
                    "O(n log n)",
                    "O(n)",
                    "Guaranteed O(n log n), written in C, nothing to maintain.",
                ),
                Alternative(
                    "Merge sort",
                    "O(n log n)",
                    "O(n)",
                    "No bad worst case and stable, but always uses extra memory.",
                ),
            ),
            aliases=("quick sort", "quicksort"),
        ),
        CatalogEntry(
            key="union_find",
            name="Union-find (disjoint set)",
            category="data structure",
            time="O(α(n))",
            space="O(n)",
            summary=(
                "Tracks which items belong to the same group (O(α(n)) amortized per operation). "
                "find() returns a group's representative; union() merges two groups. "
                "Path compression and union by rank keep both operations almost constant time."
            ),
            assessment=(
                "Excellent for connectivity questions and Kruskal's algorithm. α(n) is the "
                "inverse Ackermann function, below 5 for any practical n. It cannot split a "
                "group again."
            ),
            alternatives=(
                Alternative(
                    "Graph traversal (BFS/DFS)",
                    "O(V + E)",
                    "O(V)",
                    "Fine for a one-off question, but slow if the graph keeps changing.",
                ),
            ),
            aliases=("union-find", "union find", "disjoint set"),
        ),
        CatalogEntry(
            key="topological_sort",
            name="Topological sort (Kahn's algorithm)",
            category="graph",
            time="O(V + E)",
            space="O(V)",
            summary=(
                "Orders the nodes of a directed graph so every edge points forward, by "
                "repeatedly taking a node with no unprocessed incoming edges."
            ),
            assessment=(
                "Optimal, and it detects cycles: if fewer nodes come out than went in, the "
                "graph has a cycle and no valid order exists."
            ),
            alternatives=(
                Alternative(
                    "DFS post-order",
                    "O(V + E)",
                    "O(V)",
                    "Same cost and short to write, but recursion depth can overflow.",
                ),
            ),
            aliases=("topological sort", "topological ordering", "kahn"),
        ),
        CatalogEntry(
            key="sieve",
            name="Sieve of Eratosthenes",
            category="number theory",
            time="O(n log log n)",
            space="O(n)",
            summary=(
                "Finds all primes up to n by crossing out the multiples of each prime, "
                "starting from its square."
            ),
            assessment=(
                "The classic way to list many primes; far faster than testing each number "
                "separately. Memory grows with n, so very large limits need a segmented sieve."
            ),
            alternatives=(
                Alternative(
                    "Trial division per number",
                    "O(n * sqrt(n))",
                    "O(1)",
                    "No memory needed, but much slower for many numbers.",
                ),
            ),
            aliases=("sieve of eratosthenes", "sieve"),
        ),
        CatalogEntry(
            key="kadane",
            name="Kadane's maximum subarray",
            category="dynamic programming",
            time="O(n)",
            space="O(1)",
            summary=(
                "Finds the contiguous run with the largest sum in one pass, tracking the "
                "best sum that ends at the current item and the best seen overall."
            ),
            assessment=(
                "Optimal for this problem. Check what should happen with an empty input, "
                "and note that it returns the largest single item when all are negative."
            ),
            alternatives=(
                Alternative(
                    "Check every subarray",
                    "O(n^2)",
                    "O(1)",
                    "Simpler to reason about, but slow for large inputs.",
                ),
            ),
            aliases=("kadane", "maximum subarray", "max subarray"),
        ),
        CatalogEntry(
            key="matrix_multiplication",
            name="Matrix multiplication (triple loop)",
            category="linear algebra",
            time="O(n·m·p)",
            space="O(n·p)",
            summary=(
                "Multiplies an n×m matrix by an m×p matrix by summing products along three "
                "nested loops; for square matrices that is O(n^3)."
            ),
            assessment=(
                "Correct and easy to follow. In Python, NumPy (@ operator) is orders of "
                "magnitude faster because it uses optimised native libraries."
            ),
            alternatives=(
                Alternative(
                    "NumPy matmul",
                    "O(n^3)",
                    "O(n^2)",
                    "Same asymptotics but vectorised, typically 100x or more faster.",
                ),
                Alternative(
                    "Strassen",
                    "O(n^2.81)",
                    "O(n^2)",
                    "Better asymptotically, but only pays off for very large matrices.",
                ),
            ),
            aliases=("matrix multiplication", "matrix multiply"),
        ),
        CatalogEntry(
            key="floyd_warshall",
            name="Floyd-Warshall all-pairs shortest paths",
            category="graph",
            time="O(V^3)",
            space="O(V^2)",
            summary=(
                "Computes the shortest distance between every pair of nodes by trying each "
                "node k as an intermediate stop."
            ),
            assessment=(
                "Simple and handles negative edges (not negative cycles). The cubic time "
                "suits graphs of a few hundred nodes at most."
            ),
            alternatives=(
                Alternative(
                    "Dijkstra from every node",
                    "O(V (V + E) log V)",
                    "O(V^2)",
                    "Faster on sparse graphs, but needs non-negative weights.",
                ),
            ),
            aliases=("floyd-warshall", "floyd warshall", "floyd"),
        ),
        CatalogEntry(
            key="lru_cache",
            name="LRU cache",
            category="data structure",
            time="O(1)",
            space="O(capacity)",
            summary=(
                "Keeps the most recently used items and evicts the least recently used one "
                "when full, using an ordered dict that moves items to the end on use."
            ),
            assessment=(
                "get and put are O(1). It is not thread-safe as written, and for plain "
                "function results functools.lru_cache does the same job."
            ),
            alternatives=(
                Alternative(
                    "functools.lru_cache",
                    "O(1)",
                    "O(capacity)",
                    "Built in and thread-safe, but only caches function calls.",
                ),
            ),
            aliases=("lru cache", "least recently used"),
        ),
    )
}

# Names a model might use, mapped to catalog keys (lower case).
_ALIASES = {alias: entry.key for entry in CATALOG.values() for alias in entry.aliases}


def find_entry(name: str) -> CatalogEntry | None:
    """The catalog entry a model-supplied algorithm name refers to, if any."""
    lowered = name.strip().lower()
    if lowered in _ALIASES:
        return CATALOG[_ALIASES[lowered]]
    for alias, key in _ALIASES.items():
        if len(alias) > 4 and alias in lowered:
            return CATALOG[key]
    return None
