---
linear_issue: TBD
status: proposed
---

# Contract go-route-safety: Safer To Act On

> No Linear ticket exists yet, so no `MPI-NN` code (see `docs/repository-guidance.md`).
> Builds on `docs/contracts/go-route-story.md` (PR #19).

## Context
User feedback on PR #19: delete the package diagram ("Packages (cross-package call sites)");
make each section collapsible with a short description so a dev opens what they need; the
diagrams are readable. The open question is whether the suggested fix is good and avoids
regressions. First step, agreed: after the fix, show the dev the **blast radius** and whether
**more tests are needed**, as two or three lines on the card, with the evidence behind a
dropdown, and only for cards that are on the surface (action != keep). All computed by code
from the graph and the source, not by the model.

## 1. Current state
```
summary: header, "### Redundant routes" (cards), "### Dead-code candidates", package diagram,
         "### Package totals", "### Most used external functions", most called / calls out /
         never called tables, All functions / All call sites in <details>.
card: problem, verdict, diagram 1, fix, diagram 2, maybe-intentional, dropdowns
      (Evidence | Routes and entry points | LLM details)
```

## 2. Target state (+ = new)
```
summary: header, then collapsible sections, each  <details><summary><b>Title</b> - one-line
         description</summary>:
           Redundant routes (OPEN by default)     Dead-code candidates (N)
           Package totals                         Most used external functions
           Most called functions                  Most calls out
           Never called (entry points or unused)  All functions | All call sites (already <details>)
         package diagram and package_mermaid() deleted
card (surface cards with a fix only):
   ... fix, diagram 2, stays line
   Before you change this                         <- NEW, 2-3 lines
     - Blast radius: callers of each function (via interface or direct), exported or not
     - Tests: tests found per function; possible gap = a test one function has and the other
       lacks, found by comparing test names with the function names removed
   Maybe intentional because: ...
   dropdowns: Safety check details (NEW) | Evidence | Routes and entry points | LLM details
     Safety check details: what differs inside the steps called "the same" (these become the
     parameters of a shared function), full caller list with links, tests found with links

+tools/callgraph/safety.py   pure functions, no LLM:
   blast_radius(graph, function_id) -> callers [{id, file, line, resolution}], exported, via_interface
   find_tests(root, scope_dir, node) -> [{name, file, line}]   tests whose body mentions the
       function (or its receiver type for a method); only *_test.go under the graph's scope dir
   test_gaps(tests_a, tests_b, name_a, name_b) -> names one function has and the other lacks,
       after removing the function/type names from each test name (Go: TestOpenAIAnnotator<Does>)
   step_differences(lines_a, lines_b, steps) -> [{step, kind: type|identifier|string, a, b}]
       token diff of each step marked "same"; renamed receiver identifiers are grouped
render.py: section helper, safety block + dropdown (needs source root, already passed)
```
Data flow: judgement (steps, fix) + graph + source -> safety.* -> card. Without source access the
block shows blast radius only and says tests were not checked.

## 3. Definitions and honesty rules
- **Blast radius**: direct callers from graph edges (static or dynamic) plus whether the function
  is exported. It does NOT claim signature compatibility (the graph has no signatures); wording
  says "callers that depend on current behaviour".
- **Test gap is a heuristic by test name**; it is worded "no counterpart by name", never
  "untested". Tests found by naming or mention may still not cover the behaviour. If neither
  function has tests: "no tests found for either: add tests before changing".
- **Differences inside "same" steps** are exact token differences (renamed receivers collapsed
  to one line). They are facts about the code; whether the model's fix parameterises them is not
  checked (listed as "a shared function must take these").
- Folded cards (action keep) and un-judged cards get no safety block.

## 4. Commits (test-first; red shows failure, green must not weaken it)
1. `docs`: contract.
2. `test`: safety.py - callers incl. dynamic and exported, find_tests (function, method via
   receiver type, ignores non-test files and other packages' unrelated names), test_gaps
   (parallel names, no tests, one-sided), step_differences (type, identifier, string, receiver
   rename grouped, identical step -> none) - red.   3. `feat`: safety.py.
4. `test`: render - collapsible sections with descriptions, Redundant routes open and others
   closed, every <details> closed, package diagram absent, package totals kept inside a section,
   safety block position and wording, details dropdown, no block for folded/unjudged cards,
   source-less fallback. By-design changes to existing tests: section splits on "### ..." become
   summary-line markers; `package_mermaid` tests and the "only the package diagram" test are
   removed/updated; label tests call `_package_labels` directly - red.   5. `feat`: render.py.
6. `docs`: README + results in the contract.

Reuse: `render._Names`, `_Files`, `_text`, `source_url`, `_step_refs`, `_fix`, `_dropdowns`
(tools/callgraph/render.py); `diagrams.step_reference`; `build.Graph` edges with `resolution`;
`helpers.make_graph` (tests/helpers.py).

## 5. Verification plan
Automated: `python -m unittest discover -v -s tools/callgraph/tests -t .`; `ruff check tools`;
CI run on #19.
Real data (importer), checked against what I read earlier by hand:
- callers: Annotate <- annotateOne (via interface), Extract <- extract (via interface);
- tests by name: Annotate has `ParsesStructuredResponse` and `RedactsAPIKeyOnTransportFailure`,
  Extract only `ParsesStructuredResponse` -> gap "RedactsAPIKeyOnTransportFailure"; I re-read
  transcript/openai_test.go to confirm no differently named redaction test exists;
- differences in the "same" steps: result type (ClaimAnnotation vs StructuredExtraction),
  receiver fields (annotator.* vs extractor.*), error labels ("annotation" vs "extraction"),
  matching my manual diff.
Structure: count of <details> equals </details> in the summary; headings/diagrams still parse;
summary size stays well under 1 MiB. I cannot see GitHub's rendering of collapsed sections, so
the user is asked to look at the Summary tab.
Exit criteria: tests green; real-data safety output equals my hand check or the difference is
explained; no card claims a signature or test-coverage fact the code cannot know.

## 6. Defaults (change on request)
- "Package totals" stays but inside a collapsed section; only the diagram is deleted.
- Redundant routes is the only section open by default.
- Test search is limited to the graph's scope directory (here services/importer).
