# Survey of practice for Paper 4: planning with bounded authority, and architect/developer pipelines

> **Re-checked by the drafting session, 29 October 2026.**
> - **Confirmed against the source:**
>   - ACE, from its abstract: the two-phase plan from trusted information only, the static
>     information-flow check, the barriers between apps, NDSS 2026.
>   - Conseca, from its body: deterministic enforcement, human-readable rationales, approval
>     optional and not evaluated, 12.0/20 against 14.0/20 tasks completed.
>   - The design-patterns quote "does not prevent prompt injections contained in the user
>     prompt", verbatim.
> - **Not re-checked:** ACE's "100%" on InjecAgent, which is not in its abstract.
>
> The headline claim, that no system persists a reviewed authority artefact made from a
> natural-language task, is scoped to *what was surveyed*. Any paper must state it that way.

Fetched 29 October 2026. Every entry was checked against the URL given. Where a source's text was not read past its first ~100k characters, the entry says so. Numbers are quoted as read.

## Area 1: Planning, or emitting a plan with bounded authority, before execution

**1. CaMeL planner mechanics** (`debenedetti_defeating_2025`, already in the bib; https://arxiv.org/html/2503.18813v2, read to about 50%)
The privileged LLM sees the user task, a system prompt and the tool signatures. It writes a Markdown code block in a restricted Python subset. Each quarantined-LLM call must name a Pydantic output schema. A custom `ast` interpreter tracks a data-flow graph and tags each value with its provenance and its readers. The engine supplies the security policies as Python functions, which are checked on a tool's arguments and their dependencies before the call. The paper envisions users or tool providers writing them, but does not implement that. The P-LLM never sees tool values. On an exception it is re-prompted up to 10 times, with the message redacted when the error depends on untrusted data. No human reviews the plan; the user confirms only policy violations.
*Bears on Paper 4:* this is the template for the architect's information diet. Three differences to state: our plan is a **persistent graph** rather than ephemeral code; the policy is **authored per task inside the plan** (the `with` clauses) rather than fixed by the engine; and review happens **before** execution, not at a violation. Re-prompting also leaks: even a redacted error tells the planner that something failed, so the validator-in-the-loop channel needs the same discipline.

**2. ACE: abstract plan, concrete plan, static information-flow check** (strongest direct competitor)
```bibtex
@inproceedings{li_ace_2026,
  title={{ACE}: A Security Architecture for {LLM}-Integrated App Systems},
  author={Li, Evan and Mallick, Tushin and Rose, Evan and Robertson, William and Oprea, Alina and Nita-Rotaru, Cristina},
  booktitle={Network and Distributed System Security Symposium (NDSS)},
  year={2026}, eprint={2504.20984}, archivePrefix={arXiv}}
```
A planning LLM writes an abstract plan, a restricted Python-like `main()` over abstract apps with type signatures. Its only input is the query plus optional fully trusted context, and it is not shown the installed apps. A second LLM maps the plan to concrete apps, preferring "low privilege". The plan is compiled to an information-flow grammar and checked against a lattice policy, with the user supplying the query's sensitivity label. At execution, each app runs in its own Dockerised worker. The paper reports "a security score of 100% across all 1,054 test cases" on InjecAgent. It does not say whether plans are stored or reviewed by a human. (https://arxiv.org/abs/2504.20984; HTML read to about 60%.)
*Bears on Paper 4:* closest prior art to "an architect authors a checked plan". Position against it on four points. ACE's barriers are per app (Docker); ours are per node, with a WASM import set derived from the plan. ACE's lattice is for confidentiality; ours is a trust lattice. Its plan is not a persistent artefact. It has no independent reviewer. **Adopt** its split: an abstract plan written blind to the installed catalogue, then a separate mapping step, so the catalogue's breadth cannot tempt the planner.
A newer, weaker relative is PlanGuard (Gong and Deng, arXiv:2604.10134, April 2026; abstract only, read at https://arxiv.org/abs/2604.10134). An isolated planner derives "a reference set of valid actions" from the user's instructions alone, and deviating calls go to rule checks and then to an *LLM* intent verifier. It reports InjecAgent attack success falling from 72.8% to 0%, with a 1.49% false-positive rate. Its final arbiter is a model, which Leong's result warns against, so cite it as a contrast. `@misc{gong_planguard_2026, title={{PlanGuard}: Defending Agents against Indirect Prompt Injection via Planning-based Consistency Verification}, author={Gong, Guangyu and Deng, Zizhuang}, year={2026}, eprint={2604.10134}, archivePrefix={arXiv}}`

**3. Conseca: generated, human-verifiable, per-task policies**
```bibtex
@misc{tsai_contextual_2025,
  title={Contextual Agent Security: A Policy for Every Purpose},
  author={Tsai, Lillian and Bagdasarian, Eugene},
  year={2025}, eprint={2501.17070}, archivePrefix={arXiv}}
```
An LLM generates a policy from the task, the tool documentation, example policies and *trusted context only*. The trusted context is email categories and addresses, the filesystem tree, the username and the time. Per API call, the policy records "Can Execute", regex constraints on arguments, and a human-readable rationale. Enforcement is deterministic. Developers "can optionally" ask users to approve the policy, but the prototype reports no such review. The evaluation is 20 synthetic tasks: Conseca completes 12.0/20, against 14.0 with no policy and 0.0 with a static restrictive one. (https://arxiv.org/html/2501.17070v3)
*Bears on Paper 4:* this is the nearest existing answer to "a persistent, reviewable authority artefact from natural language", and it shows the gaps. The policy is per call, not a topology. Its review is optional and unevaluated. It names its own limit: it checks "individual actions, not trajectories". **Adopt** the per-grant rationale: each `with` clause should carry the line of the prompt that justifies it, so the reviewer checks justification, not just shape. **Avoid** regex argument constraints, which its authors call complex.

**4. Design patterns, including plan-then-execute**
```bibtex
@misc{beurerkellner_design_2025,
  title={Design Patterns for Securing {LLM} Agents against Prompt Injections},
  author={Beurer-Kellner, Luca and Buesser, Beat and Cre{\c{t}}u, Ana-Maria and Debenedetti, Edoardo and Dobos, Daniel and Fabian, Daniel and Fischer, Marc and Froelicher, David and Grosse, Kathrin and Naeff, Daniel and Ozoani, Ezinwanne and Paverd, Andrew and Tram{\`e}r, Florian and Volhejn, V{\'a}clav},
  year={2025}, eprint={2506.08837}, archivePrefix={arXiv}}
```
The paper names six patterns: action-selector, plan-then-execute, LLM map-reduce, dual LLM, code-then-execute and context-minimization. Plan-then-execute gives "control flow integrity", but an injection "could, however, arbitrarily alter the body of the email". The pattern also does "not prevent prompt injections contained in the user prompt". The paper does not discuss human review of plans. (https://arxiv.org/html/2506.08837v3)
*Bears on Paper 4:* a signal graph is code-then-execute with authority made explicit per node. Cite this as the taxonomy that places it. The second caveat is Paper 4's own threat: **the Product Owner's prompt is the trusted input, and a pretext in it is out of scope for every one of these patterns.** That gap is what Paper 4's reviewer measurement addresses.
A related practitioner guide is Del Rosario, Krawiecka and Schroeder de Witt, *Architecting Resilient LLM Agents: A Guide to Secure Plan-then-Execute Implementations*, arXiv:2509.08646 (2025). It gives blueprints for LangGraph, CrewAI and AutoGen and recommends "task-scoped tool access". From the abstract alone it is unclear whether that scoping is per step. Cite it only for the practice, not for any guarantee.

**5. Information-flow planners and autonomy (Microsoft line)**
```bibtex
@misc{costa_securing_2025,
  title={Securing {AI} Agents with Information-Flow Control},
  author={Costa, Manuel and K{\"o}pf, Boris and Kolluri, Aashish and Paverd, Andrew and Russinovich, Mark and Salem, Ahmed and Tople, Shruti and Wutschitz, Lukas and Zanella-B{\'e}guelin, Santiago},
  year={2025}, eprint={2505.23643}, archivePrefix={arXiv}}
@misc{kolluri_optimizing_2026,
  title={Optimizing Agent Planning for Security and Autonomy},
  author={Kolluri, Aashish and Sharma, Rishi and Costa, Manuel and K{\"o}pf, Boris and Nie{\ss}en, Tobias and Russinovich, Mark and Tople, Shruti and Zanella-B{\'e}guelin, Santiago},
  year={2026}, eprint={2602.11416}, archivePrefix={arXiv}}
```
FIDES gives a formal model of planners, with confidentiality and integrity labels enforced deterministically, evaluated on AgentDojo. Kolluri et al. add **autonomy metrics**: "the share of consequential actions" an agent completes without human approval while staying secure. Their threat model trusts the user, the planner LLM and the tools. (abstracts at https://arxiv.org/abs/2505.23643 and https://arxiv.org/abs/2602.11416; full texts not read)
*Bears on Paper 4:* this is the most direct AgentDojo competitor, because it is dynamic IFC on the same benchmark. Paper 4 should report an autonomy-style figure beside utility and attack success, because a fixed graph front-loads human attention into review. Position the difference precisely: FIDES labels values at run time inside one planner, while we fix the topology before run time and check it twice.

**6. Workflow-first agents (LLMCompiler, ReWOO, LangGraph)**
```bibtex
@inproceedings{kim_llm_2024,
  title={An {LLM} Compiler for Parallel Function Calling},
  author={Kim, Sehoon and Moon, Suhong and Tabrizi, Ryan and Lee, Nicholas and Mahoney, Michael W. and Keutzer, Kurt and Gholami, Amir},
  booktitle={International Conference on Machine Learning (ICML)}, year={2024}, eprint={2312.04511}, archivePrefix={arXiv}}
@misc{xu_rewoo_2023,
  title={{ReWOO}: Decoupling Reasoning from Observations for Efficient Augmented Language Models},
  author={Xu, Binfeng and Peng, Zhiyuan and Lei, Bowen and Mukherjee, Subhabrata and Liu, Yuchen and Xu, Dongkuan},
  year={2023}, eprint={2305.18323}, archivePrefix={arXiv}}
```
LLMCompiler has a planner emit a task DAG, which a task-fetching unit and an executor run in parallel. It reports "up to 3.7x" lower latency than ReAct. ReWOO plans without observations and reports 5x token efficiency. LangGraph compiles a graph, but nodes can route at run time with `Command(goto=…)`. Its `interrupt()` pauses execution for a human through a checkpointer. The interrupts page describes no authority model. (https://docs.langchain.com/oss/python/langgraph/interrupts)
*Bears on Paper 4:* all three emit DAGs for **efficiency, not authority**. They show that a planner-emits-graph design is practical. Cite them for that, and claim no security precedent from them. **Avoid** LangGraph's run-time `goto`: it is exactly the per-call topology choice the signal graph forbids.

**7. Coding-agent and MCP permission models in practice (docs)**
- **Claude Code** (https://code.claude.com/docs/en/permissions, /permission-modes). Rules are evaluated "deny, then ask, then allow". A Bash rule "isn't a security boundary around the program"; for that, use the OS sandbox. Plan mode writes a plan, and approving it switches the session's permission mode. The plan does not carry a grant. The auto-mode classifier sees tool calls but "Tool results are stripped". The docs say it "does not guarantee safety". Boundaries stated in conversation "can be lost" to compaction.
- **Codex** (https://learn.chatgpt.com/codex/agent-approvals-security). The sandbox modes are read-only, workspace-write and danger-full-access, enforced by Seatbelt, or by bwrap plus seccomp. Network is off by default. An `auto_review` setting routes approval requests to a reviewer agent.
- **Copilot coding agent.** Each MCP server needs a `tools` allowlist, and Copilot uses those tools "autonomously, and will not ask for your approval". The firewall "does not apply directly to Model Context Protocol (MCP) server processes" and is not "a comprehensive security solution". (Sources: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/extend-coding-agent-with-mcp and …/customize-the-agent-firewall.)
- **MCP authorization** (spec 2025-11-25, https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization). Scopes are per server, not per tool. Absent a challenge, clients request "all scopes defined in `scopes_supported`". Additional authority comes through **step-up authorization** at run time on `insufficient_scope`.
- **AgentBound** (Bühler, Biagiola, Di Grazia, Salvaneschi, *AgentBound: Securing Execution Boundaries of AI Agents*, FSE 2026, arXiv:2510.21236). It brings Android-style declarative manifests to MCP servers and generates them from source code "with 80.9% accuracy". BibTeX: `@inproceedings{buhler_agentbound_2026, title={{AgentBound}: Securing Execution Boundaries of {AI} Agents}, author={B{\"u}hler, Christoph and Biagiola, Matteo and Di Grazia, Luca and Salvaneschi, Guido}, booktitle={ACM International Conference on the Foundations of Software Engineering (FSE)}, year={2026}, eprint={2510.21236}, archivePrefix={arXiv}}`

*Bears on Paper 4:* practice grants authority **per session or per server**. It approves the plan's *intent*, not its authority, and it escalates at run time: step-up authorization, approval prompts, and a classifier. Paper 3's pretext result says run-time escalation is the hole. Paper 4's contrast is therefore that escalation **edits the reviewed graph** and returns to steps 3–4. Claude Code's "conversation boundaries can be lost" supports keeping authority out of context and in the artefact. AgentBound is the closest *persistent* manifest, but it is generated from code, not from a task, and it is per server.

**Answer to the persistence question.** In everything fetched, no system generates a persistent, *task-derived* authority artefact and has a human or an independent model review it before execution. Conseca comes closest and makes review optional. ACE checks its plan statically but does not persist or review it. AgentBound persists manifests but derives them from code. This is a claim about what was surveyed, not an exhaustive negative.

## Area 2: Multi-role development pipelines

**1. MetaGPT**
```bibtex
@inproceedings{hong_metagpt_2024,
  title={{MetaGPT}: Meta Programming for A Multi-Agent Collaborative Framework},
  author={Hong, Sirui and Zhuge, Mingchen and Chen, Jonathan and Zheng, Xiawu and Cheng, Yuheng and Wang, Jinlin and Zhang, Ceyao and Wang, Zili and Yau, Steven and Lin, Zijuan and Zhou, Liyang and Ran, Chenyu and Xiao, Lingfeng and Wu, Chenglin and Schmidhuber, J{\"u}rgen},
  booktitle={International Conference on Learning Representations (ICLR)}, year={2024}, eprint={2308.00352}, archivePrefix={arXiv}}
```
The roles are Product Manager, Architect, Project Manager, Engineer and QA. They pass a PRD, then a system design (file lists, data structures, interface definitions), then a task list, code and tests. Agents "communicate through documents and diagrams… rather than dialogue", over a publish-subscribe pool. The paper describes **no role restricting another's tools**: information flow is limited "through subscriptions, not through access controls" (paraphrase of the fetched text). It reports HumanEval 85.9% and MBPP 87.7% Pass@1. On SoftwareDev it reports executability 3.75 against ChatDev's 2.25. (https://proceedings.iclr.cc/…6507b115562bb0a305f1958ccc87355a…; https://arxiv.org/html/2308.00352v7. The arXiv v7 author list differs slightly from the proceedings, which the BibTeX follows.)
*Bears on Paper 4:* the architect's artefact here is an interface design, and it bounds **scope, not authority**. A signal graph is a MetaGPT system design that is also machine-checked and enforceable. That is the one-line positioning.

**2. ChatDev**
```bibtex
@inproceedings{qian_chatdev_2024,
  title={{ChatDev}: Communicative Agents for Software Development},
  author={Qian, Chen and Liu, Wei and Liu, Hongzhang and Chen, Nuo and Dang, Yufan and Li, Jiahao and Yang, Cheng and Chen, Weize and Su, Yusheng and Cong, Xin and Xu, Juyuan and Li, Dahai and Liu, Zhiyuan and Sun, Maosong},
  booktitle={Annual Meeting of the Association for Computational Linguistics (ACL)}, year={2024}, eprint={2307.07924}, archivePrefix={arXiv}}
```
Its waterfall roles are coordinated by a "chat chain", with "communicative dehallucination". The artefact is the dialogue itself, and the abstract gives no quantitative benchmarks. (https://arxiv.org/abs/2307.07924)
*Bears on Paper 4:* this is the anti-pattern. Dialogue as the hand-off is exactly where a pretext travels. Hand-offs between roles should be typed artefacts, never conversation.

**3. Aider architect/editor**
The architect model "describes how to solve the coding problem", and the editor turns that into file edits. The best pairing on aider's editing benchmark was o1-preview with o1-mini or deepseek, at 85.0%, against 79.7% for o1-preview alone (blog post, 26 Sep 2024). The docs say nothing about the architect restricting the editor. (https://aider.chat/docs/usage/modes.html; https://aider.chat/2024/09/26/architect.html)
*Bears on Paper 4:* this is evidence that splitting reasoning from editing helps on its own merits, not only for security. Here, though, the split is a capability split between models, not a privilege split.

**4. MASAI** (a stronger, SWE-bench-evaluated modular design)
```bibtex
@misc{arora_masai_2024,
  title={{MASAI}: Modular Architecture for Software-engineering {AI} Agents},
  author={Arora, Daman and Sonwane, Atharv and Wadhwa, Nalin and Mehrotra, Abhav and Utpala, Saiteja and Bairi, Ramakrishna and Kanade, Aditya and Natarajan, Nagarajan},
  year={2024}, eprint={2406.11638}, archivePrefix={arXiv}}
```
Sub-agents each solve a defined sub-problem with their own strategy. The paper reports 28.33% resolution on SWE-bench Lite. (https://arxiv.org/abs/2406.11638)
*Bears on Paper 4:* this is the standard way such systems are evaluated. Note that resolution rate measures scope decomposition, not authority. No SWE-bench-style benchmark scores whether a role stayed within granted authority, so Paper 4 should define its own measure.

**5. Claude Code subagents: the one practical case of one role bounding another's authority**
A subagent's `tools` field is an allowlist, `disallowedTools` is applied first, and the subagent "inherit[s] the parent conversation's permission rules". Its `permissionMode` cannot exceed the parent's. There are stated exceptions: inline `mcpServers` can give a subagent servers the parent lacks, and a subagent can receive Glob and Grep when the parent lacks them. (https://code.claude.com/docs/en/sub-agents, read to about 85%)
*Bears on Paper 4:* this is attenuation by delegation, and it is per tool and per session. The exceptions show an author-declared definition **widening** what the parent holds. That is the shape of authority Paper 4's reviewers must catch. The graph analogue, a sub-graph that may only narrow, is already a checked rule.

**6. SWE-bench**
```bibtex
@inproceedings{jimenez_swebench_2024,
  title={{SWE}-bench: Can Language Models Resolve Real-World {GitHub} Issues?},
  author={Jimenez, Carlos E. and Yang, John and Wettig, Alexander and Yao, Shunyu and Pei, Kexin and Press, Ofir and Narasimhan, Karthik},
  booktitle={International Conference on Learning Representations (ICLR)}, year={2024}, eprint={2310.06770}, archivePrefix={arXiv}}
```
*Bears on Paper 4:* cite it only to say why it is the wrong instrument. It scores issue resolution, and authority is unmeasured. AgentDojo, which scores utility and security together, is the right one.

**Checked and still unverified:** whether any multi-role SE framework (CrewAI's per-agent tools, AutoGen, OpenHands delegation) lets one role constrain another's *authority*. I did not fetch their docs, so treat this as UNVERIFIED.

## Suggested design consequences for the architect and reviewers

1. **Two-stage authoring, following ACE.** The architect first writes an abstract graph from the prompt alone, without the capability catalogue. A separate step maps it to concrete kinds, preferring the narrowest. A pretext then has to survive two independent steps.
2. **Every grant carries a rationale, following Conseca.** Each `with` entry cites the span of the PO prompt that justifies it. The independent reviewer checks rationale against prompt, and the formal review checks rationale against kind (for example, a rationale with no "send" in it cannot justify `ResponseChannel`).
3. **The architect's information diet follows CaMeL**: the prompt, the catalogue and validator verdicts only. Validator feedback is structured (reason class plus location), never free text echoed from data.
4. **The reviewer sees the graph and the prompt, never the architect's reasoning.** This follows the auto-mode classifier, which strips tool results, and Leong's finding that model self-arbitration is not a trust boundary. If the reviewer read the architect's justification prose, a pretext would reach it.
5. **A diff-against-minimum check, as formal tooling.** Compute or bound the least authority that the prompt's verbs require, and flag every grant beyond it. That turns "widened unseen" into a measurable quantity rather than a reviewer's judgement.
6. **No run-time escalation path.** This is unlike MCP step-up, Codex approvals and Claude Code prompts. A missing grant fails the run and returns to the architect as a graph edit. State it as the paper's contrast with practice.
7. **Report autonomy beside utility and attack success**, following Kolluri et al.: how many consequential actions run with no human prompt, because review is paid once, up front.
8. **Treat the PO prompt as the attack surface, and say so.** Every pattern above leaves "prompt injections contained in the user prompt" out of scope. Paper 4's pretext experiment is the novel measurement, not a footnote.

## Open questions for the author

1. Is the abstract-then-concrete split (consequence 1) worth the second model call and the mapping step's own failure modes, or should the architect see the catalogue from the start?
2. How strong a PlanGuard/FIDES/CaMeL baseline does Paper 4 need? Published numbers on other models (the no-paid-API rule), or a re-implementation of one on `claude -p`?
3. Is a "minimum authority from the prompt" oracle (consequence 5) in scope? It may be as hard as planning itself, but without it "unseen widening" needs a hand-labelled ground truth per AgentDojo task.
4. Should the human, via the Product Owner, see the graph at step 4, as Conseca's optional approval does? Or is excluding the human from steps 1–4 part of the claim?
