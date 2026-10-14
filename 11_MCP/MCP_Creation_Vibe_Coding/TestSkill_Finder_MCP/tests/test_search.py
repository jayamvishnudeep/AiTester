"""Keyword search: the queries people actually type find the skill they mean."""

import pytest

from test_skill_finder_mcp.search import SearchIndex, words


@pytest.fixture(scope="module")
def index(catalog) -> SearchIndex:
    return catalog.search_index


def top(index, query, n=1):
    return [skill.name for skill, *_ in index.search(query)[:n]]


@pytest.mark.parametrize("query, expected", [
    # the examples from the brief
    ("playwright api", "pw-api-tester"),
    ("playwright API", "pw-api-tester"),
    ("test case creator", "test-case-writer"),
    ("test plan creator", "test-plan-generator"),
    ("test strategy", "test-strategy-designer"),
    ("bug strategy", "test-strategy-designer"),
    # STLC
    ("requirements", "requirement-testability-reviewer"),
    ("acceptance criteria", "acceptance-criteria-writer"),
    ("test estimation", "test-estimation-calculator"),
    ("boundary value", "boundary-value-designer"),
    ("bdd", "bdd-scenario-writer"),
    ("exploratory testing", "exploratory-charter-writer"),
    ("test data", "test-data-generator"),
    ("traceability", "traceability-matrix-builder"),
    ("regression", "regression-suite-selector"),
    ("bug report", "bug-reporter"),
    ("bug triage", "bug-triage-assistant"),
    ("root cause", "rca-analyzer"),
    ("release readiness", "release-readiness-assessor"),
    ("test closure report", "test-closure-reporter"),
    ("write test cases for the login page", "test-case-writer"),
    # frameworks
    ("selenium wait", "se-wait-fixer"),
    ("selenium grid", "se-grid-configurator"),
    ("cypress intercept", "cy-intercept-mocker"),
    ("cypress component", "cy-component-tester"),
    ("visual regression", "pw-visual-regression"),
    ("contract testing", "api-contract-tester"),
    ("graphql", "graphql-api-tester"),
    ("postman", "postman-collection-builder"),
    ("appium", "appium-test-generator"),
    # domains
    ("jmeter", "jmeter-test-plan-builder"),
    ("gatling", "gatling-simulation-writer"),
    ("lighthouse", "web-performance-auditor"),
    ("owasp", "owasp-web-security-tester"),
    ("zap", "zap-security-scanner"),
    ("secrets", "secrets-leak-detector"),
    ("prompt injection", "prompt-injection-tester"),
    ("hallucination", "hallucination-checker"),
    ("rag", "rag-quality-evaluator"),
    ("llm as a judge", "llm-judge-designer"),
    ("agent tool calling", "tool-call-tester"),
    ("mcp security", "mcp-security-reviewer"),
    ("mcp inspector", "mcp-inspector-debugger"),
    ("chaos", "chaos-experiment-designer"),
])
def test_the_best_match_comes_first(index, query, expected):
    assert top(index, query) == [expected]


@pytest.mark.parametrize("query, category", [
    ("playwright", "Playwright pack"), ("pw", "Playwright pack"), ("selenium", "Selenium pack"),
    ("cypress", "Cypress pack"), ("llm evaluation", "LLM evaluation pack"), ("mcp", "MCP pack"),
    ("load test", "Performance pack"), ("pen test", "Security pack"),
])
def test_a_framework_or_domain_word_finds_its_pack(index, query, category):
    first_three = [skill.category for skill, *_ in index.search(query)[:3]]
    assert first_three[0] == category and first_three.count(category) >= 2, first_three


def test_flaky_finds_the_debugger_of_every_framework(index):
    assert set(top(index, "flaky", 3)) == {"pw-flaky-debugger", "se-flaky-debugger", "cy-flaky-debugger"}


def test_words_understand_qa_shorthand():
    assert words("PW bugs creator") == ["playwright", "defect", "creat"]
    assert words("test generator") == words("tests writer") == ["test", "creat"]
    assert words("the skill to find") == []


def test_results_say_what_matched_and_why(index):
    skill, score, matched, why = index.search("playwright api")[0]
    assert matched == ["playwright", "api"]
    assert why.startswith("name: playwright, api")
    assert score > index.search("playwright api")[1][1]


def test_every_skill_comes_first_for_its_own_name_and_title(index, catalog):
    for skill in catalog.skills:
        for query in (skill.name, skill.name.replace("-", " "), skill.title):
            assert top(index, query) == [skill.name], query


def test_nothing_matches_nonsense(index):
    assert index.search("xyzzy") == []
    assert index.search("the and of") == []


def test_misspelt_words_get_corrected(index):
    assert index.correct("playwrite api") == "playwright api"
    assert index.correct("selenum wait") == "selenium wait"
    assert index.correct("playwright api") is None  # nothing to fix
    assert index.correct("pw bug") is None  # shorthand is not a typo


def test_a_filter_limits_the_results(index):
    hits = index.search("flaky", lambda skill: skill.pack == "cypress")
    assert [skill.name for skill, *_ in hits] == ["cy-flaky-debugger"]


def test_related_skills_share_vocabulary(index):
    related = index.related("pw-flaky-debugger", 5)
    names = [skill.name for skill, _ in related]
    assert "pw-flaky-debugger" not in names
    assert {"se-flaky-debugger", "cy-flaky-debugger"} <= set(names)
    scores = [score for _, score in related]
    assert scores == sorted(scores, reverse=True) and all(0 < s <= 1.05 for s in scores)


def test_related_skills_prefer_the_same_category(index):
    names = {skill.name for skill, _ in index.related("bug-reporter", 5)}
    assert {"bug-triage-assistant", "rca-analyzer"} <= names  # the rest of Defect Management
