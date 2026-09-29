import os
import tempfile
import unittest

from dsa.compare import fmt, matches
from dsa.parsing import parse_value
from dsa.runner import _run, _run_design
from dsa.structures import from_linked, from_tree, to_linked, to_tree


def problem(input_text, expected_text=None):
    d = tempfile.mkdtemp()
    with open(os.path.join(d, 'input.txt'), 'w') as f:
        f.write(input_text)
    if expected_text is not None:
        with open(os.path.join(d, 'expected.txt'), 'w') as f:
            f.write(expected_text)
    return d


def output(d):
    with open(os.path.join(d, 'output.txt')) as f:
        return f.read()


class ParseTests(unittest.TestCase):
    def test_values(self):
        self.assertEqual(parse_value('[3, null, true]'), [3, None, True])
        self.assertEqual(parse_value("'ab'"), 'ab')
        self.assertEqual(parse_value('(1, 2)'), (1, 2))
        self.assertEqual(parse_value('abcba'), 'abcba')
        self.assertEqual(parse_value('3 5'), '3 5')
        self.assertIsNone(parse_value('None'))


class StructureTests(unittest.TestCase):
    def test_linked_roundtrip(self):
        self.assertEqual(from_linked(to_linked([1, 2, 3])), [1, 2, 3])
        self.assertIsNone(to_linked([]))

    def test_tree_roundtrip(self):
        vals = [3, 9, 20, None, None, 15, 7]
        self.assertEqual(from_tree(to_tree(vals)), vals)
        self.assertEqual(from_tree(to_tree([1, None, 2])), [1, None, 2])
        self.assertIsNone(to_tree([]))


class CompareTests(unittest.TestCase):
    def test_exact_and_bool(self):
        self.assertTrue(matches([1, 2], [1, 2]))
        self.assertFalse(matches(1, True))
        self.assertFalse(matches([1, 2], [2, 1]))

    def test_unordered_nested(self):
        self.assertTrue(matches([[2, 1], [3]], [[3], [1, 2]], unordered=True))
        self.assertFalse(matches([[2, 1], [3]], [[3], [1, 4]], unordered=True))

    def test_tolerance(self):
        self.assertTrue(matches([0.30000000000000004], [0.3], tol=1e-9))
        self.assertFalse(matches(0.31, 0.3, tol=1e-9))

    def test_none_is_a_value(self):
        self.assertTrue(matches(None, None))
        self.assertFalse(matches(None, 0))

    def test_fmt(self):
        self.assertEqual(fmt([1, 2, 3]), '1 2 3')
        self.assertEqual(fmt([[1, 2], [3, 4]]), '1 2\n3 4')
        self.assertEqual(fmt(to_linked([1, 2])), '1 2')
        self.assertEqual(fmt('abc'), 'abc')


class RunTests(unittest.TestCase):
    def test_plain_pass_is_silent(self):
        d = problem('[1, 2, 3]\n2\n', '[3, 4, 5]\n')
        _run(d, lambda nums, k: [n + k for n in nums])
        self.assertEqual(output(d), '3 4 5\n')

    def test_no_expected_file(self):
        d = problem('5\n')
        _run(d, lambda n: n * 2)
        self.assertEqual(output(d), '10\n')

    def test_failure_exits_and_reports_all_cases(self):
        d = problem('1\n\n2\n\n3\n', '2\n4\n7\n')
        with self.assertRaises(SystemExit) as cm:
            _run(d, lambda n: n * 2)
        self.assertIn('1 of 3', str(cm.exception))
        self.assertEqual(output(d), '2\n\n4\n\n6\n')

    def test_in_place(self):
        d = problem('[3, 1, 2]\n', '[1, 2, 3]\n')
        _run(d, lambda nums: nums.sort(), in_place=True)

    def test_none_return_is_a_real_answer(self):
        d = problem('5\n', 'null\n')
        _run(d, lambda n: None)
        self.assertEqual(output(d), 'None\n')

    def test_unordered_and_custom_check(self):
        d = problem('[1, 2]\n', '[[2, 1], [1, 2]]\n')
        _run(d, lambda nums: [[1, 2], [2, 1]], unordered=True)
        d = problem('[1, 2]\n')
        with self.assertRaises(SystemExit):
            _run(d, lambda nums: nums, check=lambda args, out: False)

    def test_linked_list_and_tree(self):
        d = problem('[1, 2, 3]\n', '[3, 2, 1]\n')

        def reverse(head):
            prev = None
            while head:
                head.next, prev, head = prev, head, head.next
            return prev
        _run(d, reverse, parse=[to_linked])
        d = problem('[1, 2, 3]\n', '[1, 3, 2]\n')

        def mirror(root):
            root.left, root.right = root.right, root.left
            return root
        _run(d, mirror, parse=[to_tree])

    def test_expected_count_mismatch(self):
        d = problem('1\n\n2\n', '2\n')
        with self.assertRaises(SystemExit):
            _run(d, lambda n: n)

    def test_design(self):
        class Counter:
            def __init__(self, start):
                self.n = start

            def inc(self):
                self.n += 1
                return self.n

            def reset(self):
                self.n = 0

        d = problem('["Counter", "inc", "inc", "reset"]\n[[5], [], [], []]\n', '[null, 6, 7, null]\n')
        _run_design(d, Counter)
        self.assertEqual(output(d), '[null, 6, 7, null]\n')


if __name__ == '__main__':
    unittest.main()
