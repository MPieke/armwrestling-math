import re
import unittest

from tools.callgraph import analyze, build, render
from tools.callgraph.tests import helpers


def fixture_graph():
    return build.build_graph(helpers.raw_nodes_csv(), helpers.raw_edges_csv(), helpers.SHA)


def multi_package_graph():
    """alpha.A -> beta.B (twice, two call sites), beta.B -> beta.C (same package)."""
    nodes = [
        ["x/alpha.A", "A", "x/alpha", "a/a.go", 1, 10],
        ["x/beta.B", "B", "x/beta", "b/b.go", 1, 10],
        ["x/beta.C", "C", "x/beta", "b/b.go", 12, 20],
    ]
    edges = [
        ["x/alpha.A", "x/beta.B", "a/a.go", 3],
        ["x/alpha.A", "x/beta.B", "a/a.go", 4],
        ["x/beta.B", "x/beta.C", "b/b.go", 5],
    ]
    return build.build_graph(helpers.raw_nodes_csv(nodes), helpers.raw_edges_csv(edges), helpers.SHA)


class DotTest(unittest.TestCase):
    def test_every_node_links_to_its_exact_source_lines_at_the_commit(self):
        dot = render.to_dot(fixture_graph(), helpers.REPO_URL)

        for name, start, end in helpers.FIXTURE_FUNCTIONS:
            expected = (
                f"{helpers.REPO_URL}/blob/{helpers.SHA}/{helpers.FIXTURE_FILE}#L{start}-L{end}"
            )
            self.assertRegex(dot, rf'"{re.escape(helpers.node_id(name))}" \[[^\]]*URL="{re.escape(expected)}"')

    def test_every_edge_links_to_its_call_site_line(self):
        dot = render.to_dot(fixture_graph(), helpers.REPO_URL)

        for caller, callee, line in helpers.FIXTURE_CALLS:
            expected = f"{helpers.REPO_URL}/blob/{helpers.SHA}/{helpers.FIXTURE_FILE}#L{line}"
            pattern = (
                rf'"{re.escape(helpers.node_id(caller))}" -> "{re.escape(helpers.node_id(callee))}"'
                rf' \[[^\]]*URL="{re.escape(expected)}"'
            )
            self.assertRegex(dot, pattern)

    def test_edge_count_in_dot_equals_call_sites(self):
        dot = render.to_dot(fixture_graph(), helpers.REPO_URL)

        self.assertEqual(dot.count(" -> "), len(helpers.FIXTURE_CALLS))

    def test_quotes_in_names_are_escaped(self):
        nodes = [['x.a"b', 'a"b', "x", "f.go", 1, 2]]
        graph = build.build_graph(helpers.raw_nodes_csv(nodes), helpers.raw_edges_csv([]), helpers.SHA)

        dot = render.to_dot(graph, helpers.REPO_URL)

        self.assertIn('x.a\\"b', dot)


class PackageLabelTest(unittest.TestCase):
    def labels(self, graph):
        packages = sorted({node.package for node in graph.nodes})
        mapping = render._package_labels(packages)
        return [mapping[package] for package in packages]

    def test_common_module_prefix_is_stripped_from_package_labels(self):
        nodes = [
            ["m.a", "A", "github.com/o/r/svc/cmd/tool", "a.go", 1, 2],
            ["m.b", "B", "github.com/o/r/svc/internal/store", "b.go", 1, 2],
        ]
        graph = build.build_graph(helpers.raw_nodes_csv(nodes), helpers.raw_edges_csv([]), helpers.SHA)

        self.assertEqual(self.labels(graph), ["cmd/tool", "internal/store"])

    def test_single_package_keeps_its_last_path_segment(self):
        self.assertEqual(self.labels(fixture_graph()), ["fixture"])

    def test_label_prefix_is_cut_on_path_boundaries_only(self):
        nodes = [
            ["m.a", "A", "x/storeA", "a.go", 1, 2],
            ["m.b", "B", "x/storeB", "b.go", 1, 2],
        ]
        graph = build.build_graph(helpers.raw_nodes_csv(nodes), helpers.raw_edges_csv([]), helpers.SHA)

        self.assertEqual(self.labels(graph), ["storeA", "storeB"])


class SummaryTest(unittest.TestCase):
    def test_summary_reports_node_and_edge_counts(self):
        summary = render.summary_markdown(fixture_graph(), helpers.REPO_URL)

        self.assertIn("4 functions", summary)
        self.assertIn("5 call sites", summary)

    def test_summary_ranks_most_called_function_first_with_source_link(self):
        summary = render.summary_markdown(fixture_graph(), helpers.REPO_URL)
        fan_in = summary.split("Most called")[1]
        first_row = [line for line in fan_in.splitlines() if line.startswith("| [")][0]

        # leaf is called from run and helper (2); helper from main and run (2); tie -> by name
        self.assertIn("helper", first_row)
        self.assertIn(f"{helpers.REPO_URL}/blob/{helpers.SHA}/{helpers.FIXTURE_FILE}#L13-L15", first_row)

    def test_the_summary_has_no_diagram_of_its_own_only_cards_have_diagrams(self):
        summary = render.summary_markdown(fixture_graph(), helpers.REPO_URL)

        self.assertNotIn("```mermaid", summary)
        self.assertNotIn("Packages (cross-package call sites)", summary)


