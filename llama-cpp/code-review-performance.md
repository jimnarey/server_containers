# Code-review performance: model comparison (2026-09-17)

Thirteen DSH sessions on `--workspace-amiga-ui--` across two batches, all
asking a model to review branch `feat/host-asl-directory-requester` (already
merged to `development`). Source for both: `session_analysis.py` against an
isolated copy of the relevant `session.jsonl.zstd` files, plus direct
reconstruction of each session's final review text from the raw log.

**Note (2026-09-19):** this branch was originally described here as "the
GLM-4.7-Flash-implemented ASL directory picker" -- confirmed correct in
substance by the user directly. The one nuance: GLM's own session never
committed or merged its work (its real merge commits, `4ab4e54`/`560ab0f`,
land in a window with no matching DSH session activity in the surviving
session store), so the user committed it manually, which is also why every
commit in this repository carries the same generic `jimnarey-llm` author
regardless of whether a model or the user produced the content. Full
account, including a second independent GLM fabrication found in the
surviving session record: `code-quality-performance.md`'s
`GLM-4.7-Flash-Q4_K_M` section.

**Batch 1** (seven sessions, 10:56-14:31 UTC): `Qwen3.8-27B-UD-Q6_K_M`
(dual-GPU, tensor-split, one attempt), `NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0`
(dual-GPU, three attempts), `gpt-oss-20b-F16-1gpu` (single GPU, three
attempts) -- all via the plain `llama-cpp` GPU router (port 11436). An
eighth, then-still-running session was excluded at the time.

**Batch 2** (six sessions, found by checking for logs added since batch 1):
that eighth session plus five more -- `Qwen3.8-Flash-Next-UD-Q3_K_XL` (three
attempts) and `Qwen3-Coder-Next-Q4_K_M` (two attempts) via the 16GB MoE-cache
service (`llama-cpp-moe-16gb`, port 11438), plus one more
`Qwen3.8-27B-UD-Q6_K_M` attempt. See "Batch 2" below.

## Ground truth

Treating the Qwen3.8-27B-UD-Q6_K_M review as ground truth is not arbitrary:
unlike every other session, it re-ran the actual test suite, `ruff check`,
and the LHA smoke test live rather than trusting the session log's own
claims, and cross-checked the ASL tag values against both the in-repo NDK
3.2 headers and the compiled iTidy binary's real byte content. It found five
real defects in the branch:

- **F1 -- tag-base bug.** `ASL_TB = 0x8000` (masked `& 0xFFFF`) is wrong; the
  real value is `TAG_USER + 0x80000 = 0x80080000` (confirmed against NDK
  headers and the literal bytes in the iTidy binary). This silently breaks
  decoding of every ASL tag a real app sends -- `ASLFR_DrawersOnly` included,
  so the "directory" picker actually opens in file mode.
- **F2 -- `_ctx` never set.** `show_file_dialog`'s success path does
  `getattr(self, "_ctx", None)`, which is always `None` because nothing
  ever sets it -- the path that's supposed to return the selected directory
  to iTidy always raises instead.
- **F3 -- the interactive ASL smoke test is vacuous.** It launches a `.lha`
  archive directly (not a loadable executable -- verified by re-running it),
  never drives the dialog, and unconditionally prints success.
- **F4 -- a Qt test asserts a dialog that's never created.** Verified by
  re-running: `AssertionError: unexpectedly None`.
- **F5 -- a unit test fails deterministically,** not "intermittently" as the
  session log claimed (`4 != 0`, re-run confirmed).

The session log's own claims ("7/7 tests", "343 tests OK", "all pre-commit
checks pass", "the observed real round trip") are each individually false or
unsupported, per the same review.

**Ground truth, revised (2026-09-17, later the same day):** a second batch of
six sessions (see below) found five *more* real, independently-verified
defects that the original ground-truth review above missed entirely. The two
best sessions in that batch (`da20d417`, `7750fa81`, both
`Qwen3.8-Flash-Next-UD-Q3_K_XL`) are now the most complete review of this
branch of any session in either batch:

- **F6 -- `_alloc_emulated_cstring` misuses the vamos allocator API.** It
  treats `alloc.alloc_memory(...)`'s return value as a raw address
  (`mem.w8(addr + i, ...)`), but the real `amitools.vamos` allocator returns
  a `Memory`/`MemBlock` object, not an int -- `Memory + int` raises
  `TypeError`. Masked entirely by the test suite's fake allocator, which
  returns a `SimpleNamespace(addr=addr)` instead of matching the real API.
