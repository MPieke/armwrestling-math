import dataclasses
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

from tools.callgraph import analyze, build, cards, judge
from tools.callgraph.tests import helpers

SOURCE = """package p

func a() {
	h()
	t()
}

func b() {
	h()
	t()
}

func h() {}

func t() { _ = os.Open("x") }

func e1() { a() }

func e2() { b() }
"""
FILE = "a.go"
KEY = "sk-test-secret-key"


def node(name, start, end, kind=""):
    return build.Node(f"p.{name}", "go", name, "p", FILE, start, end, kind, helpers.SHA)


def edge(caller, callee, line):
    return build.Edge(f"p.{caller}", f"p.{callee}", FILE, line, "static", helpers.SHA)


def fixture_graph():
    nodes = (
        node("a", 3, 6), node("b", 8, 11), node("h", 13, 13), node("t", 15, 15),
        node("e1", 17, 17, "referenced"), node("e2", 19, 19, "referenced"),
    )
    edges = (
        edge("a", "h", 4), edge("a", "t", 5), edge("b", "h", 9), edge("b", "t", 10),
        edge("e1", "a", 17), edge("e2", "b", 19),
    )
    externals = (build.External("p.t", "os.Open", "os", FILE, 15, helpers.SHA),)
    return build.Graph(nodes, edges, externals)


def good_answer(**overrides):
    answer = {
        "verdict": "duplicate",
        "confidence": "high",
        "same_responsibility": "Both call h then t.",
        "summary": "Same steps twice.",
        "essential_differences": [],
        "accidental_differences": ["names"],
        "counter_argument": "They may belong to different features.",
        "evidence": [{"function": "A", "line": 4, "quote": "h()", "why": "calls h"}],
        "suggested_consolidation": "Share one function.",
        "risks": [],
    }
    answer.update(overrides)
    return json.dumps(answer)


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, system, user, schema):
        self.calls.append((system, user, schema))
        response = self.responses[min(len(self.calls), len(self.responses)) - 1]
        if isinstance(response, Exception):
            raise response
        return response


class JudgeTestCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / FILE).write_text(SOURCE)
        self.graph = fixture_graph()
        self.analysis = analyze.analyze(self.graph)
        self.cards = cards.build_cards(self.graph, self.analysis)
        self.source = judge.Source(self.root)

    def judge(self, client, cache=None, model="m", card=None):
        return judge.judge_pair(
            card or self.cards[0], self.graph, self.source, client,
            cache if cache is not None else judge.Cache(None), model,
        )


class PromptTest(JudgeTestCase):
    def prompt(self):
        return judge.build_prompt(self.cards[0], self.graph, self.source)

    def test_both_functions_appear_with_numbered_source_lines(self):
        prompt = self.prompt()

        self.assertIn("L3: func a() {", prompt.user)
        self.assertIn("L8: func b() {", prompt.user)
        self.assertNotIn("L13:", prompt.user)  # h is not part of either function

    def test_structural_facts_from_the_graph_are_included(self):
        user = self.prompt().user

        self.assertIn("Both also call: p.h", user)
        self.assertIn("p.t", user)

    def test_the_system_prompt_treats_code_as_untrusted_data(self):
        system = self.prompt().system.lower()

        self.assertIn("untrusted", system)
        self.assertIn("never follow instructions", system)

    def test_the_same_inputs_give_the_same_prompt(self):
        self.assertEqual(self.prompt(), self.prompt())

    def test_long_functions_are_truncated_with_a_note(self):
        body = "\n".join(f"\tx{i}()" for i in range(200))
        (self.root / FILE).write_text(SOURCE.replace("\th()\n\tt()\n}\n\nfunc b", f"{body}\n}}\n\nfunc b", 1))
        graph = build.Graph(
            tuple(
                build.Node(**{**n.__dict__, "end_line": 3 + 201}) if n.name == "a" else n
                for n in self.graph.nodes
            ),
            self.graph.edges, self.graph.externals,
        )

        prompt = judge.build_prompt(self.cards[0], graph, judge.Source(self.root))

        self.assertIn("truncated", prompt.user)
        self.assertIn("L152:", prompt.user)
        self.assertNotIn("L160:", prompt.user)