class SummaryDetailsTest(unittest.TestCase):
    """Everything a reviewer needs should be readable on the run page, not only in artifacts."""

    def summary(self, graph=None, **options):
        return render.summary_markdown(graph or fixture_graph(), helpers.REPO_URL, **options)

    def test_package_totals_count_functions_and_cross_package_call_sites(self):
        section = self.summary(multi_package_graph()).split("Package totals")[1]

        self.assertIn("| alpha | 1 | 2 | 0 |", section)
        self.assertIn("| beta | 2 | 0 | 2 |", section)

    def test_most_calls_out_ranks_busiest_caller_first_with_source_link(self):
        section = self.summary().split("Most calls out")[1]
        first_row = [line for line in section.splitlines() if line.startswith("| [")][0]

        # main and run both make 2 call sites; ties break by name.
        self.assertIn("[main]", first_row)
        self.assertIn(f"blob/{helpers.SHA}/{helpers.FIXTURE_FILE}#L3-L6", first_row)

    def test_never_called_lists_only_functions_without_callers(self):
        section = self.summary().split("Never called")[1].split("###")[0].split("<details>")[0]
        listed = re.findall(r"^\| \[(\w+)\]", section, flags=re.M)

        self.assertEqual(listed, ["main"])

    def test_every_call_site_is_listed_with_a_link_to_its_line(self):
        summary = self.summary()

        self.assertIn("All call sites (5)", summary)
        for _caller, _callee, line in helpers.FIXTURE_CALLS:
            self.assertIn(f"blob/{helpers.SHA}/{helpers.FIXTURE_FILE}#L{line})", summary)

    def test_every_function_is_listed_in_a_collapsible_section(self):
        summary = self.summary()

        self.assertIn("<details><summary>All functions (4)</summary>", summary)
        self.assertEqual(summary.count("<details"), summary.count("</details>"))  # all closed

    def test_long_listings_are_truncated_with_a_count(self):
        summary = self.summary(max_listed_rows=2)

        self.assertIn("showing first 2 of 5", summary)
        self.assertIn("showing first 2 of 4", summary)