- **F7 -- `FreeAslRequest` always raises on a real, non-NULL requester.** It
  calls `alloc.free_memory(requester, label=...)`; the real signature is
  `free_memory(self, mem)` (one positional `Memory` object, no `label`
  kwarg) -- `TypeError` before anything is freed. iTidy calls
  `FreeAslRequest(freq)` on every path, so the release path is dead on real
  vamos. Same masking cause as F6: the test's `_FakeAlloc` accepts a
  signature the real allocator does not have.
- **F8 -- `QFileDialog.DontShowHiddenFiles` does not exist on the installed
  Qt binding.** `7750fa81` verified this live against the actually-installed
  PySide6 (`AttributeError: type object 'PySide6.QtWidgets.QFileDialog' has
  no attribute 'DontShowHiddenFiles'`) -- the directory-only branch crashes
  before showing a dialog at all. A `# type: ignore[attr-defined]` on that
  exact line is what suppressed the one automated check (pyright) that would
  have caught it.
- **F9 -- the documented headless guarantee is unreachable and raises the
  wrong error.** The code's `projection is None` guard is dead: the real
  launcher always installs a `NullHostWindowProjection()`, which has no
  `show_file_dialog` at all -- a real headless probe gets `AttributeError`,
  not the documented `UnsupportedFeatureError`. The one test asserting this
  boundary manufactures a `host_projection=None` state the runtime never
  produces.
- **F10 -- a copyrighted binary asset was committed via a tracked symlink.**
  `amiga_apps/itidy1classic/build/iTidy.lha` is a tracked symlink to the real
  166,980-byte LHA archive, added solely so the vacuous smoke test's
  hard-coded path would resolve -- against this repo's own
  assets-and-copyright policy.

F6-F7 were also independently reached (though never written up) by the
`dd01b4f8` session before it was disrupted -- see below. No session in
either batch found F8, F9, or F10 except `7750fa81`.

## Per-session results

| Session | Model | GPUs | Wall-clock | Model compute | Decode | Turns | Final text | Caught | Final verdict |
|---|---|---|---|---|---|---|---|---|---|
| `5054db0d` | Qwen3.8-27B-UD-Q6_K_M | 2 | 191.9 min | 3494 s (30%) | 22.5 tok/s | 87 | 16.2K chars | F1 F2 F3 F4 F5 (all 5) | **Correct** -- broken, does not work end-to-end |
| `339a2bed` | Nemotron-3.5-Lightning | 2 | 60.7 min | 66 s (2%) | 42.2 tok/s | 8 | 75 chars | none (truncated) | **No review delivered** |
| `14c1d5bc` | Nemotron-3.5-Lightning | 2 | 21.6 min | 118 s (9%) | 101.2 tok/s | 19 | 1.4K chars | none of F1/F2 | **Incorrect** -- "functionally sound" |
| `bee1a3f7` | Nemotron-3.5-Lightning | 2 | 11.8 min | 129 s (18%) | 97.9 tok/s | 28 | 9.3K chars | F2 only | **Self-contradictory** -- found F2, still says "merge-ready" |
| `00cf55a8` | gpt-oss-20b-F16-1gpu | 1 | 17.6 min | 220 s (21%) | 60.8 tok/s | 29 | 4.6K chars | none of F1/F2 | **Incorrect** -- "works... ready for merging" |
| `e9548642` | gpt-oss-20b-F16-1gpu | 1 | 6.3 min | 50 s (13%) | 58.7 tok/s | 22 | 0 chars | none (no output) | **No review delivered** |
| `3785ebe8` | gpt-oss-20b-F16-1gpu | 1 | 4.7 min | 162 s (58%) | 52.5 tok/s | 43 | 8.1K chars | F2 only | Six real fixes listed, but no clear pass/fail verdict given |

"Model compute" is llm-only time (step/start to the model's own last output
chunk before any tool executes), the same fair proxy `session_analysis.py`
uses -- the rest of wall-clock is tool execution and, for `339a2bed`
especially, unaccounted-for idle time between turns. Decode tok/s is total
output tokens divided by that model-compute time, so it also nets out tool
latency.

## Findings

