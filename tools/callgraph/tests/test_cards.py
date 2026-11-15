import unittest

from tools.callgraph import analyze, cards
from tools.callgraph.tests import helpers


def build(edges, entries, externals=(), ignored=(), **options):
    graph = helpers.make_graph(edges, entries=entries, externals=list(externals))
    analysis = analyze.analyze(graph, ignored_packages=ignored, **options)
    return graph, cards.build_cards(graph, analysis, ignored_packages=ignored)


def pairs(card_list):
    return [(card.first, card.second) for card in card_list]


class PairingTest(unittest.TestCase):
    def test_two_callers_on_separate_routes_form_one_card_with_the_target(self):
        edges = [("e1", "a"), ("a", "t"), ("e2", "b"), ("b", "t")]

        _, found = build(edges, ["e1", "e2"], [("t", "os.Open")])

        self.assertEqual(pairs(found), [("a", "b")])
        self.assertEqual(found[0].targets, ("t",))

    def test_one_pair_reaching_two_targets_is_a_single_card(self):
        # The Annotate/Extract shape: both call both helpers.
        edges = [("e1", "a"), ("e2", "b"), ("a", "t1"), ("a", "t2"), ("b", "t1"), ("b", "t2")]

        _, found = build(edges, ["e1", "e2"], [("t1", "os.Open"), ("t2", "os.Create")])

        self.assertEqual(pairs(found), [("a", "b")])
        self.assertEqual(found[0].targets, ("t1", "t2"))

    def test_three_callers_give_three_pairs(self):
        edges = [("e1", "a"), ("e2", "b"), ("e3", "c"), ("a", "t"), ("b", "t"), ("c", "t")]

        _, found = build(edges, ["e1", "e2", "e3"], [("t", "os.Open")])

        self.assertEqual(sorted(pairs(found)), [("a", "b"), ("a", "c"), ("b", "c")])

    def test_a_caller_that_also_calls_the_other_is_still_paired_with_it(self):
        # a reaches t directly and through b: two independent routes, as with ingestCandidate
        # calling Submit directly and through auditFailure.
        edges = [("e1", "a"), ("e2", "b"), ("a", "b"), ("a", "t"), ("b", "t")]

        _, found = build(edges, ["e1", "e2"], [("t", "os.Open")])

        self.assertEqual(pairs(found), [("a", "b")])

    def test_functions_are_paired_only_within_one_segment(self):
        # Annotate/Extract/Transcribe shape: Annotate and Extract are independent in the global
        # segment, Extract and Transcribe in the nested one; Annotate and Transcribe never are.
        edges = [
            ("e1", "ic"), ("ic", "extract"), ("ic", "transcribe"),
            ("extract", "t"), ("transcribe", "t"), ("e2", "annotate"), ("annotate", "t"),
        ]

        _, found = build(edges, ["e1", "e2"], [("t", "os.Open")])

        self.assertEqual(sorted(pairs(found)), [("annotate", "extract"), ("extract", "transcribe")])

    def test_a_split_below_a_merge_point_pairs_the_functions_before_that_point(self):
        # ingestCandidate reaches submit directly and through auditFailure (the real shape).
        edges = [
            ("e1", "run"), ("run", "ic"), ("ic", "submit"), ("ic", "af"), ("af", "submit"),
            ("e2", "sr"), ("sr", "ri"), ("submit", "ri"),
        ]

        _, found = build(edges, ["e1", "e2"], [("ri", "os.Open")])

        self.assertIn(("af", "ic"), pairs(found))
        self.assertIn(("sr", "submit"), pairs(found))
        by_pair = {(c.first, c.second): c for c in found}
        self.assertEqual(by_pair[("af", "ic")].targets, ("submit",))

    def test_a_card_says_where_its_routes_diverge(self):
        edges = [
            ("e1", "run"), ("run", "ic"), ("ic", "submit"), ("ic", "af"), ("af", "submit"),
            ("e2", "sr"), ("sr", "ri"), ("submit", "ri"),
        ]

        _, found = build(edges, ["e1", "e2"], [("ri", "os.Open")])

        by_pair = {(c.first, c.second): c for c in found}
        nested = by_pair[("af", "ic")]
        self.assertEqual((nested.starts, nested.from_entries), (("ic",), False))
        top = by_pair[("sr", "submit")]
        self.assertEqual((top.starts, top.from_entries), ((), True))

    def test_two_independent_functions_are_a_pair_card(self):
        edges = [("e1", "a"), ("a", "t"), ("e2", "b"), ("b", "t")]

        _, found = build(edges, ["e1", "e2"], [("t", "os.Open")])

        self.assertEqual((found[0].kind, found[0].owner, found[0].helper), ("pair", None, None))

    def test_a_function_that_calls_the_other_is_a_two_routes_card_owned_by_the_caller(self):
        edges = [("e1", "a"), ("e2", "b"), ("a", "b"), ("a", "t"), ("b", "t")]

        _, found = build(edges, ["e1", "e2"], [("t", "os.Open")])

        self.assertEqual(len(found), 1)
        self.assertEqual((found[0].kind, found[0].owner, found[0].helper), ("two_routes", "a", "b"))

    def test_the_ingest_candidate_shape_is_a_two_routes_card(self):
        edges = [
            ("e1", "run"), ("run", "ic"), ("ic", "submit"), ("ic", "af"), ("af", "submit"),
            ("e2", "sr"), ("sr", "ri"), ("submit", "ri"),
        ]

        _, found = build(edges, ["e1", "e2"], [("ri", "os.Open")])

        by_pair = {(c.first, c.second): c for c in found}
        card = by_pair[("af", "ic")]
        self.assertEqual((card.kind, card.owner, card.helper), ("two_routes", "ic", "af"))
        self.assertEqual(by_pair[("sr", "submit")].kind, "pair")

    def test_reaching_the_other_through_an_intermediate_function_counts(self):
        edges = [("e1", "a"), ("e2", "b"), ("a", "x"), ("x", "b"), ("a", "t"), ("b", "t")]

        _, found = build(edges, ["e1", "e2"], [("t", "os.Open")])

        card = [c for c in found if (c.first, c.second) == ("a", "b")][0]
        self.assertEqual((card.kind, card.owner, card.helper), ("two_routes", "a", "b"))

    def test_terminals_that_are_not_flagged_produce_no_cards(self):
        _, found = build([("e", "a"), ("a", "t")], ["e"], [("t", "os.Open")])

        self.assertEqual(found, ())

    def test_cards_with_more_targets_come_first(self):
        edges = [
            ("e1", "a"), ("e2", "b"), ("a", "t1"), ("b", "t1"), ("a", "t2"), ("b", "t2"),
            ("e3", "c"), ("e4", "d"), ("c", "u"), ("d", "u"),
        ]
        externals = [("t1", "os.Open"), ("t2", "os.Create"), ("u", "os.Remove")]

        _, found = build(edges, ["e1", "e2", "e3", "e4"], externals)

        self.assertEqual(pairs(found), [("a", "b"), ("c", "d")])

    def test_each_card_lists_the_entries_that_reach_each_function(self):
        edges = [("e1", "a"), ("e2", "a"), ("a", "t"), ("e3", "b"), ("b", "t")]

        _, found = build(edges, ["e1", "e2", "e3"], [("t", "os.Open")])

        self.assertEqual(dict(found[0].reached_from), {"a": ("e1", "e2"), "b": ("e3",)})

    def test_routes_end_in_a_target_and_pass_through_one_of_the_pair(self):
        edges = [("e1", "a"), ("a", "t"), ("e2", "b"), ("b", "t")]

        _, found = build(edges, ["e1", "e2"], [("t", "os.Open")])

        self.assertEqual(
            sorted(found[0].routes), [("e1", "a", "t"), ("e2", "b", "t")]
        )