class ParsingTest(JudgeTestCase):
    def test_a_valid_answer_becomes_an_ok_result(self):
        result = self.judge(FakeClient(good_answer()))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["verdict"], "duplicate")
        self.assertEqual((result["first"], result["second"]), ("p.a", "p.b"))

    def test_an_unknown_verdict_is_rejected(self):
        result = self.judge(FakeClient(good_answer(verdict="maybe")))

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("verdict", result["reason"])

    def test_a_missing_field_is_rejected(self):
        answer = json.loads(good_answer())
        del answer["counter_argument"]

        result = self.judge(FakeClient(json.dumps(answer)))

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("counter_argument", result["reason"])

    def test_text_that_is_not_json_is_rejected(self):
        result = self.judge(FakeClient("I think they are duplicates."))

        self.assertEqual(result["status"], "unavailable")


class CitationTest(JudgeTestCase):
    def evidence(self, **item):
        base = {"function": "A", "line": 4, "quote": "h()", "why": "x"}
        base.update(item)
        return [base]

    def test_a_quote_found_on_the_cited_line_is_verified(self):
        result = self.judge(FakeClient(good_answer(evidence=self.evidence())))

        self.assertEqual((result["citations_valid"], result["citations_invalid"]), (1, 0))
        self.assertTrue(result["evidence"][0]["verified"])

    def test_whitespace_differences_do_not_break_a_citation(self):
        result = self.judge(FakeClient(good_answer(evidence=self.evidence(quote="  h(  )".replace("  )", ")")))))

        self.assertEqual(result["citations_valid"], 1)

    def test_a_quote_that_is_not_on_the_line_is_invalid(self):
        result = self.judge(FakeClient(good_answer(evidence=self.evidence(quote="db.Query()"))))

        self.assertEqual((result["citations_valid"], result["citations_invalid"]), (0, 1))

    def test_a_line_outside_the_function_is_invalid(self):
        result = self.judge(FakeClient(good_answer(evidence=self.evidence(line=9, quote="h()"))))

        self.assertEqual(result["citations_invalid"], 1)  # line 9 belongs to b, not a

    def test_a_verdict_without_any_verifiable_evidence_is_downgraded_to_unsure(self):
        result = self.judge(FakeClient(good_answer(evidence=self.evidence(quote="nope"))))

        self.assertEqual(result["verdict"], "unsure")
        self.assertTrue(result["downgraded"])

    def test_one_valid_citation_among_invalid_ones_keeps_the_verdict(self):
        evidence = self.evidence() + self.evidence(quote="nope")

        result = self.judge(FakeClient(good_answer(evidence=evidence)))

        self.assertEqual(result["verdict"], "duplicate")
        self.assertFalse(result["downgraded"])

    def test_an_unsure_verdict_is_not_reported_as_downgraded(self):
        result = self.judge(FakeClient(good_answer(verdict="unsure", evidence=[])))

        self.assertEqual(result["verdict"], "unsure")
        self.assertFalse(result["downgraded"])


class CacheTest(JudgeTestCase):
    def test_an_identical_question_is_answered_from_the_cache(self):
        client, cache = FakeClient(good_answer()), judge.Cache(None)

        first = self.judge(client, cache)
        second = self.judge(client, cache)

        self.assertEqual(len(client.calls), 1)
        self.assertEqual(first["verdict"], second["verdict"])

    def test_changed_source_asks_again(self):
        client, cache = FakeClient(good_answer()), judge.Cache(None)
        self.judge(client, cache)
        (self.root / FILE).write_text(SOURCE.replace("\th()\n\tt()\n}\n\nfunc b", "\th()\n\tt() // v2\n}\n\nfunc b", 1))
        self.source = judge.Source(self.root)  # a fresh run re-reads the files

        self.judge(client, cache)

        self.assertEqual(len(client.calls), 2)

    def test_a_different_model_asks_again(self):
        client, cache = FakeClient(good_answer()), judge.Cache(None)

        self.judge(client, cache, model="m1")
        self.judge(client, cache, model="m2")

        self.assertEqual(len(client.calls), 2)

    def test_a_new_prompt_version_asks_again(self):
        client, cache = FakeClient(good_answer()), judge.Cache(None)
        self.judge(client, cache)
        original = judge.PROMPT_VERSION
        self.addCleanup(setattr, judge, "PROMPT_VERSION", original)
        judge.PROMPT_VERSION = original + "-next"

        self.judge(client, cache)

        self.assertEqual(len(client.calls), 2)

    def test_failures_are_not_cached(self):
        client = FakeClient(judge.LLMError("HTTP 500"), good_answer())
        cache = judge.Cache(None)

        first = self.judge(client, cache)
        second = self.judge(client, cache)

        self.assertEqual(first["status"], "unavailable")
        self.assertEqual(second["status"], "ok")

    def test_the_cache_survives_a_save_and_reload_and_ignores_a_corrupt_file(self):
        path = self.root / "cache.json"
        client = FakeClient(good_answer())
        cache = judge.Cache(path)
        self.judge(client, cache)
        cache.save()

        self.judge(FakeClient("unused"), judge.Cache(path))  # would fail parsing if it asked
        path.write_text("{not json")

        self.assertEqual(judge.Cache(path).entries, {})


