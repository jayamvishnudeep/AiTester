"""Keyword search over the skills: BM25 with field weights, QA synonyms and stemming.

Words are normalised before they are compared, on both sides: "pw" means Playwright, "bug"
means defect, and creator / generator / writer / builder all mean "create", so "test case
creator" finds test-case-writer. A skill whose name holds the query words gets a boost.
"""

from __future__ import annotations

import difflib
import functools
import math
import re
from collections import Counter, defaultdict
from collections.abc import Callable

import snowballstemmer

from .catalog import Skill

TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for", "from", "how", "i", "in", "is", "it",
    "its", "me", "my", "of", "on", "or", "our", "should", "that", "the", "this", "to", "we", "what", "when",
    "which", "with", "you", "your", "skill", "skills", "find", "need", "want", "related",
}
# One canonical word per idea; a value with spaces expands into several words.
SYNONYMS = {
    "pw": "playwright", "se": "selenium", "cy": "cypress", "wd": "webdriver",
    "bug": "defect", "bugs": "defect", "defects": "defect",
    "a11y": "accessibility", "perf": "performance", "rtm": "traceability", "rca": "root cause",
    "bdd": "bdd gherkin", "e2e": "end to end", "llms": "llm", "agents": "agent", "agentic": "agent",
    "creator": "create", "creators": "create", "creating": "create", "creates": "create",
    "generator": "create", "generate": "create", "generates": "create", "generating": "create",
    "writer": "create", "write": "create", "writes": "create", "writing": "create",
    "builder": "create", "build": "create", "builds": "create", "building": "create",
    "tester": "test", "testing": "test", "tests": "test",
    "analyzer": "analyze", "analyser": "analyze", "analysis": "analyze", "analyse": "analyze", "analyzes": "analyze",
    "planner": "plan", "planning": "plan", "plans": "plan",
    "designer": "design", "designs": "design", "designing": "design",
    "reporter": "report", "reporting": "report", "reports": "report",
    "selector": "select", "selection": "select",
    "tracker": "track", "tracking": "track",
    "debugger": "debug", "debugging": "debug",
    "scanner": "scan", "scanning": "scan",
    "mocker": "mock", "mocking": "mock", "mocks": "mock", "stub": "mock", "stubs": "mock", "stubbing": "mock",
    "evaluator": "eval", "evaluate": "eval", "evaluation": "eval", "evaluations": "eval", "evals": "eval",
    "reviewer": "review", "reviews": "review", "reviewing": "review",
    "configurator": "config", "configure": "config", "configuration": "config",
    "flakiness": "flaky", "flake": "flaky", "auditor": "audit",
}
K1, B = 1.2, 0.75
WEIGHTS = {"name": 4, "title": 2, "category": 3, "description": 2, "body": 1}
# Extra points, scaled by the share of the query (by IDF) behind them: query words in the skill's
# name, query words that name its category ("performance", "cypress", "bug"), and query coverage.
NAME_BOOST, CATEGORY_BOOST, COVERAGE_BOOST = 3.0, 2.0, 1.0
# ...and by the share of the skill's name the query covers: "test data" fits test-data-generator
# better than test-data-privacy-masker.
NAME_FIT_BOOST = 4.0
# A name that starts with the query is what the query is about: "regression" -> regression-suite-selector.
PREFIX_BOOST = 1.0
# Query words that are in no skill name or category ("login", "checkout") describe what is being
# tested, not which skill to use, so they count for less.
CONTEXT_WEIGHT = 0.6
# Phrases whose meaning the single words miss: "load test" is performance testing, not ETL loading.
PHRASES = {
    r"\b(load|stress|soak|spike|endurance) ?test": "performance",
    r"\bpen(etration)? ?test": "security",
    r"\bpage (load|speed)": "web performance",
    r"\bsmoke test": "regression",
}
_stemmer = snowballstemmer.stemmer("english")


@functools.lru_cache(maxsize=None)
def stem(word: str) -> str:
    """Cached: the skills reuse a few thousand words, and the pure-Python stemmer is slow."""
    return _stemmer.stemWord(word)


def words(text: str) -> list[str]:
    """Normalised search words: lower-case, synonyms applied, stopwords dropped, stemmed."""
    out = []
    for token in TOKEN.findall(text.lower()):
        for word in SYNONYMS.get(token, token).split():
            if word not in STOPWORDS:
                out.append(stem(word))
    return out


# Category words too common to say which category a query means.
GENERIC_CATEGORY_WORDS = set(words("test pack management development analysis"))