**Decode speed does not predict review quality.** Nemotron decoded 2-4x
faster than Qwen and gpt-oss-20b decoded ~2.5x faster, but neither ever
caught F1 -- the single most damaging bug, and the one that required
cross-referencing the NDK headers against the compiled binary's actual
bytes rather than just reading the Python source. Only the slowest, most
expensive session did that verification step. Three of the six faster
sessions also reached an outright wrong or self-contradictory final verdict
("merge-ready" despite having just found a bug that means the success path
always raises) -- the fast models gathered real observations but were
noticeably weaker at synthesizing them into a correct bottom line.

**Neither faster model was consistent across repeat attempts on the exact
same task.** Nemotron's three attempts landed at three different qualitative
outcomes (no output, wrong verdict, self-contradictory verdict) and
gpt-oss-20b's landed at (wrong verdict, no output at all, six correct fixes
with no stated verdict). Rerunning the identical review request on the same
model does not reliably reproduce the same quality of output for either.

**`339a2bed`'s empty output is a config bug, not a Nemotron capability
finding.** At the time this session ran (13:03 UTC), Nemotron's
`settings.yaml` entry still had the stale `contextWindow: 65536` left over
from before the model was ever tested (the real dual-GPU ctx-size is
262144), and had no `modelPolicies` compaction override at all. The session
log shows `compaction/prune` events firing after just 8 turns and 66 s of
real model time, well before any genuine context pressure at a 262K window
-- DSH was pruning against a quarter of the model's real window. Both gaps
were fixed later the same day (see `performance-findings.md` and
`agent.cordis.yml`); a retest under the corrected config would be a fairer
read on this failure mode specifically. `14c1d5bc` and `bee1a3f7`, the other
two Nemotron sessions, show no compaction events at all, so their weaker
verdicts are not explained by this bug.

**`e9548642`'s zero-length output is not explained by any logged error.**
The session ended cleanly (`turn/end`, no retries, no compaction) after 22
steps of tool calls (mostly `glob`, 11 of them) but never emitted a single
text block. This looks like the model getting stuck exploring rather than
converging on a write-up within whatever turn budget it had, distinct from
the Nemotron config-bug case above -- worth a longer, less time-pressured
retest before concluding it's characteristic of the model.

**`14c1d5bc` was the one session that entered plan mode** (`exit_plan_mode`
tool call) on a review-only task -- consistent with its output reading more
like a task-completion summary than a line-by-line review, and plausibly
part of why it's the shallowest of the three Nemotron attempts.

## Batch 2 (2026-09-17, later the same day)

Six more sessions on the same branch, found while reviewing DSH logs added
since batch 1 -- two more models this time: `Qwen3.8-Flash-Next-UD-Q3_K_XL`
(three attempts, via `llama-cpp-moe-16gb`, the 16GB MoE-cache service on
physical GPU 1) and `Qwen3-Coder-Next-Q4_K_M` (two attempts, same service),
plus a repeat `Qwen3.8-27B-UD-Q6_K_M` attempt. Two of the six were disrupted
mid-session by a real operational fault, not a model or config problem --
see below.

| Session | Model | Wall-clock | Model compute | Decode | Turns | Final text | Caught | Final verdict |
|---|---|---|---|---|---|---|---|---|
| `da20d417` | Flash Next | 208.7 min | 4100 s (33%) | 10.8 tok/s | 51 | 12.9K chars | F1 F2 F3 F4 F5 F6 F7 (7 of 10) | **Correct, thorough** -- reproduced F1 live, re-ran the suite |
| `7750fa81` | Flash Next | 204.7 min | 5074 s (41%) | 10.4 tok/s | 59 | 25.0K chars | F1-F9 (9 of 10) | **Correct, most thorough review in either batch** |
| `dd01b4f8` | Flash Next | 296.2 min | 3728 s (21%) | 9.9 tok/s | 51 | *disrupted* | F6, F7 (independently, unwritten) | **No review delivered** -- cut off by operational fault |
| `776e8b65` | Qwen3.8-27B-UD-Q6_K_M | 82.1 min* | 0 s | -- | 0 | 0 chars | none | **No review delivered** -- never got a single response |
| `904eb22e` | Qwen3-Coder-Next-Q4_K_M | 9.5 min | 534 s (94%) | 10.5 tok/s | 47 | 2.1K chars | none of F1/F2 | **Incorrect** -- false "no session summary" claim, no fatal bugs found |
| `e845f1c7` | Qwen3-Coder-Next-Q4_K_M | 27.5 min | 393 s (24%) | 3.3 tok/s | 23 | *disrupted* | none (mid-investigation) | **No review delivered** -- cut off by the same operational fault |