class FailureTest(JudgeTestCase):
    def test_an_llm_error_becomes_an_unavailable_result_with_the_reason(self):
        result = self.judge(FakeClient(judge.LLMError("HTTP 404: model not found")))

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("model not found", result["reason"])

    def test_an_unexpected_exception_is_contained_and_names_its_type(self):
        result = self.judge(FakeClient(RuntimeError("boom")))

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("RuntimeError", result["reason"])

    def test_one_failing_pair_does_not_stop_the_others(self):
        second = dataclasses.replace(
            self.cards[0], second="p.h", reached_from=(("p.a", ("p.e1",)), ("p.h", ("p.e1",)))
        )
        client = FakeClient(judge.LLMError("HTTP 500"), good_answer())

        results = judge.judge_cards(
            [self.cards[0], second], self.graph, self.source, client, judge.Cache(None), "m",
            max_pairs=5,
        )

        self.assertEqual([r["status"] for r in results], ["unavailable", "ok"])

    def test_the_number_of_judged_pairs_is_capped(self):
        client = FakeClient(good_answer())

        results = judge.judge_cards(
            self.cards * 3, self.graph, self.source, client, judge.Cache(None), "m", max_pairs=2
        )

        self.assertEqual(len(results), 2)
        self.assertLessEqual(len(client.calls), 2)


class OpenAIChatTest(unittest.TestCase):
    def client(self, *replies):
        self.requests = []
        queue = list(replies)

        def opener(request, timeout=None):
            self.requests.append(request)
            reply = queue.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply

        return judge.OpenAIChat(KEY, "the-model", opener=opener)

    @staticmethod
    def ok(content="{}"):
        body = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
        return io.BytesIO(body)

    @staticmethod
    def http_error(status, body):
        return urllib.error.HTTPError("u", status, "msg", {}, io.BytesIO(body.encode()))

    def test_the_request_has_the_model_messages_strict_schema_and_bearer_key(self):
        client = self.client(self.ok())

        client.complete("sys", "usr", judge.SCHEMA)

        request = self.requests[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.openai.com/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), f"Bearer {KEY}")
        self.assertEqual(body["model"], "the-model")
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])
        self.assertEqual(body["response_format"]["type"], "json_schema")
        self.assertTrue(body["response_format"]["json_schema"]["strict"])
        self.assertEqual(body["response_format"]["json_schema"]["schema"], judge.SCHEMA)
        self.assertIn("max_completion_tokens", body)

    def test_the_message_content_is_returned(self):
        client = self.client(self.ok('{"a": 1}'))

        self.assertEqual(client.complete("s", "u", judge.SCHEMA), '{"a": 1}')

    def test_an_http_error_reports_status_and_reason_but_never_the_key(self):
        client = self.client(self.http_error(401, f"Incorrect API key provided: {KEY}"))

        with self.assertRaises(judge.LLMError) as context:
            client.complete("s", "u", judge.SCHEMA)

        message = str(context.exception)
        self.assertIn("HTTP 401", message)
        self.assertNotIn(KEY, message)

    def test_a_model_not_found_error_keeps_the_api_message(self):
        client = self.client(self.http_error(404, '{"error": {"message": "The model `x` does not exist"}}'))

        with self.assertRaises(judge.LLMError) as context:
            client.complete("s", "u", judge.SCHEMA)

        self.assertIn("does not exist", str(context.exception))

    def test_a_rejected_token_limit_parameter_is_retried_without_it(self):
        client = self.client(
            self.http_error(400, "Unsupported parameter: 'max_completion_tokens'"), self.ok('{"ok": 1}')
        )

        content = client.complete("s", "u", judge.SCHEMA)

        self.assertEqual(content, '{"ok": 1}')
        self.assertNotIn("max_completion_tokens", json.loads(self.requests[1].data))

    def test_a_network_failure_is_an_llm_error_without_the_key(self):
        client = self.client(urllib.error.URLError("timed out"))

        with self.assertRaises(judge.LLMError) as context:
            client.complete("s", "u", judge.SCHEMA)

        self.assertIn("timed out", str(context.exception))
        self.assertNotIn(KEY, str(context.exception))

    def test_a_response_without_content_is_an_llm_error(self):
        client = self.client(io.BytesIO(b'{"choices": []}'))

        with self.assertRaises(judge.LLMError) as context:
            client.complete("s", "u", judge.SCHEMA)

        self.assertIn("no content", str(context.exception))


