# Code-review performance: model comparison

This is a model-by-model summary of observed code-review performance. It is
not a chronological session log: individual review rounds are evidence for a
model's strengths, blind spots, delivery reliability, and practical cost.

## How to read the evidence

The models were asked to review three materially different targets. A model
was not rewarded merely for producing a plausible-looking report: its final
answer was compared with independently checked code behaviour, tests, and
where relevant, platform documentation.

| Evidence stream | What it tested | Reference outcome |
|---|---|---|
| ASL directory-picker branch, DSH rounds 1--2 | Ability to find real, serious defects in a broken implementation | Ten independently reproduced defects: incorrect ASL tag base, unset context, two invalid tests, two real allocator API failures, a nonexistent Qt flag, broken headless behaviour, and a policy-violating binary asset. |
| Restore-backups branch, DSH round 3 | Ability to review sound code without inventing defects | No blocking defect; four real, non-blocking observations about documentation, ABI completeness, edge-case coverage, and pre-existing shared-state locking. |
| Model-broker supervisor, VS Code Chat round | Operational/security review, tool use, final-answer synthesis | A credible socket-file bind-mount restart hazard; recovery risk because every operation re-renders; serial unbounded control handling; inherited renderer environment; configuration/documentation drift. A supposed `ProtectSystem=strict`/`/tmp` blocker was disproved: `PrivateTmp=true` makes private `/tmp` writable. |

The first two evidence streams came from DeepSeek Harness (DSH) session logs;
the third came from VS Code Chat session records against the local llama
endpoint. Their tooling and timing fields differ, so timings are compared
within a stream, not treated as a fleet-wide benchmark. Tool-call counts are
likewise evidence of exploration cost, not a quality score.

An incomplete session is recorded as a delivery failure, but is not
automatically attributed to the model. The ASL sessions include two known
external incidents: one request never reached a stopped/unreachable service,
and another was cut off when the MoE router left a GPU-holding subprocess
orphaned. Those do not measure model capability.

## At-a-glance guidance

| Model | Evidence | Review quality | Reliability / cost | Recommended role |
|---|---|---|---|---|
| Qwen3.8-Flash-Next-UD-Q3_K_XL | Two excellent broken-code reviews; deepest supervisor review | Highest demonstrated defect-finding depth, with well-supported operational analysis | Very slow: complete ASL reviews took about 205--209 min; supervisor review 162 min | Independent merge-gate or second-pass reviewer, with a long time budget |
| Qwen3.6-35B-A3B-Q4_K_M | Sound-code review | Best fast, evidence-led review; found 3/4 known minor issues without fabrication | 3.6 min, 17 calls | First-pass reviewer; pair with a deeper reviewer on risky changes |
| Qwen3.8-27B-UD-Q6_K_M | Broken-code review | Careful live verification; found the first 5 known ASL defects, but missed the later 5 | One useful run took 192 min; one external transport failure | Deep investigation when Flash Next is unavailable, not a complete gate alone |
| Devstral-Small-2-24B-Instruct-2512-Q6_K | Supervisor review | Completed quickly but delivered a generic approval and missed every established material risk | 1.6 min, 10 calls | Do not use for in-depth review without materially better prompting or evidence |
| Ornith-1.5-35B-A3B-Q4_K_M | Supervisor review | Coherent moderate-depth analysis, but missed important lifecycle risks | 5.7 min | Fast triage only |
| NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0 | Broken and sound-code reviews | Some useful observations, but wrong or self-contradictory verdicts and one off-spec review | Fast; one failure was a known DSH configuration bug | Triage only; never sole approver |
| Laguna-XS-2.1-Q4_K_M-Expert-Offload | Sound-code review | Correct safe-code conclusion, but no independent defects despite 65 calls | 12.9 min, high exploration cost | Low-value corroboration only |
| gpt-oss-20b-F16 | All three evidence streams | Repeatedly generic, wrong, incomplete, or unevidenced | Fast, but inconsistent | Do not use as a gate |
| gpt-oss-120b-Q4_K_M | Supervisor review | Generic or truncated; missed concrete operational issues | 5.2 min completed attempt | Do not use as a gate |
| Qwen3.8-27B-UD-IQ3_S | Supervisor review | Found a real restart hazard, but promoted a false systemd claim to critical | 13.3 min | Require independent verification of every finding |
| Qwen3-Coder-Next-Q4_K_M | Broken-code review | Incorrect conclusion and a fabricated claim | One external disruption; one short completed but wrong run | Avoid for review work |
| North-Mini-Code-1.0-UD-Q4_K_M-Expert-Offload | Sound-code review | Confirmed fabrication of specific test coverage | 3.0 min | Avoid for review work |
| Ornith-1.5-9B-Q4_K_M | Supervisor review | Final review shallow; two earlier attempts delivered nothing | Required three attempts and 43 calls total | Not reliable for multi-turn agent reviews |
| Ling-3.0-flash-Q4_K_M | Supervisor review | No review delivered | Tool calls executed, but both final turns went silent | Not reliable for multi-turn agent reviews |

