"""Test braces.

Looking for brace test cases, I stumbled on https://github.com/juliangruber/brace-expansion.
The project contained great tests that mirror Bash 4.3's behavior.  And while this library
was written independently, we used their test sweet to bring this up to Bash 4.3 standard.
"""
import unittest
import wcmatch.braces as braces
import ast
import re


dollar = [
    ['${1..3}', ['${1..3}']],
    ['${a,b}${c,d}', ['${a,b}${c,d}']],
    ['x${a,b}x${c,d}x', ['x${a,b}x${c,d}x']]
]

empty = [
    ['-v{,,,,}', ['-v', '-v', '-v', '-v', '-v']],
    ['{,,}', ['']],
    ['', ['']]
]

negative_incr = [
    ['{3..1}', ['3', '2', '1']],
    ['{10..8}', ['10', '9', '8']],
    ['{10..08}', ['10', '09', '08']],
    ['{c..a}', ['c', 'b', 'a']],
    ['{4..0..2}', ['4', '2', '0']],
    ['{4..0..-2}', ['4', '2', '0']],
    ['{e..a..2}', ['e', 'c', 'a']]
]

nested = [
    ['{a,b{1..3},c}', ['a', 'b1', 'b2', 'b3', 'c']],
    ['{{A..Z},{a..z}}', list('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')],
    ['ppp{,config,oe{,conf}}', ['ppp', 'pppconfig', 'pppoe', 'pppoeconf']]
]

order = [
    ['a{d,c,b}e', ['ade', 'ace', 'abe']]
]

pad = [
    ['{09..11}', ['09', '10', '11']],
    ['{9..11}', ['9', '10', '11']]
]

sequence = [
    ['a{1..2}b{2..3}c', ['a1b2c', 'a1b3c', 'a2b2c', 'a2b3c']],
    ['{1..2}{2..3}', ['12', '13', '22', '23']],
    ['{0..8..2}', ['0', '2', '4', '6', '8']],
    ['{1..8..2}', ['1', '3', '5', '7']],
    ['{3..-2}', ['3', '2', '1', '0', '-1', '-2']],
    ['1{a..b}2{b..c}3', ['1a2b3', '1a2c3', '1b2b3', '1b2c3']],
    ['{a..b}{b..c}', ['ab', 'ac', 'bb', 'bc']],
    ['{a..k..2}', ['a', 'c', 'e', 'g', 'i', 'k']],
    ['{b..k..2}', ['b', 'd', 'f', 'h', 'j']]
]


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
        """Test that dollar expansions don't expand."""

        self.eval_brace_cases(dollar)

    def test_empty_expand(self):
        """Test empty expansion."""

        self.eval_brace_cases(empty)

    def test_negative_incr_expand(self):
        """Test negative increment expansion."""

        self.eval_brace_cases(negative_incr)

    def test_nested_expand(self):
        """Test nested expansion."""

        self.eval_brace_cases(nested)

    def test_order_expand(self):
        """Test ordered expansion."""

        self.eval_brace_cases(order)

    def test_pad_expand(self):
        """Test padded expansion."""

        self.eval_brace_cases(pad)

    def test_pad_expand(self):
        """Test sequence expansion."""

        self.eval_brace_cases(sequence)

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
