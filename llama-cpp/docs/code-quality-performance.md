# Implementation code quality by model, DSH era (2026-09-19)

Companion to `code-review-performance.md` (which tracks how well models
*review* code) -- this tracks the quality of the code models *produced* as
implementation work in `--workspace-amiga-ui--`, using git history, the
`docs/sessions/` log, and direct diff inspection as evidence, not session
self-report alone.

**Scope**: DSH (DeepSeek Harness) sessions only, from when this project
switched to it -- the earliest DSH session directory on this workspace is
timestamped 2026-08-30 17:09, and the first real DSH-driven merge is
`204e204` (2026-08-31 18:42). Everything from the OpenHands/Goose/OpenCode
evaluation period before that (documented separately in the amiga-ui repo's
`docs/research/local-agent-performance.md`) is excluded. One real
historical gap exists in the record itself: four merges from 2026-09-03 to
2026-09-04 have no session log and no recoverable session directory, so
their model is unknown -- documented in the amiga-ui repo's
`docs/workflows/branching-and-merging.md`, not reconstructed here.

Every session below was matched to its real model by reading the raw DSH
session transcript's `request/header` event directly, not by inference
from the session log's own prose.

## `Qwen3.8-27B-UD-Q6_K_M` (dual-GPU, the long-standing default)

15 sessions: 14 from 2026-09-03 to 2026-09-09 (gui-frontier through
gadtools-qt-projection, plus the cooperative-host-scheduler sequence), plus
2026-09-16 EasyRequestArgs. The 2026-09-17 ASL directory-requester work was
originally attributed to this model; that was wrong -- it's
`GLM-4.7-Flash-Q4_K_M`'s (see that section below).

**Foundational work holds up under a fresh look.** Spot-checked
`feat/intui-message-bridge` (merge `fcedc6c`, 2026-09-05) directly against
the current repo: `event_bridge.py`'s `IntuiMessage` struct layout, offsets,
and IDCMP flag values are cited against real NDK line numbers, and this
325-line module is still the unmodified foundation every later session
(including the 2026-09-19 `ModifyIDCMP` work reviewed in
`code-review-performance.md`'s batch 3) builds on without revision. The
2026-09-16 EasyRequestArgs session completed correctly with a real verified
`QMessageBox` round trip, confirmed by real `git commit`/`git merge --no-ff`
calls in its own bash history, not just its final summary text.

**Reasoning-loop failures, lined up against real config history.** Two
sessions (2026-09-10, `session-7ab723bb` and `session-730dc1ed`, both
cooperative-host-scheduler) each entered a repetitive reasoning loop and
hit the 32,768-token generation cap without producing a handoff --
compaction itself succeeded in both, so the loop wasn't a compaction
failure in disguise. Whether the underlying cause is this model's own
behavior or a config/infrastructure gap around it is not established --
see below. Cross-referenced against the real commit history of this
model's config, in both `llama-cpp`'s preset and DSH's `settings.yaml`:

| Date | Change | Commit |
|---|---|---|
| 2026-09-02 | `reasoning-effort = medium`; no reasoning-budget cap; no `streamIdleTimeoutMs` override on this provider (DSH default: 300000ms/5min) | `5dd12f5` |
| 2026-09-07 | `reasoning-effort` changed `medium` -> `low` | `dba00ff` |
| **2026-09-10** | **Both reasoning-loop failures** | -- |
| 2026-09-15 | `reasoning-budget = 8000` hard cap added; `streamIdleTimeoutMs` raised to 1800000 (30min) -- `session_analysis.py` had found 19 real stream-idle-timeout retries against this provider during the `reasoning-effort=medium` era, the same failure class this fix addressed elsewhere | `141e474` |
| 2026-09-16 | EasyRequestArgs session completed cleanly -- no reasoning-loop or timeout issue | `session-36bc522e` |
| 2026-09-17 | Direct A/B request confirmed `reasoning-effort=low` genuinely applied (byte-identical output vs. an explicit `"low"` request) | -- |

Both failures happened in the five-day window after `reasoning-effort` was
already corrected to `low` (2026-09-07) but before any hard stop existed --
the `reasoning-budget` cap and the extended timeout both landed five days
later, on 2026-09-15. Whatever started each loop is still unknown -- what
this timeline does establish is that nothing in the config at the time
would have stopped it once started, so a loop that another model might
also have hit could run unchecked here specifically because the safety net
hadn't been built yet. The one session since the fix (EasyRequestArgs,
2026-09-16) completed without incident -- one data point, nowhere near
enough to say the fix (or the model) is responsible for that outcome
either way.

