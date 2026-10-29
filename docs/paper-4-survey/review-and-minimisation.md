# Survey of practice: capability minimisation and independent LLM review (Paper 4 prep)

> **Re-checked by the drafting session, 29 October 2026:**
> - AI Control's figures are in its body (PDF v5): 79% safety and 96% usefulness for untrusted
>   monitoring, against 62% safety for trusted monitoring, in that paper's one setting;
> - Kim et al., ICML 2025, verbatim: "larger and more accurate models have highly correlated
>   errors, even with distinct architectures and providers";
> - Panickssery et al.'s self-recognition/self-preference correlation. Its arXiv page lists no
>   peer-reviewed venue, so cite it as arXiv.

Surveyed 29 October 2026. Every entry below was checked against the URL given. Where the summary depended on a source's full text, the text was read (Felt, the AI Control HTML, Ye et al. HTML). Otherwise the abstract or official docs page was read.

## 1. Permission and capability minimisation

**1.1 Felt et al., Stowaway (CCS 2011).** Source: https://comp97109.doc.ic.ac.uk/reading/felt_ccs_11.pdf. Metadata from Crossref.
```bibtex
@inproceedings{felt_android_2011,
  title     = {Android Permissions Demystified},
  author    = {Felt, Adrienne Porter and Chin, Erika and Hanna, Steve and Song, Dawn and Wagner, David},
  booktitle = {Proceedings of the 18th ACM Conference on Computer and Communications Security (CCS)},
  pages     = {627--638}, year = {2011}, doi = {10.1145/2046707.2046779}}
```
Stowaway combines a static analysis of which API calls an app makes with a permission map. The authors built the map empirically, by automated testing that reached "85% coverage of the Android API". Applied to 940 apps, it found "about one-third of applications are overprivileged". The paper reports a 7% false-positive rate, all of it "caused by incompleteness in our permission map". It calls reflection "an important open problem".
**Bears on our design. Adopt the shape, and note where we are stronger.** Stowaway's overprivilege is *declared minus used*, computed **statically**. Our analogue is *`with` clause minus what the component's body reaches*. Our map is exact by construction, because each kind has one WIT interface and is derived from `interfaces.py`, so Felt's main error source does not arise. The residual imprecision moves to reachability inside the component. Felt also found that overprivilege mostly came from developer confusion about documentation. Expect architect-AI over-granting to follow the same pattern, and measure it.

**1.2 Au et al., PScout (CCS 2012).** Sources: https://security.csl.toronto.edu/pscout/ and Crossref.
```bibtex
@inproceedings{au_pscout_2012,
  title     = {PScout: Analyzing the Android Permission Specification},
  author    = {Au, Kathy Wain Yee and Zhou, Yi Fan and Huang, Zhen and Lie, David},
  booktitle = {Proceedings of the 2012 ACM Conference on Computer and Communications Security (CCS)},
  pages     = {217--228}, year = {2012}, doi = {10.1145/2382196.2382222}}
```
PScout replaced Stowaway's test-derived map with a map extracted statically from the OS source. It covered four Android versions, and it reports a trade-off between fine-grained permissions and a stable specification as the platform evolves.
**Bears on our design. Position against it.** Its trade-off is ours when we go "below the level of kinds" (direction C). A finer authority vocabulary minimises better, but it churns the `with` clause and breaks graph stability.

**1.3 Ghavamnia et al., Confine (RAID 2020).** Source: https://www.usenix.org/conference/raid2020/presentation/ghavanmnia
```bibtex
@inproceedings{ghavamnia_confine_2020,
  title     = {Confine: Automated System Call Policy Generation for Container Attack Surface Reduction},
  author    = {Ghavamnia, Seyedhamed and Palit, Tapti and Benameur, Azzedine and Polychronakis, Michalis},
  booktitle = {23rd International Symposium on Research in Attacks, Intrusions and Defenses (RAID 2020)},
  publisher = {USENIX Association}, year = {2020}}
```
(No DOI was verified.) Confine generates seccomp policies by static analysis of a container's application and its dependencies. It does this because trace-based approaches "do not capture exhaustively all the code that can potentially be needed by future workloads".
**Bears on our design. Adopt it.** This is the standard answer to the under-approximation pitfall. Bound minimisation from below by a **static over-approximation**, and never by traces alone.

