import re
import unittest

from tools.callgraph import build, render
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

    def test_function_level_diagram_is_included_when_small(self):
        summary = render.summary_markdown(fixture_graph(), helpers.REPO_URL, max_function_edges=10)

        self.assertEqual(summary.count("```mermaid"), 2)

    def test_function_level_diagram_is_skipped_with_a_note_when_too_large(self):
        summary = render.summary_markdown(fixture_graph(), helpers.REPO_URL, max_function_edges=2)

        self.assertEqual(summary.count("```mermaid"), 1)
        self.assertIn("function-level diagram omitted", summary)


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


if __name__ == "__main__":
    unittest.main()