class SearchIndex:
    def __init__(self, skills: tuple[Skill, ...]):
        self.skills = skills
        self.name_words: list[set[str]] = []
        self.name_sequences = [words(skill.name.replace("-", " ")) for skill in skills]
        self.category_words = [set(words(skill.category)) - GENERIC_CATEGORY_WORDS for skill in skills]
        self.counts: list[Counter] = []
        self.postings: dict[str, list[int]] = defaultdict(list)
        for index, skill in enumerate(skills):
            fields = {
                "name": skill.name.replace("-", " "),
                "title": skill.title,
                # STLC-phase skills answer to "stlc"; the word itself rarely appears in a SKILL.md.
                "category": f"{skill.category} {skill.pack or ''} {skill.stlc_phase or ''}"
                            + (" stlc software testing life cycle" if skill.kind == "stlc-phase" else ""),
                "description": skill.description,
                "body": skill.body,
            }
            counts: Counter = Counter()
            for field, text in fields.items():
                for word in words(text):
                    counts[word] += WEIGHTS[field]
            self.counts.append(counts)
            self.name_words.append(set(words(fields["name"])))
            for word in counts:
                self.postings[word].append(index)
        self.lengths = [sum(c.values()) for c in self.counts]
        self.average = sum(self.lengths) / max(len(self.lengths), 1)
        total = len(skills)
        self.idf = {w: math.log(1 + (total - len(ids) + 0.5) / (len(ids) + 0.5)) for w, ids in self.postings.items()}
        self.label_words = set().union(*self.name_words, *self.category_words) if skills else set()
        self._vectors: list[dict[str, float]] | None = None
        # Words worth correcting a typo to: what the skills are called and grouped by.
        self.vocabulary = sorted({t for s in skills for t in TOKEN.findall(f"{s.name} {s.title} {s.category}".lower())
                                  if len(t) > 2})

    def correct(self, query: str) -> str | None:
        """The query with unknown, misspelt words swapped for the closest skill word ("playwrite" ->
        "playwright"), or None when there is nothing to correct."""
        fixed, changed = [], False
        for token in TOKEN.findall(query.lower()):
            unknown = len(token) > 3 and token not in SYNONYMS and any(w not in self.postings for w in words(token))
            close = difflib.get_close_matches(token, self.vocabulary, n=1, cutoff=0.8) if unknown else []
            fixed.append(close[0] if close else token)
            changed = changed or bool(close)
        return " ".join(fixed) if changed else None

    def search(self, query: str, allowed: Callable[[Skill], bool] = lambda skill: True) -> list[tuple[Skill, float, list[str], str]]:
        """Matching skills, best first, each with its score, the query words it matched, and why."""
        hints = " ".join(extra for pattern, extra in PHRASES.items() if re.search(pattern, query.lower()))
        terms = list(dict.fromkeys(words(f"{query} {hints}")))
        if not terms:
            return []
        weight = {t: 1.0 if t in self.label_words else CONTEXT_WEIGHT for t in terms}
        originals = {}
        for token in TOKEN.findall(f"{query} {hints}".lower()):
            for word in SYNONYMS.get(token, token).split():
                if word not in STOPWORDS:
                    originals.setdefault(stem(word), token)
        # A word's share of the query by IDF: "test" is in every skill, so it counts for little.
        total = sum(self.idf.get(t, 0.0) for t in terms) or 1.0

        def share(found: list[str]) -> float:
            return sum(self.idf.get(t, 0.0) for t in found) / total

        results = []
        for index, skill in enumerate(self.skills):
            if not allowed(skill):
                continue
            counts = self.counts[index]
            matched = [t for t in terms if t in counts]
            if not matched:
                continue
            norm = K1 * (1 - B + B * self.lengths[index] / self.average)
            score = sum(weight[t] * self.idf[t] * counts[t] * (K1 + 1) / (counts[t] + norm) for t in matched)
            in_name = [t for t in terms if t in self.name_words[index]]
            in_category = [t for t in terms if t in self.category_words[index]]
            score += NAME_BOOST * share(in_name)  # the name says what the skill is for
            name_mass = sum(self.idf.get(t, 0.0) for t in self.name_words[index]) or 1.0
            score += NAME_FIT_BOOST * sum(self.idf.get(t, 0.0) for t in in_name) / name_mass
            leading = next((n for n, (a, b) in enumerate(zip(terms, self.name_sequences[index])) if a != b),
                           min(len(terms), len(self.name_sequences[index])))
            score += PREFIX_BOOST * leading / len(terms)
            score += CATEGORY_BOOST * share(in_category)  # "performance ..." means the Performance pack
            score += COVERAGE_BOOST * share(matched)  # covering every query word beats repeating one
            why = []
            if in_name:
                why.append("name: " + ", ".join(originals.get(t, t) for t in in_name))
            if in_category:
                why.append("category: " + ", ".join(originals.get(t, t) for t in in_category))
            others = [originals.get(t, t) for t in matched if t not in in_name and t not in in_category]
            if others:
                why.append("text: " + ", ".join(others))
            results.append((skill, round(score, 3), [originals.get(t, t) for t in matched], " · ".join(why)))
        results.sort(key=lambda item: (-item[1], item[0].order, item[0].name))
        return results

    def related(self, name: str, limit: int) -> list[tuple[Skill, float]]:
        """Skills with the most similar vocabulary (cosine over TF-IDF)."""
        if self._vectors is None:
            self._vectors = [self._vector(i) for i in range(len(self.skills))]
        vectors = self._vectors
        target = next(i for i, skill in enumerate(self.skills) if skill.name == name)
        scores = []
        for index, vector in enumerate(vectors):
            if index == target:
                continue
            similarity = sum(weight * vectors[target].get(word, 0.0) for word, weight in vector.items())
            if self.skills[index].category == self.skills[target].category:
                similarity += 0.05
            scores.append((self.skills[index], round(similarity, 3)))
        scores.sort(key=lambda item: (-item[1], item[0].name))
        return scores[:limit]

    def _vector(self, index: int) -> dict[str, float]:
        vector = {w: (1 + math.log(c)) * self.idf[w] for w, c in self.counts[index].items()}
        length = math.sqrt(sum(v * v for v in vector.values())) or 1.0
        return {w: v / length for w, v in vector.items()}