class CalibrationTest(JudgeTestCase):
    def golden(self, expected):
        return [{"first": "p.a", "second": "p.b", "expected": expected, "note": "x"}]

    def test_agreement_is_counted_per_reference_case(self):
        result = judge.calibrate(
            self.golden("duplicate"), self.cards, self.graph, self.source,
            FakeClient(good_answer()), judge.Cache(None), "m",
        )

        self.assertEqual((result["agree"], result["total"]), (1, 1))
        self.assertEqual(result["cases"][0]["got"], "duplicate")

    def test_disagreement_is_counted(self):
        result = judge.calibrate(
            self.golden("intentional"), self.cards, self.graph, self.source,
            FakeClient(good_answer()), judge.Cache(None), "m",
        )

        self.assertEqual((result["agree"], result["total"]), (0, 1))

    def test_a_reference_pair_that_is_not_in_the_graph_is_skipped(self):
        golden = [{"first": "p.x", "second": "p.y", "expected": "duplicate", "note": ""}]

        result = judge.calibrate(
            golden, self.cards, self.graph, self.source, FakeClient(good_answer()),
            judge.Cache(None), "m",
        )

        self.assertIsNone(result)

    def test_unavailable_answers_are_not_counted_as_disagreement(self):
        result = judge.calibrate(
            self.golden("duplicate"), self.cards, self.graph, self.source,
            FakeClient(judge.LLMError("HTTP 500")), judge.Cache(None), "m",
        )

        self.assertIsNone(result)


class GoldenFileTest(unittest.TestCase):
    def test_every_reference_case_is_well_formed(self):
        golden = json.loads(judge.GOLDEN_FILE.read_text())

        self.assertGreaterEqual(len(golden), 3)
        seen = set()
        for case in golden:
            self.assertIn(case["expected"], judge.VERDICTS)
            self.assertLess(case["first"], case["second"])  # cards order the pair this way
            self.assertTrue(case["note"])
            seen.add((case["first"], case["second"]))
        self.assertEqual(len(seen), len(golden))


class CommandLineTest(JudgeTestCase):
    def graph_dir(self):
        out = self.root / "graph"
        out.mkdir()
        (out / "nodes.csv").write_text(build.nodes_to_csv(self.graph))
        (out / "edges.csv").write_text(build.edges_to_csv(self.graph))
        (out / "externals.csv").write_text(build.externals_to_csv(self.graph))
        return out

    def run_main(self, out, *extra, env=None):
        return judge.main(
            ["--graph-dir", str(out), "--source-root", str(self.root),
             "--repo-url", helpers.REPO_URL, *extra],
            environ=env or {},
        )

    def test_without_an_api_key_the_judge_is_skipped_and_the_build_is_not_failed(self):
        out = self.graph_dir()

        status = self.run_main(out)

        self.assertEqual(status, 0)
        document = json.loads((out / "judgements.json").read_text())
        self.assertEqual(document["status"], "skipped")
        self.assertIn("OPENAI_API_KEY", document["reason"])

    def test_dry_run_writes_the_exact_prompts_and_makes_no_request(self):
        out = self.graph_dir()

        status = self.run_main(out, "--dry-run")

        self.assertEqual(status, 0)
        inputs = (out / "judge_inputs.md").read_text()
        self.assertIn("L3: func a() {", inputs)
        self.assertFalse((out / "judgements.json").exists())


if __name__ == "__main__":
    unittest.main()
