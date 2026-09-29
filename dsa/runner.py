"""run() / run_design(): read input.txt, call the solution, write output.txt, check expected.txt."""
import contextlib
import json
import os
import sys

from .compare import fmt, matches, to_plain
from .parsing import parse_value, read_cases, read_expected


def _caller_dir(depth=2):
    return os.path.dirname(os.path.abspath(sys._getframe(depth).f_code.co_filename))


def run(fn, in_place=False, parse=None, unordered=False, tol=None, check=None):
    """Run fn on every case in input.txt of the calling file's folder.

    in_place   fn edits its first argument and returns None; that argument is the answer.
    parse      per-argument converters, e.g. [to_linked, None]; None leaves an argument as is.
    unordered  compare lists ignoring order (recursively).
    tol        compare numbers within this tolerance.
    check      check(args, out) -> bool; verifies the answer instead of matching expected.txt.
    """
    _run(_caller_dir(), fn, in_place, parse, unordered, tol, check)


def run_design(cls, unordered=False, tol=None):
    """Design problems (LRUCache, MinStack, ...). input.txt: line 1 the operations, line 2 the arguments."""
    _run_design(_caller_dir(), cls, unordered, tol)


def _run(directory, fn, in_place=False, parse=None, unordered=False, tol=None, check=None):
    def execute(lines):
        args = [parse_value(line) for line in lines]
        for i, convert in enumerate(parse or []):
            if convert is not None and i < len(args):
                args[i] = convert(args[i])
        out = fn(*args)
        return args, (args[0] if in_place else out)

    _drive(directory, execute, fmt, unordered, tol, check)


def _run_design(directory, cls, unordered=False, tol=None):
    def execute(lines):
        if len(lines) != 2:
            raise SystemExit('design input needs 2 lines per case: operations, then arguments')
        ops, arg_lists = parse_value(lines[0]), parse_value(lines[1])
        obj, results = None, []
        for i, (op, a) in enumerate(zip(ops, arg_lists)):
            if i == 0:
                obj = cls(*a)
                results.append(None)
            else:
                results.append(getattr(obj, op)(*a))
        return [ops, arg_lists], results

    _drive(directory, execute, lambda out: json.dumps(to_plain(out)), unordered, tol, None)


def _drive(directory, execute, render, unordered, tol, check):
    cases = read_cases(os.path.join(directory, 'input.txt'))
    expected = read_expected(os.path.join(directory, 'expected.txt'))
    if expected is not None and len(expected) != len(cases):
        raise SystemExit('expected.txt has %d lines but input.txt has %d cases' % (len(expected), len(cases)))

    failures = []
    with open(os.path.join(directory, 'output.txt'), 'w') as f, contextlib.redirect_stdout(f):
        for i, lines in enumerate(cases):
            args, out = execute(lines)
            if i:
                print()
            print(render(out))
            if check is not None:
                ok = bool(check(args, to_plain(out)))
            elif expected is not None:
                ok = matches(out, expected[i], unordered, tol)
            else:
                ok = True
            if not ok:
                failures.append((i, lines, expected[i] if expected is not None else None, to_plain(out)))

    if failures:
        for i, lines, want, got in failures:
            print('FAIL case %d/%d' % (i + 1, len(cases)), file=sys.stderr)
            print('  input:    ' + '  |  '.join(lines), file=sys.stderr)
            if want is not None:
                print('  expected: %r' % (want,), file=sys.stderr)
            print('  got:      %r' % (got,), file=sys.stderr)
        sys.exit('%d of %d cases failed' % (len(failures), len(cases)))