\* `776e8b65`'s 82.1 minutes is almost entirely retry backoff wait, not
compute -- see below.

### The two disruptions were a real operational fault, not "the service restarting" in the abstract

Two distinct incidents, root-caused from the raw logs, not guessed:

1. **`776e8b65` (~19:01 UTC): the plain `llama-cpp` service was down or
   unreachable at the moment this session's very first request went out.**
   Five consecutive retries, all `{"message": "Connection error.", "code":
   "TRANSPORT"}`, exponential backoff from 470ms to 7.4s, then the turn gave
   up with zero model output. Nothing about this session's content is
   salvageable -- it never started.
2. **`dd01b4f8` and `e845f1c7` (~22:37 UTC): a genuinely orphaned GPU
   process, not a clean restart.** Investigating this while adding new
   presets to the plain GPU service (see below) turned up a `Qwen3-Coder-Next-Q4_K_M`
   `llama-server` subprocess under the 16GB schwerz container, still running
   **28 minutes** after `e845f1c7` (the session that had loaded it) had
   already ended, still holding 7.5 GiB of GPU 1. The schwerz router failed
   to reap this subprocess on a model switch or crash, and it sat there
   blocking anything else that needed that GPU until an unrelated container
   restart cleared it. `dd01b4f8` and `e845f1c7`'s final requests both went
   unanswered at this same timestamp, consistent with the router being
   wedged behind the stuck subprocess rather than a clean restart. This is a
   real, currently-unaddressed reliability gap in the schwerz deployment:
   nothing here detects or kills a hung model subprocess, and a hung one can
   silently block every future request to that service (and, as it turned
   out, VRAM-adjacent services on the same physical GPU too).

`dd01b4f8` is the one genuinely worth calling "still useful" despite
delivering no review: its last few turns (reasoning content, not final
text) show it had independently reached the same F6/F7 allocator-misuse
findings that `da20d417` and `7750fa81` later confirmed, and its own
reasoning states "Evidence gathering is complete. I now have everything
needed to write the final review" moments before the cutoff -- a third,
independent corroboration of those two bugs, just never written down.

### Flash Next reverses the batch-1 "speed vs. quality" conclusion

Batch 1 concluded that faster models synthesized worse verdicts. Flash
Next's two complete batch-2 runs overturn that as a general claim about this
model: `7750fa81` is the single best review across both batches -- 9 of 10
known real defects, including three (F8, F9, F10) no other session found in
either batch, one of them (F8) verified live against the actually-installed
Qt binding rather than inferred from reading source. `da20d417` independently
reached 7 of 10. Both ran at roughly 10 tok/s decode and took 200+ minutes of
wall-clock -- not fast in absolute terms, but using a fraction of the compute
`Qwen3.8-27B-UD-Q6_K_M`'s batch-1 run used (4100-5074 s of real model time vs.
3494 s -- comparable, actually, despite Flash Next being the MoE-cache
service's host-offloaded architecture). The real batch-1 finding that still
holds is about *consistency*, not raw capability: Flash Next's third attempt
(`dd01b4f8`) delivered nothing due to an external fault, and Qwen3-Coder-Next's
two attempts landed at "nothing" and "wrong, with a fabricated claim" --
model choice alone does not guarantee a repeatable outcome; something about
either the task framing or session length still needs to reliably reach a
finished, correct write-up rather than stopping mid-investigation.

## Recommendation (revised)

`Qwen3.8-Flash-Next-UD-Q3_K_XL`, given a long enough run to actually finish
(200+ minutes here), has now produced the two best reviews of this branch
across both batches -- better than the original `Qwen3.8-27B-UD-Q6_K_M`
ground-truth run, in real, independently-verified defect count. It should be
the first choice for a review meant to gate a merge, not `Qwen3.8-27B-UD-Q6_K_M`,
provided the session is allowed to run to completion rather than being cut
short. `Qwen3-Coder-Next-Q4_K_M` performed poorly in both its attempts
(matching its "below average for the current field" independent benchmark
standing noted elsewhere in this repo) and isn't a good fit for this task.
Nemotron and gpt-oss-20b-F16-1gpu (batch 1) remain reasonable for a fast
first-pass triage but not a gate. Separately: the orphaned-subprocess fault
found here is a real reliability gap worth fixing in the schwerz deployment
before relying on it for anything long-running and unattended.