## Model profiles

### Qwen3.8-Flash-Next-UD-Q3_K_XL

This is the strongest demonstrated reviewer. On the broken ASL branch, two
completed reviews found 7/10 and 9/10 of the independently reproduced
defects. The 9/10 review was unique in finding the Qt binding failure, the
unreachable headless guarantee, and the policy-violating tracked binary; it
also verified the Qt failure against the installed binding rather than merely
inferring it from source.

Its VS Code supervisor review was similarly the deepest completed analysis.
It correctly identified that the supervisor renders before `stop`, `rm`, and
`ps`, so a bad profile can prevent recovery, and it covered serial request
handling, missing timeouts, inherited renderer environment, logging, install
ordering, and path/doc drift. It overstated the runtime-directory permission
mismatch as a blocker for the intended container broker: the documented
deployment bind-mounts the socket file, so Docker resolves the source as root
and container access is controlled by the mounted socket. That qualification
matters, but does not erase the rest of the review's value.

The limiting factor is wall-clock cost. Its best ASL sessions ran for roughly
205 minutes and the supervisor review took 162 minutes, with long gaps
between tool rounds. One ASL run delivered no final text only because the
router was wedged by an orphaned GPU process; that is an infrastructure
failure, not evidence that the model could not finish. Use it where depth
matters more than latency, and audit the final report rather than trusting
intermediate reasoning.

### Qwen3.6-35B-A3B-Q4_K_M

The sound-code review was the best fast review in the evidence set: 3.6
minutes, 17 tool calls, correct scope/format, three of the four known
non-blocking findings, and no fabricated claim. It explicitly enumerated
coverage and findings rather than merely repeating the prompt's assertions.

There is no directly comparable broken-code session for this exact model in
the retained evidence, so it should not be credited with Flash Next's ASL
performance by model-family resemblance. The demonstrated result is still
enough to make it the preferred first pass for ordinary changes: it gives
useful independent scrutiny quickly. Escalate security-sensitive, complex,
or merge-gating work to Flash Next or a human second review.

### Qwen3.8-27B family

`Qwen3.8-27B-UD-Q6_K_M` produced the original careful ASL investigation. It
re-ran tests and static checks, inspected the NDK headers and compiled binary,
and found the first five reproduced defects. That is strong verification
practice, but the later review set established five additional real defects
it missed. Its useful session took 191.9 minutes; a later attempt delivered
nothing because the service was unreachable before it generated any output.

`Qwen3.8-27B-UD-IQ3_S` reviewed the supervisor in 13.3 minutes. It found the
real risk that a container bind-mount of the socket *file* stays attached to
the old inode after the supervisor unlinks and re-binds it on restart. It also
made its top finding false: it claimed `ProtectSystem=strict` prevents the
renderer writing to `/tmp`, overlooking the unit's `PrivateTmp=true`. Private
`/tmp` is writable in that combination. This is a clear case where a real
observation does not compensate for a false critical conclusion; independently
verify its findings before acting on them.

### Devstral-Small-2-24B-Instruct-2512-Q6_K

Devstral completed the supervisor review cleanly in 96.6 seconds after ten
successful tool calls: it located the directory, then read the README, design,
supervisor, client, installer, unit, and example environment. This distinguishes
the result from Ling's missing-final-turn problem; the endpoint and tool loop
worked, and the model had the relevant source in context.

The resulting 455-token report was nevertheless almost entirely generic
approval. It praised the socket/HMAC boundary, bounded Compose actions, and
systemd hardening, then proposed generic logging, event, and health-check
improvements. It did not identify the render-before-every-operation recovery
failure, stale file-bind-mounted socket after restart, serial unbounded control
handling, inherited renderer environment, or configuration/documentation drift.
It also offered no commands, line-level evidence, or attempt to test its
positive assertions. For this target it is a fast surface summary, not a code
review; its successful tool use must not be mistaken for substantive analysis.

### NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0

Nemotron was fast but inconsistent. Across three ASL attempts it produced one
empty/truncated result, one incorrect “functionally sound” conclusion, and
one self-contradictory “merge-ready” conclusion after finding a fatal `_ctx`
failure. In the sound-code round it honestly verified claims from the session
log, but did not perform the requested exhaustive code-review workflow.

The empty ASL attempt was partly an environment/configuration artifact: DSH
was still pruning it as if its context were 65K rather than its real 262K and
had no compaction override. That explains the truncated run, not the weak
verdicts in its other two attempts. It can provide a fast observation pass,
but should never bless a merge by itself.

### gpt-oss models

The observations below predate the 2026-09-22 GPT-OSS configuration correction:
the models previously inherited llama.cpp's generic sampling defaults and the
embedded template's `medium` reasoning default. They are useful historical
evidence, but are not a verdict on the newly configured `high`-effort Harmony
setup; re-evaluate it before using either model as a review gate.

