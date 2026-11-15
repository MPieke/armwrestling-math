import re
import unittest

from tools.callgraph import diagrams

NAMES = {"A": "Annotate", "B": "Extract"}
STEPS = [
    {"name": "build prompt", "a": [3, 5], "b": [3, 4], "same": False},
    {"name": "build request", "a": [6, 10], "b": [5, 9], "same": True},
    {"name": "send", "a": [11, 15], "b": [10, 14], "same": True},
    {"name": "decode", "a": [16, 18], "b": [15, 17], "same": False},
]


def labels(diagram):
    return [node.label for node in diagram.nodes]


class BeforeDiagramTest(unittest.TestCase):
    def test_each_function_gets_a_header_and_a_chain_of_its_steps(self):
        diagram = diagrams.before(STEPS, [], NAMES)

        self.assertEqual(len(diagram.nodes), 10)  # 2 headers + 4 steps per function
        solid = [e for e in diagram.edges if e.style == "solid"]
        self.assertEqual(len(solid), 8)

    def test_matched_steps_are_linked_with_a_dotted_same_edge(self):
        diagram = diagrams.before(STEPS, [], NAMES)

        dotted = [e for e in diagram.edges if e.style == "dotted"]
        self.assertEqual(len(dotted), 2)
        self.assertTrue(all(e.label == "same" for e in dotted))

    def test_roles_distinguish_headers_matched_and_different_steps(self):
        diagram = diagrams.before(STEPS, [], NAMES)

        roles = {}
        for node in diagram.nodes:
            roles.setdefault(node.role, []).append(node.label)
        self.assertEqual(sorted(roles["function"]), ["Annotate", "Extract"])
        self.assertEqual(roles["same"].count("build request"), 2)
        self.assertEqual(roles["differs"].count("build prompt"), 2)

    def test_a_step_only_one_function_has_appears_only_in_that_chain(self):
        steps = STEPS + [{"name": "validate", "a": [19, 20], "b": None, "same": False}]

        diagram = diagrams.before(steps, [], NAMES)

        self.assertEqual(labels(diagram).count("validate"), 1)
        self.assertEqual(len([e for e in diagram.edges if e.style == "dotted"]), 2)

    def test_fewer_than_two_steps_gives_no_diagram(self):
        self.assertIsNone(diagrams.before(STEPS[:1], [], NAMES))
        self.assertIsNone(diagrams.before([], [], NAMES))


class IssueMarkerTest(unittest.TestCase):
    ISSUES = [
        {"step": "build request", "function": "both", "note": "repeated"},
        {"step": "decode", "function": "A", "note": "only here"},
    ]

    def test_issues_are_numbered_in_order_and_listed_in_the_legend(self):
        diagram = diagrams.before(STEPS, self.ISSUES, NAMES)

        self.assertEqual(diagram.legend, ((1, "repeated"), (2, "only here")))

    def test_both_marks_the_step_on_each_side_and_a_marks_only_function_a(self):
        diagram = diagrams.before(STEPS, self.ISSUES, NAMES)

        marked = {n.label: n.issues for n in diagram.nodes if n.issues}
        request_nodes = [n for n in diagram.nodes if n.issues == (1,)]
        decode_nodes = [n for n in diagram.nodes if n.issues == (2,)]
        self.assertEqual(len(request_nodes), 2)
        self.assertEqual(len(decode_nodes), 1)
        self.assertEqual(sorted(marked), ["build request (1)", "decode (2)"])

    def test_the_marker_number_is_part_of_the_node_label(self):
        diagram = diagrams.before(STEPS, self.ISSUES, NAMES)

        self.assertIn("build request (1)", labels(diagram))
        self.assertIn("decode (2)", labels(diagram))

    def test_an_issue_on_an_unknown_step_is_ignored(self):
        issues = [{"step": "nope", "function": "both", "note": "x"}]

        diagram = diagrams.before(STEPS, issues, NAMES)

        self.assertEqual(diagram.legend, ())


