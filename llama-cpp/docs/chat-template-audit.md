# Chat-template audit

This is an operational compatibility audit, not a quality ranking. A GGUF
template controls the exact wire format for system messages, reasoning, tools,
and tool results. Therefore a template can make an otherwise sound model fail
only in an agent client, as happened with Devstral. Do not replace templates
solely because a newer one exists: retain an override only when the deployed
GGUF is demonstrably incompatible with the client protocol.

## Applied override: Devstral Small 2 24B Instruct 2512

The GGUF template rejected a valid `assistant` tool call -> `tool` result ->
`user` continuation with the exact role-alternation exception recorded by the
32GB router. Mistral's [fixed template discussion](https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512/discussions/30)
describes that same agent/tool round failure. The publisher's
[55c5b41 template revision](https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512/blob/55c5b41e98c2dbd21b0c8afffc540dcfc9eb5128/chat_template.jinja)
aggregates consecutive messages and validates the tool-aware transitions.

`config/chat-templates/devstral-small-2-24b-instruct-2512.jinja` vendors that
exact revision. Every declared 2512 Devstral entry uses it via
`chat-template-file`; the 2505 family does not, because its wire format and
compatibility have not been tested against this change.

## Other models in the coding-quality and code-review evidence

| Model family | Publisher evidence | Deployment assessment | Action |
| --- | --- | --- | --- |
| GLM-4.7-Flash | The official repository changed its template from a minimal historical file to the current [3,120-byte template](https://huggingface.co/zai-org/GLM-4.7-Flash/blob/main/chat_template.jinja). | The deployed GGUF begins with the same `[gMASK]<sop>` format as the current publisher template. No client-template fault is recorded. | Keep embedded template; exercise a multi-turn tool round after every GGUF refresh. |
| gpt-oss-20b / 120b | OpenAI's [current 20b template](https://huggingface.co/openai/gpt-oss-20b/blob/main/chat_template.jinja) has been updated, including a published [assistant-tool-call null-content fix](https://huggingface.co/openai/gpt-oss-20b/discussions/229/files). | The deployed Unsloth GGUF contains a converter-modified template, so it should not be assumed equivalent to the current OpenAI template. | High-priority protocol comparison and tool-round regression test; do not override until the rendered prompt and output protocol have been compared. |
| Laguna XS 2.1 | Poolside publishes a versioned [2.1 template](https://huggingface.co/poolside/Laguna-XS-2.1-INT4/blob/main/chat_template.jinja), and its artefacts show template updates between releases. | The deployed GGUF starts with the current `laguna_glm_thinking_v8` template header. No incompatibility is known. | Keep embedded template; recheck the exact publisher quant/revision before replacing the GGUF. |
| Qwen3-Coder-Next | The official [template history](https://huggingface.co/Qwen/Qwen3-Coder-Next/commits/main/chat_template.jinja) shows the initial published template rather than a later compatibility update. | No newer publisher template is indicated. | No override; include in routine tool-call regression tests. |
| Qwen3.6 / Qwen3.8 | The current official [Qwen3.8 template](https://huggingface.co/Qwen/Qwen3.8-27B/blob/main/tokenizer_config.json) accepts only `xhigh`, `medium`, and `low` reasoning effort. | Existing `low` and `medium` presets are compatible. A client that sends `high` or `none` will fail during template rendering. | Keep the embedded template; do not advertise unsupported reasoning values, and test a tool round when upgrading the GGUF. |
| DeepSeek-Coder-V2-Lite | The official [tokenizer configuration](https://huggingface.co/deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct/blob/main/tokenizer_config.json) provides a basic user/assistant/system template, not an OpenAI `tool`-role protocol. | This is a capability mismatch risk if a client advertises it as tool-capable, but there is no publisher replacement to vendor. | Test explicitly; if it cannot complete a real tool round, advertise `toolCalling: false` rather than inventing a template. |
| North Mini Code | Cohere published a [tokenizer-template packaging change](https://huggingface.co/CohereLabs/North-Mini-Code-1.0-w4a16/commit/a444b5817084e05d6e4def37a278543b0da43945). | It is evidence to compare a refreshed GGUF's embedded template, not evidence to transplant a template into the existing GGUF. | Regression-test tool rounds after a GGUF update; no override now. |
| Ling 3.0 flash | A community llama.cpp analysis reports that the stock Bailing/Ling template can mis-serialize multi-argument calls and distinguishes it from a separate llama.cpp grammar bug. | This is consistent with the silent VS Code multi-turn symptoms, but the proposed template is for another conversion/build and is not publisher-authoritative. | Highest-priority reproduction test after Devstral. Do not vendor the third-party override without comparing its protocol to this Bartowski GGUF. |
| Ornith and NVIDIA Nemotron | No publisher template replacement with direct applicability to the deployed GGUF was established in this audit. | Absence of a finding is not a compatibility guarantee, particularly for multi-turn agent use. | Keep embedded templates and add the same regression test when a client-facing GGUF is upgraded. |

The highest-priority cases after Devstral are Ling 3.0 flash (a reported
llama.cpp/Bailing tool protocol fault), gpt-oss (publisher fixes versus a
converter-modified deployed template), and DeepSeek-Coder-V2-Lite (no published
tool-result protocol). GLM and Laguna warrant revision tracking but not
speculative overrides.