class SummaryCardsTest(unittest.TestCase):
    INDEPENDENT = [("e1", "a"), ("a", "t"), ("e2", "b"), ("b", "t")]

    def summary(self, edges, entries, externals=(("t", "os.Open"),), judgements=None,
                ignored=(), **kw):
        graph = helpers.make_graph(edges, entries=entries, externals=list(externals))
        analysis = analyze.analyze(graph, ignored_packages=ignored)
        return render.summary_markdown(
            graph, helpers.REPO_URL, analysis=analysis, judgements=judgements,
            ignored_packages=ignored, **kw,
        )

    def section(self, text):
        return text.split("<b>Redundant routes</b>")[1].split("<b>Dead-code")[0]

    def test_the_card_says_in_plain_words_which_functions_reach_which_targets(self):
        text = self.section(self.summary(self.INDEPENDENT, ["e1", "e2"]))

        self.assertIn("`p.a` and `p.b` each reach `p.t` on separate routes", text)

    def test_a_global_card_says_the_routes_share_nothing_on_the_way_in(self):
        text = self.section(self.summary(self.INDEPENDENT, ["e1", "e2"]))

        self.assertIn("the routes share no function on the way in", text)

    def test_a_nested_card_says_where_the_routes_diverge_instead(self):
        edges = [
            ("e1", "run"), ("run", "x"), ("run", "y"), ("x", "t"), ("y", "t"),
            ("e2", "z"), ("z", "t"),
        ]

        text = self.section(self.summary(edges, ["e1", "e2"]))
        card = [c for c in text.split("#### ") if c.startswith("1.") or "`x` and `y`" in c.splitlines()[0]]
        nested = [c for c in text.split("#### ")[1:] if c.splitlines()[0].endswith("`x` and `y`")][0]

        self.assertIn("below `p.run`, the routes share no function", nested)
        self.assertNotIn("on the way in", nested)
        self.assertTrue(card)

    def test_each_function_says_which_entry_points_reach_it(self):
        text = self.section(self.summary(self.INDEPENDENT, ["e1", "e2"]))

        self.assertIn("`p.a` is reached from `p.e1`", text)
        self.assertIn("`p.b` is reached from `p.e2`", text)

    def test_shared_calls_are_listed_as_evidence(self):
        edges = self.INDEPENDENT + [("a", "h"), ("b", "h")]
        externals = (("t", "os.Open"), ("a", "encoding/json.Marshal"), ("b", "encoding/json.Marshal"))

        text = self.section(self.summary(edges, ["e1", "e2"], externals))

        self.assertIn("Both also call: `p.h`", text)
        self.assertIn("`json.Marshal`", text)

    def test_pairs_with_nothing_in_common_say_so(self):
        text = self.section(self.summary(self.INDEPENDENT, ["e1", "e2"]))

        self.assertIn("They share no calls apart from the targets", text)

    def test_calls_made_by_only_one_function_are_listed_per_function(self):
        edges = self.INDEPENDENT + [("a", "only_a"), ("b", "only_b")]

        text = self.section(self.summary(edges, ["e1", "e2"]))

        self.assertIn("Only `p.a` calls: `p.only_a`", text)
        self.assertIn("Only `p.b` calls: `p.only_b`", text)

    def test_the_similarity_band_and_percentage_are_stated(self):
        edges = self.INDEPENDENT + [("a", "h"), ("b", "h")]

        text = self.section(self.summary(edges, ["e1", "e2"]))

        self.assertIn("very similar (100% of their calls in common)", text)

    def test_external_variants_with_one_name_are_collapsed(self):
        externals = [("t", "os.Open")] + [
            (caller, name)
            for caller in ("a", "b")
            for name in ("io.Closer.Close", "io.ReadCloser.Close", "net/http.File.Close")
        ]

        text = self.section(self.summary(self.INDEPENDENT, ["e1", "e2"], externals))

        self.assertIn("`Close` (3 variants)", text)

    def test_every_card_has_its_own_diagram_and_the_summary_has_none_besides(self):
        text = self.summary(self.INDEPENDENT, ["e1", "e2"])

        self.assertEqual(text.count("```mermaid"), 1)

    def test_the_diagram_marks_gateways_and_targets_and_draws_every_hop(self):
        text = self.summary(self.INDEPENDENT, ["e1", "e2"])
        diagram = text.split("```mermaid")[1].split("```")[0]

        for hop in ("e1", "a"), ("a", "t"), ("e2", "b"), ("b", "t"):
            self.assertRegex(diagram, rf'n\d+\["p\.{hop[0]}"\][\s\S]*-->')
        self.assertEqual(diagram.count("class "), 3)  # one class assignment per role
        self.assertIn("classDef gateway", diagram)
        self.assertIn("classDef target", diagram)
        self.assertIn("classDef entry", diagram)

    def test_long_chains_are_collapsed_and_the_diagram_stays_under_the_node_cap(self):
        chain = [("e1", "c1")] + [(f"c{i}", f"c{i + 1}") for i in range(1, 8)] + [("c8", "a"), ("a", "t")]
        edges = chain + [("e2", "b"), ("b", "t")]

        text = self.summary(edges, ["e1", "e2"])
        diagram = text.split("```mermaid")[1].split("```")[0]

        self.assertIn("functions", diagram)
        self.assertLessEqual(len(set(re.findall(r"\bn\d+\[", diagram))), render.DIAGRAM_NODE_CAP)

    def test_routes_sharing_an_entry_and_gateway_share_one_collapsed_node(self):
        # Two targets reached through the same long chains must not repeat the chain node.
        chain1 = [("e1", "c1"), ("c1", "c2"), ("c2", "c3"), ("c3", "a")]
        chain2 = [("e2", "d1"), ("d1", "d2"), ("d2", "d3"), ("d3", "b")]
        edges = chain1 + chain2 + [("a", "t1"), ("a", "t2"), ("b", "t1"), ("b", "t2")]
        externals = (("t1", "os.Open"), ("t2", "os.Create"))

        text = self.summary(edges, ["e1", "e2"], externals)
        diagram = text.split("```mermaid")[1].split("```")[0]

        self.assertEqual(diagram.count("... 3 functions"), 2)

    def test_the_card_title_uses_short_names_without_the_package_path(self):
        graph = helpers.make_graph(
            self.INDEPENDENT, entries=["e1", "e2"], externals=[("t", "os.Open")],
            packages={"a": "example.com/m/internal/one", "b": "example.com/m/internal/two"},
        )
        renamed = {"a": "example.com/m/internal/one.a", "b": "example.com/m/internal/two.b"}
        nodes = tuple(
            build.Node(**{**n.__dict__, "id": renamed.get(n.id, n.id)}) for n in graph.nodes
        )
        edges = tuple(
            build.Edge(**{**e.__dict__,
                          "caller_id": renamed.get(e.caller_id, e.caller_id),
                          "callee_id": renamed.get(e.callee_id, e.callee_id)})
            for e in graph.edges
        )
        graph = build.Graph(nodes, edges, graph.externals)

        text = render.summary_markdown(graph, helpers.REPO_URL, analysis=analyze.analyze(graph))

        self.assertIn("#### 1. `a` and `b`", text)

    def test_node_labels_with_quotes_are_escaped_in_the_diagram(self):
        graph = helpers.make_graph(self.INDEPENDENT, entries=["e1", "e2"], externals=[("t", "os.Open")])
        nodes = tuple(
            build.Node(**{**n.__dict__, "name": 'a"b', "id": 'a"b'}) if n.id == "a" else n
            for n in graph.nodes
        )
        edges = tuple(
            build.Edge(**{**e.__dict__, "caller_id": 'a"b' if e.caller_id == "a" else e.caller_id,
                          "callee_id": 'a"b' if e.callee_id == "a" else e.callee_id})
            for e in graph.edges
        )
        graph = build.Graph(nodes, edges, graph.externals)

        text = render.summary_markdown(graph, helpers.REPO_URL, analysis=analyze.analyze(graph))

        self.assertNotIn('"p.a"b"', text)

    def test_routes_and_entry_points_are_collapsed_under_the_card(self):
        text = self.section(self.summary(self.INDEPENDENT, ["e1", "e2"]))

        self.assertIn("<details><summary>Routes and entry points</summary>", text)
        self.assertIn("p.e1 > p.a > p.t", text)
        self.assertIn("p.e2 > p.b > p.t", text)

    def test_cards_are_capped_with_a_count(self):
        edges = self.INDEPENDENT + [("e3", "c"), ("c", "u"), ("e4", "d"), ("d", "u")]
        externals = (("t", "os.Open"), ("u", "os.Create"))

        text = self.summary(edges, ["e1", "e2", "e3", "e4"], externals, max_findings=1)

        self.assertIn("showing first 1 of 2 cards", text)

    def test_no_cards_says_so(self):
        text = self.summary([("e", "a"), ("a", "t")], ["e"])

        self.assertIn("No redundant routes found", text)

    def test_an_unavailable_judge_shows_the_reason(self):
        judgements = {"calibration": None, "judgements": [{
            "first": "a", "second": "b", "status": "unavailable", "reason": "HTTP 404: model not found",
        }]}

        text = self.section(self.summary(self.INDEPENDENT, ["e1", "e2"], judgements=judgements))

        self.assertIn("LLM verdict: unavailable (HTTP 404: model not found)", text)

    def test_calibration_agreement_is_shown_and_a_low_score_warns(self):
        good = {"judgements": [], "calibration": {"agree": 3, "total": 3, "cases": []}}
        bad = {"judgements": [], "calibration": {"agree": 1, "total": 3, "cases": []}}

        self.assertIn("LLM calibration: 3 of 3", self.summary(self.INDEPENDENT, ["e1", "e2"], judgements=good))
        warned = self.summary(self.INDEPENDENT, ["e1", "e2"], judgements=bad)
        self.assertIn("LLM calibration: 1 of 3", warned)
        self.assertIn("unreliable", warned)

    def test_a_skipped_judge_says_why_once_at_the_top_of_the_section(self):
        judgements = {"status": "skipped", "reason": "OPENAI_API_KEY is not set",
                      "judgements": [], "calibration": None}

        text = self.section(self.summary(self.INDEPENDENT, ["e1", "e2"], judgements=judgements))

        self.assertEqual(text.count("LLM judge skipped (OPENAI_API_KEY is not set)"), 1)

    def test_a_judge_that_failed_everywhere_says_so_once_at_the_top(self):
        judgements = {"status": "unavailable", "reason": "HTTP 404: model not found",
                      "calibration": None, "judgements": [{
                          "first": "a", "second": "b", "status": "unavailable",
                          "reason": "HTTP 404: model not found"}]}

        text = self.section(self.summary(self.INDEPENDENT, ["e1", "e2"], judgements=judgements))

        self.assertIn("LLM judge unavailable (HTTP 404: model not found)", text)

    def test_a_working_judge_shows_no_status_line(self):
        judgements = {"status": "ok", "reason": "", "judgements": [], "calibration": None}

        text = self.section(self.summary(self.INDEPENDENT, ["e1", "e2"], judgements=judgements))

        self.assertNotIn("LLM judge", text)

    def test_no_judgements_means_no_llm_text(self):
        text = self.summary(self.INDEPENDENT, ["e1", "e2"])

        self.assertNotIn("LLM", text)