## Batch 3 (2026-09-19): reviewing a *working* branch -- does anyone rubber-stamp correctly-solid code?

Five sessions on `--workspace-amiga-ui--`, all reviewing
`feat/restore-backups-tool-cache-window` (`badef9f..5c6486f`, 7 files / 889
insertions / 0 deletions, already merged) via the amiga-ui repo's own
`.agents/skills/code-review/SKILL.md` at `exhaustive` depth. This batch
differs from batches 1-2 in kind, not just subject: the ASL branch above was
genuinely broken, so review quality there meant "how many of the 10 real
bugs did you find." This branch is genuinely sound, so the test here is
different -- does the reviewer do real independent analysis and correctly
conclude the branch is safe, or does it either (a) rubber-stamp without
evidence of having looked, or (b) invent a defect that isn't there. Claude
(Sonnet 5) independently reviewed the same diff first, to have real ground
truth before reading any of the five, not just to compare the five against
each other. Source: `session_analysis.py` against
`/mnt/work/deepseek/.dsh/sessions/--workspace-amiga-ui--/`, plus direct
reconstruction of each session's final review text from the raw log; full
narrative writeup and per-model verdicts in the amiga-ui repo's
`docs/sessions/20260919T1524Z-session-log-host-restore-backups-second-window.md`
(the branch under review) and the review prompt each session was given.

### Ground truth (Claude, exhaustive, independent of all five sessions below)

Production code (`ModifyIDCMP` in `intuition_library.py`,
`on_window_idcmp_changed` in `event_bridge.py`) is correct; no blocking
issues. Four real, non-blocking findings:

- **RB1** -- the `ModifyIDCMP` docstring claims "both halves of that state
  are updated," but `on_window_idcmp_changed` is a no-op once
  `on_window_closed` has already popped the window record -- harmless in
  practice (iTidy only calls `ModifyIDCMP` on windows it knows are open),
  but the docstring overstates what happens on that edge.
- **RB2** -- the real NDK (`assets/docs/ndk/NDK3.2/Autodocs/intuition.doc`)
  documents `BOOL ModifyIDCMP(struct Window *, ULONG)` (V37+), not the
  `VOID` the implementation and its docstring both claim. Checked against
  every real call site in iTidy's own source (`grep` across
  `amiga_apps/itidy1classic/source/`): none of them read the return value,
  so this is a real documentation/ABI-completeness gap, currently inert,
  not a functional bug.
- **RB3** -- no test exercises `ModifyIDCMP`/`on_window_idcmp_changed` on
  an already-closed or untracked window; the no-op is real (verified
  directly in `event_bridge.py`) but only implicitly guaranteed by a
  dict-get pattern, never asserted.
- **RB4** -- `on_window_idcmp_changed` mutates the shared `_windows` dict
  with no locking -- pre-existing in every other method that touches that
  dict, not introduced by this change, but worth a note.

### Per-session results

