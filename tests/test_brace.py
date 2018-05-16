"""Test braces."""
import unittest
import wcmatch.braces as braces
import ast
import re


dollar = [
    ['${1..3}', ['${1..3}']],
    ['${a,b}${c,d}', ['${a,b}${c,d}']],
    ['x${a,b}x${c,d}x', ['x${a,b}x${c,d}x']]
]

empty = []


class TestBraces(unittest.TestCase):
    """Test globbing."""

    def eval_str_esc(self, string):
        r"""Evaluate buffer as a string buffer counting things like \\ as \."""

        return ast.literal_eval('"%s"' % string.strip().replace('"', '\\"'))

    def eval_brace_cases(self, cases):
        """Evaluate the brace cases."""

        for p in cases:
            print("PATTERN: ", p[0])
            expanded_pattern = []
            try:
                expanded_pattern.extend(
                    list(braces.iexpand(p[0]))
                )
            except Exception as e:
                expanded_pattern.append(p[0])
            result = expanded_pattern
            goal = p[1]
            print('TEST: ', result, '<==>', goal, '\n')
            self.assertEqual(result, goal)

    def test_dollar_expand(self):
        """Test brace expansion."""

        self.eval_brace_cases(dollar)

    def test_bash_cases(self):
        """Test bash cases."""

        RE_REMOVE = re.compile(r'^\[|\]$')
        RE_SPLIT = re.compile(r'><><><><')

        with open('tests/brace-results.txt', 'r') as r:
            # Split by test cases
            results = RE_SPLIT.split(r.read())
            results.pop()
            # Split by line within test case
            wanted = [x.split('\n') for x in results]

        with open('tests/brace-cases.txt', 'r') as r:
            # Split by line ignoring commented lines.
            # We may have blank lines that get included,
            # But the test will compare those too, so it
            # isn't a problem.
            cases = [x.strip() for x in r.read().split('\n') if not x.startswith('#')]
            cases.pop()

        count = 0
        while cases:
            count += 1
            test_case = self.eval_str_esc(cases.pop(0))
            entry = wanted.pop(0)
            print('TEST: ', test_case)
            self.assertEqual(test_case, entry.pop(0))
            expansions = braces.expand(test_case)
            if len(expansions) == 1 and not expansions[0]:
                entry.pop(0)
            else:
                for a in expansions:
                    b = RE_REMOVE.sub('', entry.pop(0))
                    # print('    ', a, '<==>', b)
                    self.assertEqual(a, b)