STEPS = [
    {"name": "build prompt", "a": [3, 5], "b": [3, 4], "same": False},
    {"name": "build request", "a": [6, 10], "b": [5, 9], "same": True},
    {"name": "send", "a": [11, 15], "b": [10, 14], "same": True},
    {"name": "decode", "a": [16, 18], "b": [15, 17], "same": False},
]


def judged(first="a", second="b", **overrides):
    verdict = {
        "first": first, "second": second, "status": "ok", "kind": "pair",
        "verdict": "duplicate", "confidence": "high", "action": "extract_shared",
        "headline": "a and b each build, send and decode their own request.",
        "explanation": "They repeat the same pipeline.",
        "steps": STEPS,
        "issues": [{"step": "build request", "function": "both", "note": "repeated in both"}],
        "fix": {"summary": "Share one request function.", "shared_name": "chatCompletion",
                "moved_steps": ["build request", "send"], "stays_in_a": ["build prompt"],
                "stays_in_b": ["build prompt"]},
        "maybe_intentional": {"reason": "they serve different commands",
                              "would_matter_if": "the commands diverge"},
        "essential_differences": ["different prompts"], "accidental_differences": ["names"],
        "risks": ["error messages differ"], "evidence": [],
        "citations_valid": 3, "citations_invalid": 1, "steps_invalid": 0,
        "issues_dropped": 0, "fix_unknown_steps": 0,
    }
    verdict.update(overrides)
    return verdict


