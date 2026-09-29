"""Turning results into plain data, printing them, and comparing them."""
from .structures import ListNode, TreeNode, from_linked, from_tree


def to_plain(x):
    """ListNode/TreeNode/tuple/set -> lists, recursively."""
    if isinstance(x, ListNode):
        return from_linked(x)
    if isinstance(x, TreeNode):
        return from_tree(x)
    if isinstance(x, (list, tuple)):
        return [to_plain(v) for v in x]
    if isinstance(x, (set, frozenset)):
        return sorted((to_plain(v) for v in x), key=repr)
    if isinstance(x, dict):
        return {k: to_plain(v) for k, v in x.items()}
    return x


def fmt(x):
    """Human-readable form for output.txt: a matrix is one row per line, a list is space-separated."""
    x = to_plain(x)
    if isinstance(x, list) and x and all(isinstance(r, list) for r in x):
        return '\n'.join(fmt(r) for r in x)
    if isinstance(x, list):
        return ' '.join(map(str, x))
    return str(x)


def _canon(x):
    if isinstance(x, list):
        return sorted((_canon(v) for v in x), key=repr)
    if isinstance(x, dict):
        return {k: _canon(v) for k, v in x.items()}
    return x


def _equals(a, b, tol):
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol if tol is not None else a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_equals(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_equals(a[k], b[k], tol) for k in a)
    return a == b


def matches(got, expected, unordered=False, tol=None):
    got, expected = to_plain(got), to_plain(expected)
    if unordered:
        got, expected = _canon(got), _canon(expected)
    return _equals(got, expected, tol)