**1.4 AWS IAM Access Analyzer policy generation.** Docs: https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-policy-generation.html
It generates a policy *template* from CloudTrail activity over a window of "up to 90 days". The template is then reviewed and customised: you add actions, specify resources, and add conditions. The docs list blind spots. Data events (for example S3) get no action-level detail, and "`iam:PassRole` ... is not tracked by CloudTrail and is not included in generated policies". The docs also say "Do not use policy generation for auditing purposes".
**Bears on our design. Adopt the posture, and note one difference.** Trace output is a *proposal for review*, labelled with its observation window. Its blind spots are enumerated and published, not implied. Our equivalent blind spot is the host tier: there the trace is advisory, so a host-tier trace must never drive a removal.

**1.5 seccomp profile recording, Kubernetes Security Profiles Operator.** Repository: https://github.com/kubernetes-sigs/security-profiles-operator
The operator records profiles from running workloads. For seccomp it can record from audit logs or from eBPF. The README does **not** discuss coverage or merging across replicas (I found nothing on either).
**Bears on our design. Use it as contrast.** This is industry-default trace-based minimisation, with no stated coverage story. It is the practice Confine argues against.

**1.6 SELinux `audit2allow`.** Man page: https://man7.org/linux/man-pages/man1/audit2allow.1.html
It turns logged denials into allow rules. It warns "Care must be exercised while acting on the output of this utility". It also says that making structural changes (new domains or types) is often better than "blindly implementing the sometimes broad changes recommended by this utility".
**Bears on our design. Avoid this pattern; it is the anti-pattern for step 5.** A denied crossing must never become a grant automatically. That is exactly the escalation-as-text path Paper 3 warns against. The structural fix audit2allow recommends corresponds to *escalation as a graph change, decomposed into a sub-graph*.

**1.7 WASI-Virt (Bytecode Alliance).** Repository: https://github.com/bytecodealliance/WASI-Virt
It wraps a component so that it no longer imports chosen WASI subsystems. "By default the virtualization will deny all subsystems". On composition, subsystems the component does not import are dropped, so "only the imports that are actually used" remain.
**Bears on our design. Adopt it as a mechanism and position the claim against it.** This is import-level trimming at the WebAssembly boundary, the same unit our gate checks. It trims to *imported*, not to *reached*. A component that imports `http-client` but never calls it keeps the import. So minimisation needs a reachability pass over the core module, not import trimming alone.

## 2. Independent and adversarial LLM review

**2.1 Greenblatt et al., AI Control (ICML 2024).** Sources: https://proceedings.mlr.press/v235/greenblatt24a.html and https://arxiv.org/html/2312.06942v5
```bibtex
@inproceedings{greenblatt_ai_2024,
  title     = {{AI} Control: Improving Safety Despite Intentional Subversion},
  author    = {Greenblatt, Ryan and Shlegeris, Buck and Sachan, Kshitij and Roger, Fabien},
  booktitle = {Proceedings of the 41st International Conference on Machine Learning},
  series    = {PMLR}, volume = {235}, pages = {16295--16336}, year = {2024},
  eprint    = {2312.06942}, archivePrefix = {arXiv}}
```
The setting pairs an untrusted strong model (GPT-4) with a trusted weaker one (GPT-3.5). In "untrusted monitoring", a copy of the untrusted model reviews the untrusted model's output. The risk is collusion, through input features or through signals planted in the output. The countermeasures are upfront validation on synthetic backdoors (shut down if the false-negative rate is too high), redaction, paraphrasing, and ensembling with the trusted model. Table 2 reports safety/usefulness of 62%/97% for trusted monitoring, 79%/96% for untrusted monitoring, and 92%/94% for trusted editing (20%).
**Bears on our design. Adopt it; this is the most load-bearing entry.** It gives a sanctioned way to use a *same-model* reviewer, which is our situation. The reviewer must be **validated before use** on planted widening graphs, and its input must be **redacted** of the architect's free-text. With those countermeasures, the same-model monitor still beat a trusted weaker monitor in their setting. That is one setting, not a general law.