class AfterFixTest(unittest.TestCase):
    FIX = {"summary": "share it", "shared_name": "chatCompletion",
           "moved_steps": ["build request", "send"], "stays_in_a": [], "stays_in_b": []}

    def after(self, fix=None, steps=STEPS):
        return diagrams.apply_fix(diagrams.before(steps, [], NAMES), fix or self.FIX, steps)

    def edge_pairs(self, diagram):
        label = {node.id: node.label for node in diagram.nodes}
        return {(label[e.source], label[e.target]) for e in diagram.edges}

    def test_moved_steps_of_both_functions_become_one_shared_node(self):
        after = self.after()

        self.assertEqual(len(after.nodes), 7)  # 2 headers, 2 prompts, 2 decodes, 1 shared
        shared = [n for n in after.nodes if n.role == "shared"]
        self.assertEqual([n.label for n in shared], ["chatCompletion"])
        self.assertTrue(shared[0].dashed)
        self.assertNotIn("send", labels(after))

    def test_each_function_flows_through_the_shared_node_between_its_own_steps(self):
        pairs = self.edge_pairs(self.after())

        self.assertIn(("build prompt", "chatCompletion"), pairs)
        self.assertIn(("chatCompletion", "decode"), pairs)
        self.assertIn(("Annotate", "build prompt"), pairs)

    def test_a_moved_block_at_the_start_hangs_off_the_function_header(self):
        fix = {**self.FIX, "moved_steps": ["build prompt", "build request"]}

        pairs = self.edge_pairs(self.after(fix))

        self.assertIn(("Annotate", "chatCompletion"), pairs)
        self.assertIn(("Extract", "chatCompletion"), pairs)

    def test_a_moved_block_at_the_end_leaves_the_shared_node_as_a_sink(self):
        fix = {**self.FIX, "moved_steps": ["send", "decode"]}

        after = self.after(fix)

        shared = [n for n in after.nodes if n.role == "shared"][0]
        self.assertFalse([e for e in after.edges if e.source == shared.id])

    def test_unknown_moved_steps_are_ignored_and_nothing_to_move_gives_no_diagram(self):
        self.assertIsNone(self.after({**self.FIX, "moved_steps": ["invented"]}))
        self.assertIsNone(self.after({**self.FIX, "moved_steps": []}))

    def test_a_missing_shared_name_gets_a_neutral_label(self):
        after = self.after({**self.FIX, "shared_name": ""})

        self.assertIn("shared function", labels(after))


class TwoRoutesDiagramTest(unittest.TestCase):
    def test_the_owner_reaches_the_target_directly_and_through_the_helper(self):
        diagram = diagrams.two_routes("ingestCandidate", "auditFailure", ["Submit"])

        label = {n.id: n.label for n in diagram.nodes}
        pairs = {(label[e.source], label[e.target], e.label) for e in diagram.edges}
        self.assertEqual(
            pairs,
            {("ingestCandidate", "auditFailure", ""), ("auditFailure", "Submit", ""),
             ("ingestCandidate", "Submit", "directly")},
        )


class MermaidTest(unittest.TestCase):
    def text(self, diagram):
        return diagrams.to_mermaid(diagram)

    def test_every_edge_refers_to_a_defined_node(self):
        text = self.text(diagrams.before(STEPS, [], NAMES))

        defined = set(re.findall(r'^\s*(n\d+)\["', text, re.M))
        used = set(re.findall(r"\b(n\d+)\b(?=\s*(?:-->|-\.|\.-))|(?<=-->\s)(n\d+)|(?<=\.-\s)(n\d+)", text))
        refs = {x for group in used for x in group if x}
        self.assertTrue(refs <= defined)
        self.assertTrue(text.startswith("flowchart LR"))

    def test_dotted_same_links_use_mermaid_dotted_syntax_with_a_label(self):
        text = self.text(diagrams.before(STEPS, [], NAMES))

        self.assertEqual(len(re.findall(r"-\. same \.-", text)), 2)

    def test_quotes_in_labels_are_escaped(self):
        steps = [{"name": 'say "hi"', "a": [3, 4], "b": [3, 4], "same": True},
                 {"name": "x", "a": [5, 6], "b": [5, 6], "same": True}]

        text = self.text(diagrams.before(steps, [], NAMES))

        self.assertNotIn('say "hi"', text)
        self.assertIn("say #quot;hi#quot;", text)

    def test_roles_and_issue_marks_get_styles_and_the_shared_node_is_dashed(self):
        issues = [{"step": "send", "function": "both", "note": "x"}]
        before = diagrams.before(STEPS, issues, NAMES)
        fix = {"summary": "", "shared_name": "s", "moved_steps": ["build request"],
               "stays_in_a": [], "stays_in_b": []}

        text = self.text(before)
        after = self.text(diagrams.apply_fix(before, fix, STEPS))

        for role in ("same", "differs", "function", "issue"):
            self.assertIn(f"classDef {role} ", text)
        self.assertRegex(text, r"class n\d+(,n\d+)* issue")
        self.assertIn("classDef shared ", after)
        self.assertIn("stroke-dasharray", after)


class CapTest(unittest.TestCase):
    def test_very_long_step_lists_are_cut_with_a_note(self):
        steps = [
            {"name": f"step {i}", "a": [3 + 2 * i, 4 + 2 * i], "b": [3 + 2 * i, 4 + 2 * i], "same": True}
            for i in range(20)
        ]

        diagram = diagrams.before(steps, [], NAMES)

        per_function = (len(diagram.nodes) - 2) // 2
        self.assertLessEqual(per_function, diagrams.MAX_STEPS)
        self.assertIn("showing the first", diagram.note)


if __name__ == "__main__":
    unittest.main()