class SummaryStoryTest(unittest.TestCase):
    INDEPENDENT = [("e1", "a"), ("a", "t"), ("e2", "b"), ("b", "t")]

    def summary(self, verdicts, edges=None, entries=("e1", "e2"), externals=(("t", "os.Open"),),
                calibration=None, **kw):
        graph = helpers.make_graph(edges or self.INDEPENDENT, entries=list(entries),
                                   externals=list(externals))
        analysis = analyze.analyze(graph)
        judgements = {"status": "ok", "reason": "", "judgements": verdicts, "calibration": calibration}
        return render.summary_markdown(graph, helpers.REPO_URL, analysis=analysis,
                                       judgements=judgements, **kw)

    def section(self, text):
        return text.split("<b>Redundant routes</b>")[1].split("<b>Dead-code")[0]

    def card(self, text, number=1):
        return self.section(text).split("#### ")[number]

    def test_the_problem_comes_first_then_the_picture_then_the_fix(self):
        card = self.card(self.summary([judged()]))

        problem = card.index("a and b each build, send and decode")
        picture = card.index("```mermaid")
        fix = card.index("Fix:")
        after = card.index("```mermaid", picture + 10)
        maybe = card.index("Maybe intentional because:")
        details = card.index("<details>")
        self.assertTrue(problem < picture < fix < after < maybe < details)

    def test_the_advisory_verdict_is_one_line_with_the_recommended_action(self):
        card = self.card(self.summary([judged()]))

        self.assertIn("Advisory verdict: extract the shared part (duplicate, high confidence)", card)

    def test_the_first_diagram_shows_each_functions_steps_with_the_issue_marker_and_legend(self):
        card = self.card(self.summary([judged()]))
        diagram = card.split("```mermaid")[1].split("```")[0]

        self.assertIn("build request (1)", diagram)
        self.assertIn("-. same .-", diagram)
        self.assertIn("(1) repeated in both", card.split("```mermaid")[1].split("```")[1])

    def test_the_second_diagram_shows_the_shared_function_and_the_fix_text(self):
        card = self.card(self.summary([judged()]))
        after = card.split("```mermaid")[2].split("```")[0]

        self.assertIn("chatCompletion", after)
        self.assertIn("classDef new", after)
        self.assertIn("Fix: Share one request function.", card)
        self.assertIn("Stays in each function: build prompt", card)

    def first_diagram(self, card):
        return card.split("```mermaid")[1].split("```")[0]

    def second_diagram(self, card):
        return card.split("```mermaid")[2].split("```")[0]

    def test_boxes_show_the_code_names_and_line_range_when_the_source_is_available(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as root:
            for name in ("a.go", "b.go"):
                (Path(root) / name).write_text("\n".join(f"\tfoo{i}()" for i in range(1, 30)))
            card = self.card(self.summary([judged()], source_root=root))

        diagram = self.first_diagram(card)
        self.assertIn("build request (1)<br/>foo6, foo7, foo8 · L6-10", diagram)  # function a
        self.assertIn("build request (1)<br/>foo5, foo6, foo7 · L5-9", diagram)   # function b

    def test_without_source_boxes_show_only_the_line_range(self):
        diagram = self.first_diagram(self.card(self.summary([judged()])))

        self.assertIn("build request (1)<br/>L6-10", diagram)

    def test_red_marks_every_step_the_fix_moves_not_only_the_ones_the_model_noted(self):
        diagram = self.first_diagram(self.card(self.summary([judged()])))

        members = re.search(r"class ((?:n\d+,?)+) problem", diagram).group(1).split(",")
        self.assertEqual(len(members), 4)  # build request and send, in both functions

    def test_the_after_diagram_has_no_red_and_the_shared_node_is_orange_and_dashed(self):
        diagram = self.second_diagram(self.card(self.summary([judged()])))

        self.assertNotIn("problem", diagram)
        self.assertEqual(len(re.findall(r"class (n\d+) same", diagram)), 1)
        self.assertIn("class n", diagram)
        self.assertRegex(diagram, r"class n\d+ new")

    def test_a_colour_key_sits_under_both_diagrams(self):
        card = self.card(self.summary([judged()]))

        after_first = card.split("```mermaid")[1].split("```")[1]
        after_second = card.split("```mermaid")[2].split("```")[1]
        self.assertIn("orange = the same step in both functions", after_first)
        self.assertIn("red outline = part of the problem", after_first)
        self.assertIn("same colours as above", after_second)
        self.assertIn("dashed = the new shared function", after_second)

    def test_the_maybe_intentional_reason_is_visible_not_in_a_dropdown(self):
        card = self.card(self.summary([judged()]))

        visible = card.split("<details>")[0]
        self.assertIn("Maybe intentional because: they serve different commands", visible)
        self.assertIn("It would matter if the commands diverge", visible)

    def test_the_maybe_intentional_line_does_not_repeat_the_words_or_punctuation_the_model_used(self):
        verdict = judged(maybe_intentional={
            "reason": "They serve different workflows.",
            "would_matter_if": "It would matter if the helper coupled their prompts.",
        })

        card = self.card(self.summary([verdict]))

        self.assertIn(
            "Maybe intentional because: They serve different workflows. "
            "It would matter if the helper coupled their prompts.", card,
        )
        self.assertNotIn("..", card.split("<details>")[0])
        self.assertNotIn("if It would", card)

    def test_a_would_matter_if_without_the_prefix_gets_one(self):
        verdict = judged(maybe_intentional={"reason": "different commands", "would_matter_if": "they diverge"})

        card = self.card(self.summary([verdict]))

        self.assertIn("Maybe intentional because: different commands. It would matter if they diverge.", card)

    def test_a_leading_common_word_after_it_would_matter_if_is_lower_cased_but_names_are_not(self):
        common = judged(maybe_intentional={"reason": "r", "would_matter_if": "The commands diverge."})
        name = judged(maybe_intentional={"reason": "r", "would_matter_if": "OpenAI changes the schema."})

        self.assertIn("It would matter if the commands diverge.", self.card(self.summary([common])))
        self.assertIn("It would matter if OpenAI changes the schema.", self.card(self.summary([name])))

    def test_what_stays_is_every_step_that_is_not_moved_whatever_the_model_listed(self):
        fix = {"summary": "Share it.", "shared_name": "shared", "moved_steps": ["build request", "send"],
               "stays_in_a": [], "stays_in_b": []}

        card = self.card(self.summary([judged(fix=fix)]))

        self.assertIn("Stays in each function: build prompt, decode", card)

    def test_when_the_two_functions_keep_different_steps_each_is_listed_separately(self):
        steps = STEPS + [{"name": "validate", "a": [19, 20], "b": None, "same": False}]
        fix = {"summary": "Share it.", "shared_name": "shared", "moved_steps": ["build request", "send"],
               "stays_in_a": [], "stays_in_b": []}

        card = self.card(self.summary([judged(steps=steps, fix=fix, issues=[])]))

        self.assertIn(
            "Stays in `a`: build prompt, decode, validate; stays in `b`: build prompt, decode", card
        )

    def test_step_names_keep_their_capitals_in_the_stays_line(self):
        steps = [
            {"name": "build OpenAI request", "a": [3, 5], "b": [3, 4], "same": True},
            {"name": "send", "a": [6, 8], "b": [5, 7], "same": True},
            {"name": "decode OpenAI reply", "a": [9, 10], "b": None, "same": False},
        ]
        fix = {"summary": "Share it.", "shared_name": "shared", "moved_steps": ["send"],
               "stays_in_a": [], "stays_in_b": []}

        card = self.card(self.summary([judged(steps=steps, fix=fix, issues=[])]))

        self.assertIn("Stays in `a`: build OpenAI request, decode OpenAI reply", card)

    def test_calls_and_overlap_are_behind_a_dropdown_not_on_the_surface(self):
        edges = self.INDEPENDENT + [("a", "h"), ("b", "h")]
        card = self.card(self.summary([judged()], edges=edges))

        visible = card.split("<details>")[0]
        self.assertNotIn("Call overlap", visible)
        self.assertNotIn("Both also call", visible)
        evidence = card.split("<summary>Evidence")[1]
        self.assertIn("Both also call: `p.h`", evidence)
        self.assertIn("Call overlap", evidence)

    def test_the_route_diagram_moves_into_the_routes_dropdown(self):
        card = self.card(self.summary([judged()]))

        routes = card.split("<summary>Routes and entry points</summary>")[1]
        self.assertIn("```mermaid", routes)
        self.assertEqual(card.count("```mermaid"), 3)  # steps, after, routes

    def test_llm_details_list_the_explanation_differences_steps_and_checks(self):
        card = self.card(self.summary([judged()]))

        details = card.split("<summary>LLM details</summary>")[1]
        self.assertIn("They repeat the same pipeline.", details)
        self.assertIn("different prompts", details)
        self.assertIn("error messages differ", details)
        self.assertIn("3 of 4 citations verified", details)
        self.assertIn(f"{helpers.REPO_URL}/blob/{helpers.SHA}/a.go#L6-L10", details)

    def test_cards_the_model_says_to_keep_are_folded_and_the_rest_stay_on_the_surface(self):
        edges = self.INDEPENDENT + [("e3", "c"), ("c", "u"), ("e4", "d"), ("d", "u")]
        verdicts = [judged("a", "b", action="keep", verdict="intentional"), judged("c", "d")]

        text = self.section(self.summary(verdicts, edges=edges, entries=("e1", "e2", "e3", "e4"),
                                         externals=(("t", "os.Open"), ("u", "os.Create"))))

        folded = text.split("<summary>Looked at, probably fine (1)</summary>")
        self.assertEqual(len(folded), 2)
        self.assertIn("`c` and `d`", folded[0])
        self.assertNotIn("`a` and `b`", folded[0])
        self.assertIn("`a` and `b`", folded[1])

    def test_a_keep_card_with_an_unsure_verdict_stays_on_the_surface(self):
        text = self.section(self.summary([judged(action="keep", verdict="unsure")]))

        self.assertNotIn("Looked at, probably fine", text)

    def test_cards_are_ordered_merge_then_extract_then_unsure_then_unjudged(self):
        edges = self.INDEPENDENT + [
            ("e3", "c"), ("c", "u"), ("e4", "d"), ("d", "u"),
            ("e5", "f"), ("f", "w"), ("e6", "g"), ("g", "w"),
        ]
        verdicts = [judged("a", "b", action="extract_shared"), judged("c", "d", action="merge")]

        text = self.section(self.summary(
            verdicts, edges=edges, entries=("e1", "e2", "e3", "e4", "e5", "e6"),
            externals=(("t", "os.Open"), ("u", "os.Create"), ("w", "os.Remove")),
        ))

        titles = [c.splitlines()[0] for c in text.split("#### ")[1:]]
        self.assertEqual([t.split(". ", 1)[1] for t in titles], ["`c` and `d`", "`a` and `b`", "`f` and `g`"])

    def test_a_judged_card_without_enough_steps_falls_back_to_the_route_diagram(self):
        card = self.card(self.summary([judged(steps=[], issues=[], fix={
            "summary": "", "shared_name": "", "moved_steps": [], "stays_in_a": [], "stays_in_b": []})]))

        self.assertIn("a and b each build, send and decode", card)
        diagram = card.split("```mermaid")[1].split("```")[0]
        self.assertIn("p.e1", diagram)  # the route diagram, not a step diagram
        self.assertNotIn("Fix:", card)

    def test_a_two_routes_card_says_one_function_reaches_it_two_ways_and_draws_both(self):
        edges = [
            ("e1", "run"), ("run", "ic"), ("ic", "submit"), ("ic", "af"), ("af", "submit"),
            ("e2", "sr"), ("sr", "ri"), ("submit", "ri"),
        ]
        graph = helpers.make_graph(edges, entries=["e1", "e2"], externals=[("ri", "os.Open")])
        analysis = analyze.analyze(graph)

        text = render.summary_markdown(graph, helpers.REPO_URL, analysis=analysis)
        card = [c for c in text.split("#### ") if "two ways" in c.splitlines()[0]][0]

        self.assertIn("`ic` reaches `submit` two ways", card.splitlines()[0])
        diagram = card.split("```mermaid")[1].split("```")[0]
        self.assertIn("directly", diagram)
        self.assertIn('"af"', diagram)

    def test_a_deliberate_two_routes_card_is_folded_away(self):
        edges = [
            ("e1", "run"), ("run", "ic"), ("ic", "submit"), ("ic", "af"), ("af", "submit"),
            ("e2", "sr"), ("sr", "ri"), ("submit", "ri"),
        ]
        verdict = judged("af", "ic", kind="two_routes", verdict="deliberate", action="keep",
                         steps=[], issues=[], headline="ic reaches submit on success and via af on failure.")
        graph = helpers.make_graph(edges, entries=["e1", "e2"], externals=[("ri", "os.Open")])
        judgements = {"status": "ok", "judgements": [verdict], "calibration": None}

        text = render.summary_markdown(graph, helpers.REPO_URL, analysis=analyze.analyze(graph),
                                       judgements=judgements)

        folded = text.split("<summary>Looked at, probably fine (1)</summary>")[1]
        self.assertIn("two ways", folded)
        self.assertIn("ic reaches submit on success and via af on failure.", folded)

    def test_llm_text_is_escaped_everywhere_it_is_shown(self):
        verdict = judged(
            headline="<script>alert(1)</script> [x](http://evil)",
            issues=[{"step": "build request", "function": "both", "note": "<b>bold</b> \"q\""}],
            maybe_intentional={"reason": "<i>x</i>", "would_matter_if": "[l](u)"},
            fix={"summary": "<u>fix</u>", "shared_name": "n\"q", "moved_steps": ["build request"],
                 "stays_in_a": [], "stays_in_b": []},
        )

        card = self.card(self.summary([verdict]))

        for raw in ("<script>", "<b>", "<i>", "<u>", "[x](http://evil)", "[l](u)"):
            self.assertNotIn(raw, card)
        self.assertIn("&lt;script&gt;", card)
        self.assertNotIn('"n"q"', card)

    def test_an_unavailable_card_still_shows_its_deterministic_content(self):
        verdict = {"first": "a", "second": "b", "status": "unavailable", "reason": "HTTP 500"}

        card = self.card(self.summary([verdict]))

        self.assertIn("LLM verdict: unavailable (HTTP 500)", card)
        self.assertIn("`p.a` and `p.b` each reach `p.t` on separate routes", card)
        self.assertIn("```mermaid", card)


class SummarySectionsTest(unittest.TestCase):
    def text(self):
        graph = helpers.make_graph(
            [("e1", "a"), ("a", "t"), ("e2", "b"), ("b", "t")], entries=["e1", "e2"],
            externals=[("t", "os.Open")],
        )
        return render.summary_markdown(graph, helpers.REPO_URL, analysis=analyze.analyze(graph))

    SECTIONS = {
        "Redundant routes": "pairs of functions that reach the same code separately",
        "Dead-code candidates (0)": "functions no entry point can reach",
        "Package totals": "functions and cross-package calls per package",
        "Most used external functions": "outside functions your code calls most",
        "Most called functions": "functions with the most call sites",
        "Most calls out": "functions that make the most calls",
        "Never called (entry points or unused)": "functions nothing calls",
    }

    def test_every_section_is_a_collapsible_block_with_a_one_line_description(self):
        text = self.text()

        for title, description in self.SECTIONS.items():
            self.assertRegex(text, rf"<details( open)?><summary><b>{re.escape(title)}</b> - {re.escape(description)}")

    def test_only_the_redundant_routes_section_is_open_by_default(self):
        text = self.text()

        self.assertIn("<details open><summary><b>Redundant routes</b>", text)
        self.assertEqual(text.count("<details open>"), 1)
        for title in list(self.SECTIONS)[1:]:
            self.assertIn(f"<details><summary><b>{title}</b>", text)

    def test_every_block_that_is_opened_is_closed(self):
        text = self.text()

        self.assertEqual(text.count("<details"), text.count("</details>"))

    def test_there_are_no_plain_section_headings_left_besides_the_title_and_card_titles(self):
        text = self.text()

        self.assertEqual(re.findall(r"^### .*", text, flags=re.M), [])

    def test_the_package_diagram_is_gone_but_the_package_table_stays(self):
        text = self.text()

        self.assertNotIn("Packages (cross-package call sites)", text)
        self.assertIn("| package | functions | calls out | calls in |", text)


def _source(receiver, label, label_line):
    lines = [f"\tcall({receiver})"] * 30
    lines[label_line - 1] = f'\tlog("{label}")'
    return "\n".join(lines)


# Steps in the shared fixture are build request A[6,10] / B[5,9] and send A[11,15] / B[10,14].
SOURCE_ANNOTATE = _source("annotator", "annotation label", 8)
SOURCE_EXTRACT = _source("extractor", "extraction label", 7)


class SummarySafetyTest(unittest.TestCase):
    """The 'Before you change this' block and its details, on cards with a fix."""

    EDGES = [("e1", "Annotate"), ("Annotate", "t"), ("e2", "Extract"), ("Extract", "t")]

    def graph(self, dynamic=False):
        graph = helpers.make_graph(self.EDGES, entries=["e1", "e2"], externals=[("t", "os.Open")])
        if dynamic:
            edges = tuple(
                build.Edge(**{**e.__dict__, "resolution": "dynamic"}) if e.callee_id == "Annotate" else e
                for e in graph.edges
            )
            graph = build.Graph(graph.nodes, edges, graph.externals)
        return graph

    def card(self, root=None, verdict=None, dynamic=False, tests=True):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "Annotate.go").write_text(SOURCE_ANNOTATE)
            (base / "Extract.go").write_text(SOURCE_EXTRACT)
            if tests:
                (base / "Annotate_test.go").write_text(
                    "package p\n\nfunc TestAnnotateParses(t *testing.T) {\n\tAnnotate()\n}\n\n"
                    "func TestAnnotateRedacts(t *testing.T) {\n\tAnnotate()\n}\n")
                (base / "Extract_test.go").write_text(
                    "package p\n\nfunc TestExtractParses(t *testing.T) {\n\tExtract()\n}\n")
            graph = self.graph(dynamic)
            judgements = {"status": "ok", "judgements": [verdict or judged("Annotate", "Extract")],
                          "calibration": None}
            text = render.summary_markdown(
                graph, helpers.REPO_URL, analysis=analyze.analyze(graph), judgements=judgements,
                source_root=None if root is False else directory,
            )
        return text.split("<b>Redundant routes</b>")[1].split("<b>Dead-code")[0].split("#### ")[1]

    def test_the_block_sits_after_the_fix_and_before_the_maybe_intentional_line(self):
        card = self.card()

        block = card.index("Before you change this")
        self.assertTrue(card.index("Fix:") < block < card.index("Maybe intentional because:"))

    def test_the_blast_radius_names_the_callers_of_each_function(self):
        card = self.card()

        self.assertIn("`Annotate` is called from `e1`", card)
        self.assertIn("`Extract` is called from `e2`", card)

    def test_a_call_through_an_interface_says_so(self):
        card = self.card(dynamic=True)

        self.assertIn("`Annotate` is called from `e1` (through an interface)", card)

    def test_a_behaviour_tested_for_one_function_only_is_named_as_a_gap(self):
        card = self.card()

        visible = card.split("<details>")[0]
        self.assertIn("`Annotate` has 2 tests, `Extract` has 1", visible)
        self.assertIn("`Extract` has no counterpart by name for: `Redacts`", visible)

    def test_test_names_that_are_not_parallel_say_gaps_cannot_be_told_by_name(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "Annotate.go").write_text(SOURCE_ANNOTATE)
            (base / "Extract.go").write_text(SOURCE_EXTRACT)
            (base / "Annotate_test.go").write_text(
                "package p\n\nfunc TestAnnotateParses(t *testing.T) {\n\tAnnotate()\n}\n")
            (base / "Extract_test.go").write_text(
                "package p\n\nfunc TestExtractSendsAudio(t *testing.T) {\n\tExtract()\n}\n")
            graph = self.graph()
            judgements = {"status": "ok", "judgements": [judged("Annotate", "Extract")], "calibration": None}
            text = render.summary_markdown(graph, helpers.REPO_URL, analysis=analyze.analyze(graph),
                                           judgements=judgements, source_root=directory)

        card = text.split("<b>Redundant routes</b>")[1].split("<b>Dead-code")[0].split("#### ")[1]
        visible = card.split("<details>")[0]
        self.assertNotIn("no counterpart by name", visible)
        self.assertIn("names are not parallel", visible)
        self.assertIn("`Annotate` has 1 test, `Extract` has 1 test", visible)

    def test_a_function_without_tests_says_to_add_tests_first(self):
        card = self.card(tests=False)

        self.assertIn("none found for either function", card.split("<details>")[0])

    def test_without_source_access_tests_are_not_checked_but_callers_still_are(self):
        card = self.card(root=False)

        visible = card.split("<details>")[0]
        self.assertIn("not checked (no source access)", visible)
        self.assertIn("`Annotate` is called from `e1`", visible)

    def test_the_details_dropdown_lists_what_differs_inside_the_same_steps(self):
        card = self.card()

        details = card.split("<summary>Safety check details</summary>")[1].split("</details>")[0]
        self.assertIn("`annotator` -> `extractor`", details)
        self.assertIn('"annotation label"', details)
        self.assertIn("a shared function must take these", details)

    def test_the_details_dropdown_links_callers_and_tests_to_their_lines(self):
        card = self.card()

        details = card.split("<summary>Safety check details</summary>")[1].split("</details>")[0]
        self.assertIn(f"{helpers.REPO_URL}/blob/{helpers.SHA}/e1.go#L5", details)
        self.assertIn("TestAnnotateRedacts", details)

    def test_the_details_dropdown_comes_first_among_the_dropdowns(self):
        card = self.card()

        self.assertLess(card.index("<summary>Safety check details"), card.index("<summary>Evidence"))

    def test_cards_the_model_says_to_keep_get_no_safety_block(self):
        verdict = judged("Annotate", "Extract", action="keep", verdict="intentional")

        import tempfile
        graph = self.graph()
        judgements = {"status": "ok", "judgements": [verdict], "calibration": None}
        with tempfile.TemporaryDirectory() as directory:
            text = render.summary_markdown(graph, helpers.REPO_URL, analysis=analyze.analyze(graph),
                                           judgements=judgements, source_root=directory)

        self.assertNotIn("Before you change this", text)

    def test_cards_without_a_judgement_get_no_safety_block(self):
        graph = self.graph()

        text = render.summary_markdown(graph, helpers.REPO_URL, analysis=analyze.analyze(graph))

        self.assertNotIn("Before you change this", text)
        self.assertNotIn("Safety check details", text)

    def test_a_judged_card_with_no_fix_text_gets_no_safety_block(self):
        verdict = judged("Annotate", "Extract", fix={"summary": "", "shared_name": "",
                                                    "moved_steps": [], "stays_in_a": [], "stays_in_b": []})

        self.assertNotIn("Before you change this", self.card(verdict=verdict))


