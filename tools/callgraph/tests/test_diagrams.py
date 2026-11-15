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

    def test_a_skipped_issue_does_not_shift_the_numbers_of_later_notes(self):
        steps = STEPS + [{"name": "validate", "a": [19, 20], "b": None, "same": False}]
        issues = [
            {"step": "validate", "function": "B", "note": "skipped: B has no such step"},
            {"step": "decode", "function": "A", "note": "kept"},
        ]

        diagram = diagrams.before(steps, issues, NAMES)

        self.assertEqual(diagram.legend, ((1, "kept"),))
        self.assertIn("decode (1)", labels(diagram))

    def test_an_issue_on_an_unknown_step_is_ignored(self):
        issues = [{"step": "nope", "function": "both", "note": "x"}]

        diagram = diagrams.before(STEPS, issues, NAMES)

        self.assertEqual(diagram.legend, ())


class ProblemMarkingTest(unittest.TestCase):
    def test_every_step_the_fix_moves_is_part_of_the_problem_on_both_sides(self):
        diagram = diagrams.before(STEPS, [], NAMES, moved=["build request", "send"])

        problem = sorted(n.label for n in diagram.nodes if n.problem)
        self.assertEqual(problem, ["build request", "build request", "send", "send"])

    def test_a_step_with_a_model_note_is_part_of_the_problem_even_if_not_moved(self):
        issues = [{"step": "decode", "function": "A", "note": "x"}]

        diagram = diagrams.before(STEPS, issues, NAMES, moved=["send"])

        self.assertEqual(sorted(n.label for n in diagram.nodes if n.problem),
                         ["decode (1)", "send", "send"])

    def test_nothing_is_marked_when_nothing_moves_and_nothing_is_noted(self):
        diagram = diagrams.before(STEPS, [], NAMES)

        self.assertFalse([n for n in diagram.nodes if n.problem])

    def test_the_after_diagram_has_no_problem_marks_and_keeps_each_steps_colour(self):
        before = diagrams.before(STEPS, [], NAMES, moved=["send"])
        fix = {"summary": "", "shared_name": "s", "moved_steps": ["send"],
               "stays_in_a": [], "stays_in_b": []}

        after = diagrams.apply_fix(before, fix, STEPS)

        self.assertFalse([n for n in after.nodes if n.problem])
        roles = {n.label: n.role for n in after.nodes}
        self.assertEqual(roles["build request"], "same")   # stays, and was orange before
        self.assertEqual(roles["build prompt"], "differs")  # stays, and was grey before


class CodeDetailTest(unittest.TestCase):
    REFS = {("A", "build request"): "json.Marshal, http.NewRequest · L6-L10",
            ("B", "build request"): "json.Marshal, http.NewRequest · L5-L9"}

    def test_each_box_carries_the_code_detail_for_its_own_side(self):
        diagram = diagrams.before(STEPS, [], NAMES, refs=self.REFS)

        details = {n.id: n.detail for n in diagram.nodes if n.detail}
        self.assertEqual(sorted(details.values()), sorted(self.REFS.values()))

    def test_the_detail_is_printed_on_a_second_line_of_the_box_and_escaped(self):
        refs = {("A", "build request"): 'say "hi" <b>'}

        text = diagrams.to_mermaid(diagrams.before(STEPS, [], NAMES, refs=refs))

        self.assertIn('build request<br/>say #quot;hi#quot; #lt;b#gt;', text)

    def test_steps_that_stay_keep_their_detail_in_the_after_diagram(self):
        refs = {("A", "decode"): "json.Unmarshal · L16-L18"}
        before = diagrams.before(STEPS, [], NAMES, refs=refs)
        fix = {"summary": "", "shared_name": "s", "moved_steps": ["send"],
               "stays_in_a": [], "stays_in_b": []}

        after = diagrams.apply_fix(before, fix, STEPS, refs=refs)

        self.assertIn("json.Unmarshal · L16-L18", [n.detail for n in after.nodes])


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
        shared = [n for n in after.nodes if n.dashed]
        self.assertEqual([n.label for n in shared], ["chatCompletion"])
        self.assertEqual(shared[0].role, "same")  # the merged duplicates keep their colour
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

        shared = [n for n in after.nodes if n.dashed][0]
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
        self.assertTrue(text.startswith("flowchart TB"))

    def test_step_diagrams_run_top_to_bottom_and_the_small_route_diagram_left_to_right(self):
        before = diagrams.before(STEPS, [], NAMES)
        fix = {"summary": "", "shared_name": "s", "moved_steps": ["send"],
               "stays_in_a": [], "stays_in_b": []}

        self.assertTrue(self.text(before).startswith("flowchart TB"))
        self.assertTrue(self.text(diagrams.apply_fix(before, fix, STEPS)).startswith("flowchart TB"))
        self.assertTrue(self.text(diagrams.two_routes("a", "b", ["t"])).startswith("flowchart LR"))

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

        for role in ("same", "differs", "function", "problem"):
            self.assertIn(f"classDef {role} ", text)
        self.assertRegex(text, r"class n\d+(,n\d+)* problem")
        self.assertIn("classDef new ", after)
        self.assertIn("stroke-dasharray", after)


class StepReferenceTest(unittest.TestCase):
    LINES = [
        "\tresponse, err := client.Do(request)",
        "\tif err != nil {",
        '\t\treturn x, fmt.Errorf("boom: %s", Redact(err))',
        "\t}",
        "\tdefer response.Body.Close()",
    ]

    def test_the_first_calls_in_the_range_are_listed_with_the_line_range(self):
        ref = diagrams.step_reference(self.LINES, 1, 5)

        self.assertEqual(ref, "client.Do, fmt.Errorf, Redact · L1-5")

    def test_control_keywords_and_comments_are_not_call_names(self):
        lines = ["\tif ready() { // closeAll(now)", "\t\tfor range items {}"]

        self.assertEqual(diagrams.step_reference(lines, 1, 2), "ready · L1-2")

    def test_a_step_without_calls_shows_the_start_of_its_first_line(self):
        lines = ["var output ClaimAnnotation", "}"]

        self.assertEqual(diagrams.step_reference(lines, 1, 2), "var output ClaimAnnotation · L1-2")

    def test_a_single_line_range_and_missing_source_still_give_a_reference(self):
        self.assertEqual(diagrams.step_reference(self.LINES, 1, 1), "client.Do · L1")
        self.assertEqual(diagrams.step_reference(None, 74, 78), "L74-78")

    def test_a_range_beyond_the_file_gives_just_the_range(self):
        self.assertEqual(diagrams.step_reference(self.LINES, 40, 42), "L40-42")


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
