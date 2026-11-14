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


class MermaidTest(unittest.TestCase):
    def test_package_graph_counts_call_sites_between_packages(self):
        mermaid = render.package_mermaid(multi_package_graph())

        self.assertRegex(mermaid, r"alpha.*-->\|2\|.*beta")

    def test_calls_within_one_package_are_not_drawn(self):
        mermaid = render.package_mermaid(multi_package_graph())

        self.assertEqual(mermaid.count("-->"), 1)

    def test_package_ids_are_valid_mermaid_identifiers(self):
        mermaid = render.package_mermaid(multi_package_graph())

        for identifier in re.findall(r"^\s*(\w[^\s\[]*)\[", mermaid, flags=re.M):
            self.assertRegex(identifier, r"^[A-Za-z0-9_]+$")


class PackageLabelTest(unittest.TestCase):
    def labels(self, mermaid):
        return re.findall(r'\["([^"]*)"\]', mermaid)

    def test_common_module_prefix_is_stripped_from_package_labels(self):
        nodes = [
            ["m.a", "A", "github.com/o/r/svc/cmd/tool", "a.go", 1, 2],
            ["m.b", "B", "github.com/o/r/svc/internal/store", "b.go", 1, 2],
        ]
        graph = build.build_graph(helpers.raw_nodes_csv(nodes), helpers.raw_edges_csv([]), helpers.SHA)

        self.assertEqual(self.labels(render.package_mermaid(graph)), ["cmd/tool", "internal/store"])

    def test_single_package_keeps_its_last_path_segment(self):
        self.assertEqual(self.labels(render.package_mermaid(fixture_graph())), ["fixture"])

    def test_label_prefix_is_cut_on_path_boundaries_only(self):
        nodes = [
            ["m.a", "A", "x/storeA", "a.go", 1, 2],
            ["m.b", "B", "x/storeB", "b.go", 1, 2],
        ]
        graph = build.build_graph(helpers.raw_nodes_csv(nodes), helpers.raw_edges_csv([]), helpers.SHA)

        self.assertEqual(self.labels(render.package_mermaid(graph)), ["storeA", "storeB"])


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

    def test_summary_has_only_the_package_diagram_not_a_function_level_one(self):
        summary = render.summary_markdown(fixture_graph(), helpers.REPO_URL)

        self.assertEqual(summary.count("```mermaid"), 1)
        self.assertNotIn("### Functions", summary)


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
        self.assertEqual(summary.count("<details>"), 2)
        self.assertEqual(summary.count("</details>"), 2)

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
        return text.split("### Redundant routes")[1].split("### Dead-code")[0]

    def test_the_card_says_in_plain_words_which_functions_reach_which_targets(self):
        text = self.section(self.summary(self.INDEPENDENT, ["e1", "e2"]))

        self.assertIn("`p.a` and `p.b` each reach `p.t` on separate routes", text)

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

    def test_every_card_has_its_own_diagram_in_addition_to_the_package_diagram(self):
        text = self.summary(self.INDEPENDENT, ["e1", "e2"])

        self.assertEqual(text.count("```mermaid"), 2)

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

    def test_routes_and_independence_details_are_collapsed_under_the_card(self):
        text = self.section(self.summary(self.INDEPENDENT, ["e1", "e2"]))

        self.assertIn("<details><summary>Details", text)
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

    def test_an_llm_verdict_is_shown_as_advisory_with_its_reasoning(self):
        judgements = {
            "calibration": None,
            "judgements": [{
                "first": "a", "second": "b", "status": "ok", "verdict": "duplicate",
                "confidence": "high", "summary": "Same pipeline twice.",
                "essential_differences": ["different prompt"], "accidental_differences": [],
                "counter_argument": "They serve different features.",
                "suggested_consolidation": "Share one client.", "risks": [],
                "evidence": [], "citations_valid": 2, "citations_invalid": 0,
            }],
        }

        text = self.section(self.summary(self.INDEPENDENT, ["e1", "e2"], judgements=judgements))

        self.assertIn("LLM verdict (advisory): duplicate (high confidence)", text)
        self.assertIn("Same pipeline twice.", text)
        self.assertIn("They serve different features.", text)
        self.assertIn("2 of 2 citations verified", text)

    def test_llm_text_is_escaped_so_it_cannot_inject_markup(self):
        judgements = {"calibration": None, "judgements": [{
            "first": "a", "second": "b", "status": "ok", "verdict": "unsure",
            "confidence": "low", "summary": "<script>alert(1)</script> [x](http://evil)",
            "essential_differences": [], "accidental_differences": [], "counter_argument": "",
            "suggested_consolidation": "", "risks": [], "evidence": [],
            "citations_valid": 0, "citations_invalid": 0,
        }]}

        text = self.section(self.summary(self.INDEPENDENT, ["e1", "e2"], judgements=judgements))

        self.assertNotIn("<script>", text)
        self.assertIn("&lt;script&gt;", text)
        self.assertNotIn("[x](http://evil)", text)

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

    def test_no_judgements_means_no_llm_text(self):
        text = self.summary(self.INDEPENDENT, ["e1", "e2"])

        self.assertNotIn("LLM", text)


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
