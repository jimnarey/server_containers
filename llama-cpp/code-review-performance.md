# Code-review performance: model comparison (2026-09-17)

Seven DSH sessions on `--workspace-amiga-ui--`, run back-to-back today
between 10:56 and 14:31 UTC, each asked a model to review branch
`feat/host-asl-directory-requester` (the GLM-4.7-Flash-implemented ASL
directory picker, already merged to `development`). An eighth, currently
running session was excluded. All seven ran through the plain `llama-cpp`
GPU router (port 11436) -- one or two GPUs depending on the model, not the
CPU or MoE-cache services. Source: `session_analysis.py` against an isolated
copy of just these seven `session.jsonl.zstd` files, plus direct
reconstruction of each session's final review text from the raw log.

Three models were tested: `Qwen3.8-27B-UD-Q6_K_M` (dual-GPU, tensor-split,
one attempt), `NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0` (dual-GPU, three
attempts), `gpt-oss-20b-F16-1gpu` (single GPU, three attempts).

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

## Recommendation

For a review meant to actually gate a merge decision, none of the three
faster sessions here would have caught the branch's worst bug or reached the
correct verdict -- only the ~3.2-hour Qwen3.8-27B-UD-Q6_K_M pass did, and it
did so by verifying claims against external ground truth (the NDK headers,
the compiled binary, and live test re-runs) rather than reading the Python
source in isolation. Nemotron and gpt-oss-20b-F16-1gpu are fast enough for a
same-minute first-pass triage and did surface some real, correctly-described
issues (notably F2, independently, in their best runs), but their verdicts
should be treated as a second opinion to sanity-check, not a gate, until
something closes the gap between "found a real bug" and "still says the
branch is merge-ready anyway."
