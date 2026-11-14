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


if __name__ == "__main__":
    unittest.main()