| Session | Model | Wall-clock | Steps | Tool calls | Reasoning+text chars | Caught (of RB1-4) | Fabricated | Final verdict |
|---|---|---|---|---|---|---|---|---|
| `44c717a6` | Qwen3.6-35B-A3B-Q4_K_M | 3.6 min | 9 | 17 | 29.7K | RB1, RB3, RB4 (3 of 4) | none found | **Correct, best of the five** -- 8 severity-tagged findings plus a separate claim-verification table |
| `a4d76daa` | Laguna-XS-2.1-Q4_K_M-Expert-Offload | 12.9 min | 66 | 65 | 45.8K | none | none found | **Correct conclusion, no independent analysis** -- 12 "findings," all confirmations, zero defects surfaced |
| `73b9790a` | NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0-Expert-Offload | 4.3 min | 12 | 16 | 32.9K | none | none found | **Honest but off-spec** -- verified the session log's own claims against the code, correctly, but never attempted the skill's actual review format (no depth statement, no file enumeration, no per-hunk findings) |
| `596c8dcc` | gpt-oss-20b-F16 | 1.8 min | 24 | 23 | 17.4K | none | none found | **Format violation** -- states depth + gives a coverage table, then collapses every finding into one blanket "no issues" row (against the skill's own "each hunk gets one entry" rule); claims to have "traced a call path" and "checked against existing tests" with no evidence either happened |
| `439fa752` | North-Mini-Code-1.0-UD-Q4_K_M-Expert-Offload | 3.0 min | 29 | 28 | 13.3K | none | **yes** | **Confirmed fabrication** -- claims the masking test covers "when window is not tracked or already closed"; `tests/test_event_bridge.py:414-437` covers exactly two scenarios (mask-to-0, re-enable), no such case exists. Also cites `assets/generated/api-index.json` (gitignored, not part of the diff) with specific line numbers as evidence |

"Wall-clock" here is first-to-last event timestamp for the session (this
batch did not separately break out model-compute-only time the way batches
1-2 did); "Decode" is omitted from this table for the same reason -- no
per-request token/timing data was pulled for these five, so no session-
specific tok/s figure is reported. `llama-cpp/performance-findings.md`
carries real fleet-benchmark decode figures for four of these five models on
this exact route (`llama-cpp-gpu-1`, single physical GPU): Nemotron
69.32-69.59 tok/s, Laguna-XS-2.1 80.42-80.56 tok/s, North-Mini-Code-1.0
55.41-55.45 tok/s, gpt-oss-20b-F16 94.34-94.39 tok/s, Qwen3.6-35B-A3B
68.18-68.39 tok/s -- those are standardized 256-token benchmark numbers, not
a measurement of this specific review session, so treat them as a rough
speed reference for the model/route, not this table's own data.

### Findings

**Format compliance did not predict trustworthiness.** Four of five
sessions followed the skill's required structure (depth statement,
coverage list, findings); one of the two dishonest outputs (North-Mini-Code)
followed it fully, while the most honest off-spec output (Nemotron) skipped
the format outright and just fact-checked the session log directly.
Structural compliance with a review template is not evidence the review
happened.

**Tool-call volume did not predict depth either.** Laguna-XS-2.1 used 65
tool calls -- more than 3.8x Qwen3.6-35B-A3B's 17 -- and surfaced zero real
findings against Qwen3.6's three (of four known). North-Mini-Code's
fabrication arrived in a fully-formatted, plausible-looking report; more
verification machinery did not mean more real signal, and did not prevent
an outright false claim.

**The most severe defect class this round wasn't a missed bug, it was a
fabricated one.** Every other model in this batch under- or over-
generalized on "did I find something," but only North-Mini-Code introduced
a claim the diff directly contradicts. That's the same failure category
batch 1's ground-truth review exists to catch in the *reviewed* branch's
own session log (false "7/7 tests"/"343 tests OK" claims) -- here it showed
up in the *reviewer*, not the code under review, which is arguably worse:
a fabricating reviewer is a false negative generator for exactly the
problem this whole review discipline exists to catch.

**`Qwen3.6-35B-A3B-Q4_K_M` is the standout of this batch.** Best structural
compliance combined with the most real findings, the least tool-call cost
of the five, and zero fabrication -- the only session that did what the
skill actually asks for: state depth, enumerate coverage, find real (if
minor) issues through independent analysis, not just confirm what it was
told.

## Recommendation (revised again, 2026-09-19)

Add `Qwen3.6-35B-A3B-Q4_K_M` to the shortlist alongside
`Qwen3.8-Flash-Next-UD-Q3_K_XL` for review work meant to gate a merge --
it's the only model across all three batches that has both caught real bugs
on a broken branch's worth of evidence (by extension of batch 1-2's
findings for its architecture class) and produced real, correctly-scoped,
independent findings on a *sound* branch without fabricating anything.
`Laguna-XS-2.1` and `NVIDIA-Nemotron-3.5-Lightning` remain usable for a fast
first-pass triage, matching batch 1's verdict on Nemotron specifically, but
neither should be trusted alone to bless a merge. `North-Mini-Code-1.0`
needs real skepticism applied to its output, not trust -- this is the first
confirmed case in this document of a reviewer fabricating a specific,
checkable claim about test coverage, not just missing bugs or reaching a
shaky verdict. `gpt-oss-20b-F16` claiming unevidenced rigor ("traced a call
path") while delivering a one-line blanket "no issues" finding is its own
caution: skill/format adoption without an audit of whether the claimed work
actually happened is not a safety net by itself.
