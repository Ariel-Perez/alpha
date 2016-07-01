#!/usr/bin/python
# -*- coding: utf8 -*-
"""Metrics for word comparison."""
import collections
import itertools


def squash(word):
    """
    Replace multiple occurrences of a letter. Allow 2 at most.

    >>> squash('woooooooooo')
    'woo'
    >>> squash('bookkeeper')
    'bookkeeper'
    """
    word = ''.join(''.join(s)[:2] for _, s in itertools.groupby(word))
    return word


class Distance:
    """Class that computes distance between two words."""

    def edit_distance(self, s, t):
        """Compute the edit distance between two strings."""
        raise NotImplementedError()


class LevehnsteinDistance(Distance):
    """Levehnstein distance between two words."""

    def letter_distance(self, a, b):
        """Compute the distance between two letters."""
        if a == b:
            return 0
        elif {a, b} in [
                {u'á', u'a'},
                {u'é', u'e'},
                {u'í', u'i'},
                {u'ó', u'o'},
                {u'ú', u'u'}]:
            return 0.1
        else:
            return 1

    def edit_distance(self, s, t):
        u"""
        Compute the edit distance between two strings.

        Previously, collapses all repetition of 3+ characters to 2 at most.

        >>> ld = LevehnsteinDistance()
        >>> ld.edit_distance("hello", "ell")
        2
        >>> ld.edit_distance("penguin", "pencil")
        3
        >>> ld.edit_distance("hallo", "hell")
        2
        >>> ld.edit_distance("hello", "HELLO")
        0
        >>> ld.edit_distance(u"ÁREA", u"área")
        0
        >>> ld.edit_distance(u"ÁREA", u"area")
        0.1
        """
        s = squash(s.lower())
        t = squash(t.lower())

        m = len(s)
        n = len(t)

        # Create the distance matrix. Initially all zero.
        d = [[0] * (n + 1) for c in range(m + 1)]

        # First column and row are sequences 0..m, 0..n
        d[0] = [i for i in range(n + 1)]
        for i in range(m):
            d[i + 1][0] = d[i][0] + 1

        # Use dynamic programming to find the minimum cost
        for j in range(1, n + 1):
            for i in range(1, m + 1):
                replace_cost = d[i - 1][j - 1] + self.letter_distance(
                    s[i - 1], t[j - 1])
                delete_cost = d[i - 1][j] + 1
                insert_cost = d[i][j - 1] + 1

                # The cost of swapping letters only makes sense for i,j >= 2
                if i >= 2 and j >= 2:
                    swap_cost = d[i - 2][j - 2] + self.letter_distance(
                        s[i - 2], t[j - 1]) + self.letter_distance(
                        s[i - 1], t[j - 2]) + 1
                    d[i][j] = min(
                        replace_cost, delete_cost, insert_cost, swap_cost)

                else:
                    d[i][j] = min(
                        replace_cost, delete_cost, insert_cost)

        return d[m][n]


class TypoAdmissiveDistance(LevehnsteinDistance):
    """Distance metric that allows for keyboard typos."""

    def __init__(self):
        """Initialize an instance of TypoAdmissiveDistance."""
        self.dist_dict = self.build_distance_dictionary()

    def letter_distance(self, a, b):
        """Get the distance between two letters using the dictionary."""
        if a == b:
            return 0
        return self.dist_dict[(a, b)]

    def build_distance_dictionary(self):
        """
        Build a distance dictionary that gives less penalization to typos.

        Something might be a typo if swapped letters are close by
        in the keyboard.

        >>> tad = TypoAdmissiveDistance()
        >>> d = tad.dist_dict
        >>> d[('a', 's')]
        0.8
        >>> d[('a', 'p')]
        1
        """
        dist_dict = collections.defaultdict(lambda: 1)
        typo_value = 0.8

        keyboard_map = [
            [u'q', u'w', u'e', u'r', u't', u'y', u'u', u'i', u'o', u'p'],
            [None, u'a', u's', u'd', u'f', u'g', u'h', u'j', u'k', u'l', u'ñ'],
            [None, None, u'z', u'x', u'c', u'v', u'b', u'n', u'm']
        ]

        for y, row in enumerate(keyboard_map):
            for x, col in enumerate(row):
                current = keyboard_map[y][x]
                if not current:
                    continue

                if x + 1 < len(row):
                    other = keyboard_map[y][x + 1]
                    dist_dict[(current, other)] = typo_value
                    dist_dict[(other, current)] = typo_value

                if y + 1 < len(keyboard_map) and x < len(keyboard_map[y + 1]):
                    other = keyboard_map[y + 1][x]
                    dist_dict[(current, other)] = typo_value
                    dist_dict[(other, current)] = typo_value

                if y + 1 < len(keyboard_map) and \
                   x + 1 < len(keyboard_map[y + 1]):
                    other = keyboard_map[y + 1][x + 1]
                    dist_dict[(current, other)] = typo_value
                    dist_dict[(other, current)] = typo_value

        return dist_dict


def unit_test():
    """Test the module."""
    import doctest
    doctest.testmod()


if __name__ == '__main__':
    unit_test()