`gpt-oss-20b-F16` has no dependable review pattern. Its ASL attempts were,
respectively, an incorrect approval, no output, and a list of useful fixes
without a pass/fail verdict. The sound-code review claimed activities such as
tracing a call path without evidence, then collapsed the result into a blanket
“no issues.” Its supervisor review was generic and made unnecessary secret
permission recommendations. Fast decoding did not translate into reliable
synthesis or evidence discipline.

`gpt-oss-120b-Q4_K_M` is not rescued by its larger size in the available
supervisor evidence. One attempt stopped after 384 characters; another
delivered a generic review that missed the meaningful recovery and lifecycle
risks. Neither model should be used as a code-review gate.

### Qwen3-Coder-Next-Q4_K_M and North-Mini-Code-1.0

These are the clearest negative cases. Qwen3-Coder-Next completed one short
ASL review with an incorrect “no fatal bugs” conclusion and a false claim
about the session summary; its other attempt was externally disrupted. North
Mini's sound-code review fabricated a specific claim that a test covered
untracked/already-closed windows, while the cited test covered only mask-to-0
and re-enable cases. A reviewer that invents checkable evidence is more
dangerous than one that simply misses a defect. Avoid both for review work.

### Laguna-XS-2.1-Q4_K_M-Expert-Offload

Laguna's sound-code conclusion was correct, but it spent 65 tool calls and
12.9 minutes to return twelve confirmations and no independently discovered
issue among the four known non-blocking observations. It is evidence that a
well-formatted, non-fabricated review can still add almost no diagnostic
value. Use only as inexpensive corroboration when another reviewer has
already done the substantive work.

### Ornith models

`Ornith-1.5-35B-A3B-Q4_K_M` delivered a coherent supervisor review in 5.7
minutes. It correctly understood the private-`/tmp` behaviour and noted the
single-threaded control server and replay-check ordering. It nevertheless
missed the higher-value recovery problem caused by rendering for every action,
and made some assumptions about the socket deployment that were not borne out
by the documented container bind mount. It is suitable for rapid triage, not
for a decisive operational review.

`Ornith-1.5-9B-Q4_K_M` is an agentic reliability failure. Its first two
supervisor attempts each made 19 mostly serial tool rounds, then returned
“Sorry, no response was returned” after several minutes of silence. A third
attempt inherited the exploration, made six more calls, and produced a
superficial final review. The session metadata lacks a server finish reason,
so the exact boundary cannot be proven; the repeated shape is consistent with
a tool-round or stream-idle limit being exhausted by slow convergence. Do not
select it for unattended, multi-turn reviews.

### Ling-3.0-flash-Q4_K_M

Ling did not deliver a final supervisor review in either attempt. It did
*execute* tools: VS Code recorded two `list_dir` calls in the first request
and six `read_file` calls in the second, with returned result content for
each. The visible `<tool>` tags in reasoning were therefore a
model/template-channel symptom, not proof that tool calls were ignored.

Both requests went silent after tool results and VS Code marked them
incomplete. The captured state has neither a raw llama-server error nor a
finish reason, so it cannot distinguish a model failure from an endpoint
stream/parser failure. The practical verdict is straightforward: do not use
this endpoint/template combination for multi-turn agent reviews until a raw
failing completion trace and server log explain the missing final turn.

## Cross-model findings

### Final answers matter more than intermediate work

Several models had useful internal observations but failed to put the right
ones in their final answer. Qwen3.8-27B-IQ3_S found the stale socket bind-mount
hazard but led with a false `PrivateTmp` claim. Flash Next found the
runtime-directory permission mismatch but applied it too broadly to a
file-mounted container. A review workflow must verify final recommendations,
not merely reward apparent exploration.

### Tool use is neither depth nor reliability

Laguna made 65 calls and found none of the known sound-code issues; Qwen3.6
made 17 and found three. Ling's calls executed despite appearing in the
reasoning channel, but it never wrote a final answer. Ornith-1.5-9B made 43
calls over three attempts because it did not converge. Tool-call count is a
cost and failure-mode signal, not a proxy for review quality.

### Separate service incidents from model behaviour

The stopped/unreachable service and the orphaned GPU subprocess explain
specific zero-output sessions, not broad model incapability. By contrast,
Ling's two silent final turns, Ornith-1.5-9B's repeated serial exploration,
gpt-oss-20b's inconsistent conclusions, and North Mini's fabricated test
claim persisted in otherwise functioning sessions and are model or
model/template concerns.

## Practical review workflow

For ordinary changes, start with `Qwen3.6-35B-A3B-Q4_K_M` and require it to
list inspected files, tests run, and each finding's evidence. For a risky,
security-sensitive, or merge-gating change, use Flash Next as an independent
second pass and allow hours rather than minutes. Treat any critical claim
from other reviewed models as a hypothesis to reproduce, not a reason to
change production code immediately.

No model in this evidence set replaces a final human check for high-impact
changes. The most productive division of labour is fast independent triage,
slow deep review where warranted, and explicit reproduction of the final
findings before a merge decision.