class SummaryExtrasTest(unittest.TestCase):
    def test_dead_candidates_and_suppressed_externals_are_reported(self):
        edges = [("e", "a"), ("a", "t"), ("u", "d")]
        graph = helpers.make_graph(
            edges, entries=["e"], dead=["u"],
            externals=[("t", "os.Open"), ("t", "fmt.Println"), ("t", "fmt.Sprintf")],
        )
        analysis = analyze.analyze(graph, ignored_packages=("fmt",))

        text = render.summary_markdown(graph, helpers.REPO_URL, analysis=analysis)

        self.assertIn("Dead-code candidates (2)", text)
        self.assertIn("p.d", text)
        self.assertIn("fmt (2)", text)

    def test_most_used_external_functions_are_ranked_by_calling_packages(self):
        graph = helpers.make_graph(
            [("e", "a"), ("e", "b")], entries=["e"],
            externals=[("a", "os.Open"), ("b", "os.Open"), ("b", "os.Remove")],
            packages={"a": "p/one", "b": "p/two"},
        )

        text = render.summary_markdown(graph, helpers.REPO_URL, analysis=analyze.analyze(graph))

        rows = [line for line in text.split("Most used external functions")[1].splitlines()
                if line.startswith("| os.")]
        self.assertTrue(rows[0].startswith("| os.Open | 2 |"))


if __name__ == "__main__":
    unittest.main()