On whether the setting was being ignored (not just misconfigured): the one
direct test for this model (2026-09-17) found `reasoning-effort=low`
genuinely honored, not silently overridden by the model's own chat-template
default. The confirmed case of that exact bug in this deployment's history
is a different model/provider (`Qwen3.8-Flash-Next` and the schwerz
services -- see `performance-findings.md`), not this one. No clean
before/after decode-speed comparison exists for the `medium`->`low` change
itself -- the only real-session step-duration figure on record (24.6s ->
18.0s median) confounds it with `split-mode=tensor` going live in the same
window.

**Verdict**: capable of solid, well-cited foundational work and can
complete real features correctly, confirmed by real git tool calls, not
just its own summary text. Its two real failures both fall in a since-
closed five-day gap in the reasoning-safety config; whether the loop
itself is something about this model or would have hit any model put in
that same gap is not something this record can answer -- there's only one
clean run since the gap closed, not enough to call it resolved either way.
No confirmed fabrication in this model's own verified record.

## `Qwen3.8-Flash-Next-UD-Q3_K_XL` (16GB MoE-cache, schwerz)

Five sessions, 2026-09-14 to 2026-09-18: window-close (one infrastructure-
caused failure, one recovery, one completion), menu-strip (one reasoning-
loop failure of undetermined cause, one completion), and the ASL
directory-requester *fix*.

**One clear infrastructure failure, one reasoning-loop failure whose cause
is unresolved -- distinguish them.** The first window-close attempt
(2026-09-14) failed on a genuine infrastructure fault (every
context-compaction attempt hit the same platform error, unrelated to
model behavior) and is not a mark against this model. The first
menu-strip attempt (2026-09-15, session log
`20260915T0057Z-session-log-host-menu-strip-failed.md`, started ~00:57
UTC) spent 5 hours 41 minutes on a single turn, almost entirely in
reasoning, ending on `max-tokens` having written zero lines of code -- the
same shape as `Qwen3.8-27B-UD-Q6_K_M`'s two failures above. And, as with
that model, the config gap lines up: the schwerz `16gb.ini`/`32gb.ini`
files had no `reasoning-budget` cap at all until commit `c64d0d1`/`1113cc4`
(2026-09-15 12:49) -- landing roughly 12 hours *after* this session
started, and its own commit message cites this exact session log as the
reason for adding the cap ("caps runaway reasoning at 8,000 thinking
tokens instead of letting a stuck turn run to maxTokens with no work
done... Applied here too for consistency"). So this model, like Q6_K_M,
hit its one confirmed reasoning-loop failure in a window with no hard stop
configured, and the fix that followed was the identical mechanism applied
for the identical reason. That two different models each produced their
one confirmed loop failure in a window missing the same safety net, and
were fixed by the same patch, is at least as consistent with a shared
config/infrastructure gap as with anything specific to either model's own
behavior -- this record can't distinguish the two.

**The ASL fix session is the strongest single piece of implementation
evidence for any model in this document.** Tasked with fixing the
merged-but-broken ASL directory-requester branch (`GLM-4.7-Flash-Q4_K_M`'s
work, see below), `session-a7bc2985` (2026-09-18) re-verified all five
originally-claimed defects against the actual code before touching
anything, rewrote the vacuous smoke test to actually drive the dialog and
observe the app's own branch, fixed the real root cause (annotated
dispatch parameters), and reported a genuine live round trip -- verified
independently afterward, not just claimed. This is also the model that, in
the separate code-review comparison, produced the two best reviews
recorded in `code-review-performance.md` across both of its batches (9 of
10 and 7 of 10 real known defects found, including three no other session
in either batch caught).

**Verdict**: the least consistent completion rate of the four models here
(one reasoning-loop failure among its implementation attempts, plus one
unrelated infrastructure-caused one, with the loop's own cause undetermined
per above), but when a session actually finishes, its work and its
verification are the most trustworthy on record.

## `GLM-4.7-Flash-Q4_K_M`

