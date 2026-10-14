"""Keyword search (BM25) over a case's summary, feature, description, steps and expected result."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from collections.abc import Callable

from .catalog import Case

TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "its", "of", "on", "or",
             "the", "this", "to", "with"}
K1, B = 1.2, 0.75


def tokens(text: str) -> list[str]:
    return [token for token in TOKEN.findall(text.lower()) if token not in STOPWORDS]


class SearchIndex:
    def __init__(self, cases: tuple[Case, ...]):
        self.cases = cases
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.lengths: list[int] = []
        self.titles: list[str] = []
        for index, case in enumerate(cases):
            # The summary counts twice: it names what the case is about.
            text = " ".join([case.summary, case.summary, case.feature, case.module, case.test_type, case.description,
                             " ".join(case.steps), case.expected_result, " ".join(case.labels)])
            counts = Counter(tokens(text))
            for term, frequency in counts.items():
                self.postings[term].append((index, frequency))
            self.lengths.append(sum(counts.values()))
            self.titles.append(" ".join(tokens(f"{case.summary} {case.feature}")))
        self.average = sum(self.lengths) / max(len(self.lengths), 1)
        total = len(cases)
        self.idf = {term: math.log(1 + (total - len(p) + 0.5) / (len(p) + 0.5)) for term, p in self.postings.items()}

    def search(self, query: str, allowed: Callable[[Case], bool]) -> list[tuple[Case, float, list[str]]]:
        terms = list(dict.fromkeys(tokens(query)))
        scores: dict[int, float] = defaultdict(float)
        matched: dict[int, list[str]] = defaultdict(list)
        for term in terms:
            for index, frequency in self.postings.get(term, ()):
                norm = frequency + K1 * (1 - B + B * self.lengths[index] / self.average)
                scores[index] += self.idf[term] * frequency * (K1 + 1) / norm
                matched[index].append(term)
        phrase = " ".join(terms)
        results = []
        for index, score in scores.items():
            case = self.cases[index]
            if not allowed(case):
                continue
            if len(terms) > 1 and phrase in self.titles[index]:
                score += 2.0  # the words appear together in the summary or feature
            results.append((case, round(score, 3), matched[index]))
        results.sort(key=lambda item: (-item[1], item[0].number))
        return results