class EvidenceTest(unittest.TestCase):
    def evidence(self, a_calls, b_calls, ignored=()):
        edges = [("e1", "a"), ("e2", "b"), ("a", "t"), ("b", "t")]
        edges += [("a", x) for x in a_calls if not x.startswith("ext:")]
        edges += [("b", x) for x in b_calls if not x.startswith("ext:")]
        externals = [("t", "os.Open")]
        externals += [("a", x[4:]) for x in a_calls if x.startswith("ext:")]
        externals += [("b", x[4:]) for x in b_calls if x.startswith("ext:")]
        graph, found = build(edges, ["e1", "e2"], externals, ignored)
        return graph, found[0].evidence

    def test_shared_and_different_calls_are_listed_per_function(self):
        _, evidence = self.evidence(
            ["h1", "h2", "ext:json.Marshal", "only_a"], ["h1", "h2", "ext:json.Marshal", "only_b"]
        )

        self.assertEqual(evidence.shared_callees, ("h1", "h2"))
        self.assertEqual(evidence.shared_externals, ("json.Marshal",))
        self.assertEqual(evidence.only_first, ("only_a",))
        self.assertEqual(evidence.only_second, ("only_b",))

    def test_every_shared_callee_is_a_direct_callee_of_both_functions(self):
        graph, evidence = self.evidence(["h1", "h2", "x"], ["h1", "h2", "y"])

        direct = {}
        for edge in graph.edges:
            direct.setdefault(edge.caller_id, set()).add(edge.callee_id)
        for callee in evidence.shared_callees:
            self.assertIn(callee, direct["a"])
            self.assertIn(callee, direct["b"])

    def test_identical_call_sets_are_very_similar(self):
        _, evidence = self.evidence(["h1", "ext:json.Marshal"], ["h1", "ext:json.Marshal"])

        self.assertEqual(evidence.similarity, 1.0)
        self.assertEqual(evidence.band, "very similar")

    def test_disjoint_call_sets_have_little_overlap(self):
        _, evidence = self.evidence(["x1", "x2"], ["y1", "y2"])

        self.assertEqual(evidence.similarity, 0.0)
        self.assertEqual(evidence.band, "little overlap")

    def test_partial_overlap_is_partly_similar(self):
        # shared {h1, h2}; union {h1, h2, x1, x2, y1} -> 2/5 = 0.4
        _, evidence = self.evidence(["h1", "h2", "x1", "x2"], ["h1", "h2", "y1"])

        self.assertAlmostEqual(evidence.similarity, 0.4)
        self.assertEqual(evidence.band, "partly similar")

    def test_ignored_external_packages_do_not_count_as_shared(self):
        _, evidence = self.evidence(
            ["ext:fmt.Println", "ext:json.Marshal"], ["ext:fmt.Println", "ext:json.Marshal"],
            ignored=("fmt",),
        )

        self.assertEqual(evidence.shared_externals, ("json.Marshal",))


if __name__ == "__main__":
    unittest.main()