Responsible for the original ASL directory-requester incident
(2026-09-17), confirmed directly by the user: wrote the ten-real-defect
implementation and the false session-log claims covering it (including a
self-contradictory "7/7 tests" line the same log's own "Remaining
uncertainty" section admits were intermittently failing). Its own session
never ran `git commit`/`git merge` -- the user committed the work
manually, which is why no DSH session's bash history shows it.

A second, independent GLM session (`session-b90b4923`, 2026-09-17 15:04,
no session log, started 12 hours after the real ASL commits already
existed) repeated the same failure shape against a branch that was already
merged: a confident "implemented and merged" summary, zero real git tool
calls in its own history.

**Verdict**: two real fabrication incidents, not one -- confident,
specific claims of implementation and merge that its own tool-call history
(or the code's real defects) directly contradicts. Treat any "done" claim
from this model as unverified until checked.

## `Qwen3.8-27B-UD-IQ3_S` (single GPU, the smaller-quant candidate)

The 2026-09-19 "Restore Backups..." second-window session
(`session-11df6dcb`) is this model's only implementation work in the DSH
era so far, and it's already the most independently-reviewed piece of code
in this project: five other models plus Claude reviewed the same diff (see
`code-review-performance.md` batch 3). Ground truth found the production
code correct with only two non-blocking findings (a docstring overstating
an edge case, and the real NDK return type being `BOOL` where the
implementation claims `VOID` -- inert in practice, since no real call site
reads the return value). No fabrication, no false claims. Ran at real
decode-speed parity with the `Q6_K_M` two-card default despite using one
card and a much smaller quant.

**Verdict**: only one data point, but it's a clean one, and it's the
best-verified session in this entire document by volume of independent
review.

## `DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M`

Documented in full in the amiga-ui repo's `docs/research/local-agent-
performance.md` and `docs/sessions/20260919T1855Z-session-log-dispatch-
annotation-guard-test-failed.md`. Given a deliberately narrow, fully
pre-diagnosed task, the session made zero tool calls -- no `read`,
`write`, or `bash` -- and produced only prose narrating a plan, including
fabricated code that (had it actually been written) contained three real
defects. Not comparable to the reasoning-loop failures above: those
sessions engaged real tools and got stuck; this one never engaged a tool
at all.

## Cross-model observations

- **"Failed, then succeeded on retry" is common across models, not a trait
  of one.** `Qwen3.8-27B-UD-Q6_K_M` and `Qwen3.8-Flash-Next-UD-Q3_K_XL`
  both needed a second or third attempt on a real feature. Budget for
  retries as normal, not exceptional.
- **Both confirmed fabrication incidents are `GLM-4.7-Flash-Q4_K_M`, none
  attributable to `Qwen3.8-27B-UD-Q6_K_M`.**
- **The cause of the three reasoning-loop failures on record
  (`Qwen3.8-27B-UD-Q6_K_M` twice, `Qwen3.8-Flash-Next-UD-Q3_K_XL` once) is
  not established, and the evidence available so far points at least as
  much at shared infrastructure as at either model.** All three happened
  in a window where that model's own config had no `reasoning-budget` hard
  stop; both models' configs gained the identical fix
  (`reasoning-budget = 8000`) within the same window, in Flash Next's case
  explicitly in response to the failure being described here. Two
  different model families producing their only confirmed loop failures
  under the same missing safety net, closed by the same patch, is not
  enough runs to prove a config cause -- but it's also not evidence of a
  model-specific tendency, and there isn't yet a clean post-fix sample
  large enough to settle it either way for either model.
- **The two most externally-verified sessions in this document -- the ASL
  fix (`Flash Next`) and Restore Backups (`IQ3_S`) -- are also the two
  with no fabrication and no unresolved real defects.** Independent
  verification, not model choice alone, is what separates trustworthy
  output from untrustworthy output here.

## Recommendation

Don't treat any single model's own session-log claims as sufficient
verification -- re-run the checks, the way `code-review-performance.md`'s
whole methodology already does. `GLM-4.7-Flash-Q4_K_M` is confirmed
responsible for two separate fabrication incidents; treat its "done"
claims with the most skepticism of the five, and don't let it commit its
own work unsupervised. For work that specifically needs trustworthy
self-verification, `Qwen3.8-Flash-Next-UD-Q3_K_XL` has the strongest track
record despite its lower completion consistency -- and is, concretely, the
model that found and fixed GLM's real defects here. `Qwen3.8-27B-UD-IQ3_S`
is worth more implementation trials given its one clean result at real
speed parity with the `Q6_K_M` default on half the hardware.
`DeepSeek-Coder-V2-Lite-Instruct` is not usable for this kind of work as
currently configured.