**2.2 Panickssery, Bowman and Feng (NeurIPS 2024).** Source: https://papers.nips.cc/paper_files/paper/2024/hash/7f1f0218e45f5414c79c0679633e47bc-Abstract-Conference.html
```bibtex
@inproceedings{panickssery_llm_2024,
  title     = {{LLM} Evaluators Recognize and Favor Their Own Generations},
  author    = {Panickssery, Arjun and Bowman, Samuel R. and Feng, Shi},
  booktitle = {Advances in Neural Information Processing Systems 37 (NeurIPS 2024)},
  year      = {2024}, doi = {10.52202/079017-2197}}
```
Models recognise their own text with non-trivial accuracy. The paper reports "a linear correlation between self-recognition capability and the strength of self-preference bias".
**Bears on our design. FLAG: this argues against our single-family constraint.** A Claude reviewer judging a Claude-authored graph is the configuration this paper predicts will be lenient. Mitigations: the reviewer should judge a **canonicalised** graph (regenerated pseudocode, not the architect's prose), and we should *measure* its leniency against human-made widenings.

**2.3 Goel et al., "Great Models Think Alike" (2025).** Source: https://arxiv.org/abs/2502.04313
```bibtex
@misc{goel_great_2025,
  title  = {Great Models Think Alike and this Undermines {AI} Oversight},
  author = {Goel, Shashwat and Struber, Joschka and Auzina, Ilze Amanda and Chandra, Karuna K and Kumaraguru, Ponnurangam and Kiela, Douwe and Prabhu, Ameya and Bethge, Matthias and Geiping, Jonas},
  year   = {2025}, eprint = {2502.04313}, archivePrefix = {arXiv}}
```
The paper defines CAPA, a similarity metric based on overlap in mistakes. It finds that "LLM-as-a-judge scores favor models similar to the judge". It also finds that models' mistakes grow more alike as capability rises, which it ties to "risks from correlated failures".
**Bears on our design. FLAG, and adopt its reporting practice.** Report architect/reviewer similarity alongside every catch rate.

**2.4 Kim et al., "Correlated Errors in Large Language Models" (ICML 2025, per arXiv).** Source: https://arxiv.org/abs/2506.07962
```bibtex
@misc{kim_correlated_2025,
  title  = {Correlated Errors in Large Language Models},
  author = {Kim, Elliot and Garg, Avi and Peng, Kenny and Garg, Nikhil},
  year   = {2025}, eprint = {2506.07962}, archivePrefix = {arXiv},
  note   = {Accepted to ICML 2025}}
```
The study covers more than 350 LLMs. On one leaderboard, models agree 60% of the time when both are wrong. Shared architecture and provider contribute to the correlation. Larger, more accurate models are highly correlated *even across* architectures and providers.
**Bears on our design. FLAG, with a qualification.** Same provider raises error correlation, so our constraint costs some independence. But switching to another family is not a full cure either. Independence has to come from **information and role separation plus deterministic checks**, not from model choice alone.

**2.5 Arnav et al., "CoT Red-Handed" (NeurIPS 2025, per arXiv).** Source: https://arxiv.org/abs/2505.23575
```bibtex
@misc{arnav_cot_2025,
  title  = {{CoT} Red-Handed: Stress Testing Chain-of-Thought Monitoring},
  author = {Arnav, Benjamin and Bernabeu-P{\'e}rez, Pablo and Helm-Burger, Nathan and Kostolansky, Tim and Whittingham, Hannes and Phuong, Mary},
  year   = {2025}, eprint = {2505.23575}, archivePrefix = {arXiv}}
```
Monitors that read the untrusted model's reasoning beat output-only monitors on *subtle* sabotage. But misleading rationalisations deceive them on *obvious* sabotage. A hybrid that scores reasoning and actions independently and then combines them beat both.
**Bears on our design. Adopt it.** This answers "is a reviewer that sees the generator's reasoning more persuadable?": yes, sometimes. Score the **graph alone** and the **graph plus architect rationale** as two independent verdicts, and never only the second.

**2.6 Ye et al., "Justice or Prejudice?" (2024).** Sources: https://arxiv.org/abs/2410.02736 and the HTML v2
```bibtex
@misc{ye_justice_2024,
  title  = {Justice or Prejudice? Quantifying Biases in {LLM}-as-a-Judge},
  author = {Ye, Jiayi and Wang, Yanbo and Huang, Yue and Chen, Dongping and Zhang, Qihui and Moniz, Nuno and Gao, Tian and Geyer, Werner and Huang, Chao and Chen, Pin-Yu and Chawla, Nitesh V and Zhang, Xiangliang},
  year   = {2024}, eprint = {2410.02736}, archivePrefix = {arXiv}}
```
The paper names 12 judge biases, including **authority** ("more credibility to statements made by authority figures"), tested by injecting fake citations, as well as self-enhancement and chain-of-thought biases.
**Bears on our design. Adopt it as a threat class.** Paper 3's "approved" pretext is an authority cue. The Paper 4 attack should place the pretext where the *reviewer* reads it too, not only where the architect does.

**2.7 Zheng et al., MT-Bench (NeurIPS 2023 D&B).** Source: https://arxiv.org/abs/2306.05685
```bibtex
@inproceedings{zheng_judging_2023,
  title     = {Judging {LLM}-as-a-Judge with {MT}-Bench and Chatbot Arena},
  author    = {Zheng, Lianmin and Chiang, Wei-Lin and Sheng, Ying and Zhuang, Siyuan and Wu, Zhanghao and Zhuang, Yonghao and Lin, Zi and Li, Zhuohan and Li, Dacheng and Xing, Eric P. and Zhang, Hao and Gonzalez, Joseph E. and Stoica, Ion},
  booktitle = {NeurIPS 2023 Datasets and Benchmarks Track},
  year      = {2023}, eprint = {2306.05685}, archivePrefix = {arXiv}}
```
GPT-4 as judge agrees with human preference over 80% of the time, matching agreement between humans. The paper names position, verbosity and self-enhancement biases.
**Bears on our design. Position against it.** It measures *preference* agreement on chat answers, not adversarial defect detection. Cite it for the existence of the biases, not as evidence that a reviewer will catch an attack.

**2.8 Rodriguez, Dearstyne and Cleland-Huang, traceability prompting (2023).** Source: https://arxiv.org/abs/2308.00229
```bibtex
@misc{rodriguez_prompts_2023,
  title  = {Prompts Matter: Insights and Strategies for Prompt Engineering in Automated Software Traceability},
  author = {Rodriguez, Alberto D. and Dearstyne, Katherine R. and Cleland-Huang, Jane},
  year   = {2023}, eprint = {2308.00229}, archivePrefix = {arXiv}}
```
Prompt engineering for LLM trace-link prediction. The authors say how best to use LLMs here "remains unclear".
**Bears on our design. Adopt the output form.** Make the reviewer emit explicit trace links: every capability in the graph links to a requirement sentence in the prompt. An untraced capability is a finding by rule.

UNVERIFIED, so no BibTeX: Bartel et al. on Android permission-gap reduction (ASE 2012); Docker seccomp-profile generation tooling; Inspektor Gadget's `advise seccomp-profile`.

## Suggested design consequences

1. **Isolate the reviewer by information, not only by model.** Its input is the PO prompt plus the *canonicalised* graph (regenerated pseudocode or JSON). It gets no architect prose, comments or rationale (redaction, per 2.1; persuasion, per 2.5 and 2.6). Add a second, rationale-aware score as a separate verdict.
2. **Validate the reviewer upfront on planted widenings**, in the AI Control style: a pinned corpus of graphs widened by hand, like our mutation corpus. Report its false-negative rate before any architect run, with a stop rule.
3. **Report reviewer–architect similarity and same-family status with every catch rate** (2.3, 2.4). State plainly that a Claude-reviews-Claude result is a **lower bound on independence**, and that a cross-family replication is the missing control.
4. **Exploit variation inside the family where it is cheap.** Paper 3 found a large between-model spread. Use the model *least* susceptible to the pretext as the reviewer, and say this is diversity within one family, not independence.
5. **Make traceability mechanical where possible.** The reviewer outputs capability→requirement links. A deterministic check then fails any capability with no link, so the LLM proposes and the check decides (per the project's "prefer mechanising" rule).
6. **Minimisation: static lower bound, trace as proposal.** Remove only authority that no reachable path in the component uses (1.3, 1.7). A trace-derived narrowing (1.4) is a *proposal* that must go back through steps 3–4 as a graph change, labelled with its observation window. Host-tier traces are never used.
7. **Never auto-widen from a denial** (1.6). A denied crossing produces an escalation request against the graph, never a grant.
8. **Name the blind spots up front**, as AWS does. These are the free-text residual, unreached branches, and below-kind authority (allowlist entries), which import-level minimisation cannot see.

## Open questions for the author

1. Is a cross-family control (one non-Claude reviewer, a small run, even with another person's access) acceptable as a *limitation check*, given the constraint? Without it, 2.2–2.4 leave the independence claim unfalsifiable.
2. Should the reviewer see the architect's rationale at all, or only in the second, separate score (consequence 1)?
3. For minimisation, is reachability inside a component in scope for Paper 5, or does it stop at interface-level imports, as WASI-Virt does?
4. Should the reviewer-validation corpus be authored by hand, by an adversarial model, or by both, and is it registered in advance like Paper 3's run?
