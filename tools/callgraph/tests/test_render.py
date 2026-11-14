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


class SummaryFindingsTest(unittest.TestCase):
    INDEPENDENT = [("e1", "s1"), ("s1", "t"), ("e2", "s2"), ("s2", "t")]
    MERGE_THEN_SPLIT = [
        ("e1", "run"), ("run", "resolve"), ("run", "submit"), ("resolve", "t"), ("submit", "t"),
        ("e2", "annotate"), ("annotate", "t"),
    ]

    def summary(self, edges, entries, externals=(("t", "os.Open"),), analysis_options=None, **kw):
        graph = helpers.make_graph(edges, entries=entries, externals=list(externals))
        analysis = analyze.analyze(graph, **(analysis_options or {}))
        return render.summary_markdown(graph, helpers.REPO_URL, analysis=analysis, **kw)

    def test_a_flagged_terminal_is_listed_with_its_independent_route_count(self):
        text = self.summary(self.INDEPENDENT, ["e1", "e2"]).split("### Redundant routes")[1]

        self.assertIn("`t`", text)
        self.assertIn("2 independent routes", text)
        self.assertIn("2 entries", text)

    def test_gateways_link_to_their_source_and_say_how_many_entries_they_serve(self):
        text = self.summary(self.INDEPENDENT, ["e1", "e2"])

        self.assertIn(f"[p.s1]({helpers.REPO_URL}/blob/{helpers.SHA}/s1.go#L1-L100)", text)
        self.assertIn("serves 1 entry", text)

    def test_each_route_is_listed_as_a_chain_of_function_names(self):
        text = self.summary(self.INDEPENDENT, ["e1", "e2"])

        self.assertIn("p.e1 > p.s1 > p.t", text)
        self.assertIn("p.e2 > p.s2 > p.t", text)

    def test_a_direct_call_gateway_is_described_as_a_direct_call(self):
        text = self.summary([("e1", "t"), ("e2", "t")], ["e1", "e2"])

        self.assertIn("direct call", text)

    def test_nested_routes_are_shown_under_the_entry_that_has_them(self):
        text = self.summary(self.MERGE_THEN_SPLIT, ["e1", "e2"])

        self.assertIn("Nested under `p.e1`", text)
        self.assertIn("p.resolve", text)
        self.assertIn("p.submit", text)

    def test_a_nested_block_shared_by_several_terminals_is_shown_once(self):
        # Both t1 and t2 sit below x, so both inherit e1's split above x.
        edges = [
            ("e1", "a"), ("e1", "b"), ("a", "x"), ("b", "x"), ("e2", "x"),
            ("x", "t1"), ("x", "t2"),
        ]
        text = self.summary(
            edges, ["e1", "e2"], externals=(("t1", "os.Open"), ("t2", "os.Create"))
        )

        self.assertEqual(text.count("**Nested under `p.e1`**"), 1)
        self.assertIn("same nested routes as #1", text)

    def test_no_flagged_terminals_says_so(self):
        text = self.summary([("e", "a"), ("a", "t")], ["e"])

        self.assertIn("No redundant routes found", text)

    def test_findings_are_capped_with_a_count(self):
        edges = self.INDEPENDENT + [("e1", "u1"), ("u1", "u"), ("e2", "u2"), ("u2", "u")]
        text = self.summary(
            edges, ["e1", "e2"], externals=(("t", "os.Open"), ("u", "os.Open")), max_findings=1
        )

        self.assertIn("showing first 1 of 2", text)

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
