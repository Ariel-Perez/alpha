#!/usr/bin/python
# -*- coding: utf8 -*-
"""Spelling Correction."""
import collections

import wordmetric


class SpellingCorector:
    """
    Basic spelling corrector class.

    Doesn't implement any method.
    """
    def __init__(self, language='en'):
        """Initializes an instance of SpellingCorrector with a language."""
        self.language = language

    def suggest(self, word):
        """Get possible corrections for the word."""
        raise NotImplementedError()

    def correct(self, word):
        """Get the most likely suggestion for the word."""
        raise NotImplementedError()


class Term:
    def __init__(self, term, count=0):
        self.term = term
        self.count = count

    def __str__(self):
        return self.term

    def __repr__(self):
        return self.term

    def __hash__(self):
        return hash(self.term)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.term == other.term
        else:
            return False

    def __ne__(self, other):
        return not Term.__eq__(self, other)


class Suggestion:
    def __init__(self, term, count=0, distance=float('inf')):
        self.term = term
        self.count = count
        self.distance = distance

    def __str__(self):
        return self.term

    def __repr__(self):
        return self.term

    def __hash__(self):
        return hash(self.term)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.term == other.term
        else:
            return False

    def __ne__(self, other):
        return not Suggestion.__eq__(self, other)


class FarooSpellingCorrector(SpellingCorector):
    """
    Faroo Spelling Corrector.

    Faster lookup through Symmetric Delete spelling correction algorithm.

    Python implementation of the algorithm by Wolf Garbe <wolf.garbe@faroo.com>
    Source:
    "http://blog.faroo.com/2012/06/07/improved-edit-distance-based-spelling-correction/"
    """
    def __init__(self, language='en',
                 max_distance=2, keep_all_suggestions=False, metric=None):
        """Initialize an instance of FarooSpellingCorrector."""
        SpellingCorector.__init__(self, language)
        self.max_distance = max_distance
        self.keep_all_suggestions = keep_all_suggestions

        self.dictionary = collections.defaultdict(lambda: None)
        self.suggestions = collections.defaultdict(list)
        self.metric = metric or wordmetric.LevehnsteinDistance()

    def add_entry(self, entry):
        """
        Add an entry to the dictionary.

        Returns whether the entry is new.

        The entry is a string containing a single word.
        After calling this method, dictionary contains a Term object
        for the given entry with the updated count.

        The term object is indexed using the entry string.

        >>> f = FarooSpellingCorrector(max_distance=2)
        >>> f.add_entry('hey')
        True
        >>> f.dictionary['hey'].term
        'hey'
        >>> f.dictionary['hey'].count
        1
        >>> f.suggestions['he']
        [hey]
        >>> f.suggestions['y']
        [hey]
        >>> len(f.suggestions)
        7
        """
        term = self.dictionary[entry]
        new = term is None

        if new:
            self.dictionary[entry] = term = Term(entry, 0)
            deletes = self.edits(entry, max_distance=self.max_distance)

            self.suggestions[entry] = [Suggestion(entry, distance=0)]
            for delete in deletes:
                suggestion = Suggestion(entry, distance=delete.distance)

                suggestions = self.suggestions[delete.term]
                self.keep_lowest_distance(suggestions, suggestion)

        term.count += 1

        return new

    def add_corpus(self, corpus):
        """
        Add a bunch of words to the dictionary.

        Returns the number of unique words added.

        Corpus is assumed to be a list of strings corresponding to words.
        All words are added to the inner dictionary and their counts updated.

        >>> corpus = ["hello", "hello", "hello", "world", "world"]
        >>> f = FarooSpellingCorrector()
        >>> f.add_corpus(corpus)
        2
        >>> f.dictionary['hello'].count
        3
        """
        new_word_count = 0
        for word in corpus:
            if self.add_entry(word):
                new_word_count += 1

        return new_word_count

    def edits(self, entry, max_distance=1, distance=1):
        """
        Get all possible deleting edits for given entry up to max_distance.

        >>> f = FarooSpellingCorrector()
        >>> word = "hell"
        >>> supposed_edits = {Suggestion(x) for x in ["ell", "hll", "hel"]}
        >>> actual_edits = f.edits(word, max_distance=1)
        >>> len(actual_edits) == len(supposed_edits)
        True
        >>> all([x in actual_edits for x in supposed_edits])
        True

        >>> f = FarooSpellingCorrector()
        >>> word = "abc"
        >>> supposed_edits = {
        ...     Suggestion(x) for x in ["ab", "ac", "bc", "a", "b", "c"]}
        >>> actual_edits = f.edits(word, max_distance=2)
        >>> len(actual_edits) == len(supposed_edits)
        True
        >>> all([x in actual_edits for x in supposed_edits])
        True
        """
        deletes = set()

        n = len(entry)
        if n > 1:
            for i in range(n):
                modified_entry = entry[:i] + entry[i + 1:]
                delete = Suggestion(modified_entry, distance=distance)

                if delete not in deletes:
                    deletes.add(delete)

                    if distance < max_distance:
                        deletes.update(
                            self.edits(
                                modified_entry,
                                max_distance=max_distance,
                                distance=distance + 1)
                        )

        return deletes

    def distance(self, original, other):
        """
        Get the actual distance between two words.

        Uses the metric set at initialization.
        """
        dist = self.metric.edit_distance(original, other)
        return dist

    def keep_lowest_distance(self, suggestion_list, suggestion):
        """Add the new suggestion to the list and remove all non-minimal."""
        if suggestion_list and not self.keep_all_suggestions:
            if suggestion_list[0].distance > suggestion.distance:
                del suggestion_list[:]

        if self.keep_all_suggestions or not suggestion_list \
           or suggestion_list[0].distance >= suggestion.distance:
            suggestion_list.append(suggestion)

    def suggest(self, word):
        """
        Get possible corrections for the word.

        >>> corpus = ["hello", "hell"]
        >>> f = FarooSpellingCorrector(
        ...     keep_all_suggestions=True,
        ...     max_distance=2
        ... )
        >>> n = f.add_corpus(corpus)
        >>> f.suggest("hel")
        [hell, hello]

        >>> f = FarooSpellingCorrector(
        ...     keep_all_suggestions=False,
        ...     max_distance=2
        ... )
        >>> n = f.add_corpus(corpus)
        >>> f.suggest("hel")
        [hell]
        >>> f.suggest("help")
        [hell]
        >>> f.suggest("hallo")
        [hello]
        """
        suggestions = set()
        candidates = collections.deque([Suggestion(word, 1, 0)])
        seen = set(candidates)

        while len(candidates) > 0:
            candidate = candidates.popleft()
            candidate_suggestions = self.suggestions[candidate.term]

            for candidate_suggestion in candidate_suggestions:
                distance = candidate_suggestion.distance
                if candidate_suggestion.term != candidate.term:
                    distance = self.distance(candidate.term, word)

                if distance <= self.max_distance:
                    if suggestions and not self.keep_all_suggestions:
                        some_suggestion = next(iter(suggestions))
                        # Skip if worse
                        if some_suggestion.distance \
                           < distance:
                            continue
                        # Clear all if better
                        if some_suggestion.distance \
                           > distance:
                            suggestions.clear()

                    suggestions.add(candidate_suggestion)

            if candidate.distance < self.max_distance:
                candidate_edits = self.edits(candidate.term, max_distance=1)
                for candidate_edit in candidate_edits:
                    if candidate_edit not in seen:
                        candidates.append(candidate_edit)
                        seen.add(candidate_edit)

        return sorted(suggestions,
                      key=lambda s: (s.distance, s.count))

    def correct(self, word):
        """
        Get the most likely suggestion for the word.

        >>> f = FarooSpellingCorrector(max_distance=2)
        >>> corpus = ["hello", "hell"]
        >>> n = f.add_corpus(corpus)
        >>> f.correct("hel")
        hell
        """
        suggestions = self.suggest(word)
        return suggestions[0] if suggestions else None


def unit_test():
    import doctest
    doctest.testmod()


if __name__ == '__main__':
    unit_test()
