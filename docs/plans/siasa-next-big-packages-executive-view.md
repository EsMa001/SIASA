# SIASA Executive View: Next Big Packages

> Steering note: `docs/plans/siasa-master-steering-document.md` remains the single steering document. This file is a compact project-lead communication layer for the next large package families.

Created: 2026-06-11
Purpose: Summarize the next major SIASA package families in one page with target state, user value, main risks, dependencies, recommended order, and the next concrete bounded package focus.

---

## 1. Recommended order

1. G1 – Runtime breadth and live evidence expansion
2. G3 – Operational evidence-lane normalization / truthfulness support
3. G4 – Approval-to-distribution release lifecycle closure
4. G2 – External credentialed-source activation follow-through (conditional trigger)
5. G5 – Optional server-backed multi-user governance

Important interpretation:
- G2 is no longer the next default repo package family: repo-controlled closure is now materially complete because blockers, country scope, next actions, and activation-vs-evidence truth are explicit.
- G2 jumps ahead of the queue only if valid ReliefWeb/UCDP credentials or equivalent provider registrations become available and materially change the reachable runtime/source breadth.

---

## 2. Executive package view

| Package | Target state | Main user value | Main risks | Dependencies / gating | Relative size | Recommended next bounded package |
| --- | --- | --- | --- | --- | --- | --- |
| G1 – Runtime breadth and live evidence expansion | SIASA runs repeatably across broader governed MVP/P2 multi-country slices with honest degraded-mode semantics and explicit C/E usage truth under real live conditions. | Largest remaining product-reach increase; proves SIASA is operational beyond already-proven subsets. | Rate limits, source instability, false-green runtime evidence, long-running live probes. | Existing governed runtime/verifier path already in place; depends mainly on runtime stability and bounded slice choice, not on new architecture. | XL | Next broader governed live-runtime slice with fresh evidence package and explicit degraded-mode / C-E truth checks. |
| G3 – Operational evidence-lane normalization / truthfulness support | Operators and project lead always get one authoritative, fresh, low-ambiguity evidence lane that matches the current governed runtime and release truth. | Keeps steering honest while broader runtime slices expand; reduces drift between code closure and fresh evidence. | UX-heavy progress without enough value if detached from real runtime evidence; can become report-polish work if not kept bounded. | Best when paired with G1/G4 work that needs fresh truthful handoff and review surfaces. | M | Next bounded evidence-lane truthfulness slice that reduces ambiguity in fresh run review or handoff. |
| G4 – Approval-to-distribution release lifecycle closure | SIASA does not stop at readiness/blocking assessment; it records the actual lifecycle transition from pending sign-off to approved to distributed. | Closes the management gap between “ready for decision” and “actually governed and sent”. | Governance-only progress without enough prior runtime/source breadth closure; process complexity. | Strong readiness/release package baseline already exists; best started after G1/G3 no longer dominate the value frontier. | L | Add explicit approval/distribution state model and closure artifact chain for one governed release packet path. |
| G2 – External credentialed-source activation follow-through | Credential-gated sources such as ReliefWeb/UCDP move from repo-ready and truthfully classified into live operational evidence once external credentials/registrations are actually provided. | Converts repo completeness into real source breadth exactly when the external dependency becomes available. | External credential/registration delays, provider policy changes, apparent activation without durable operational value. | Repo-controlled G2 closure is complete; valid credentials / app registrations are now the hard gate. | S (internal) / M (with live run) | When credentials arrive: run one governed activation slice for the highest-value blocked source class and capture explicit source-success evidence. |
| G5 – Optional server-backed multi-user governance | SIASA evolves from strong local governed bundles to shared multi-user operation with authn/authz, persistence, and reviewer workflows. | Enables true team operation and persistent collaborative governance. | Large architecture jump, higher complexity, risk of solving for a target operating model that is not yet required. | Only justified if the target operating model explicitly requires multi-user/server-backed deployment now. | XL | Architecture decision slice: confirm operating model, scope authn/authz + persistence boundary, and decide whether to start at all. |

---

## 3. Why this order is recommended

### First: G1
Because it is the largest remaining stakeholder-value gap:
- it increases actual product reach
- it tests the system under real operational conditions
- it provides the strongest evidence that SIASA is useful beyond curated/proven subsets

### Second: G3
Because truthful steering is now the next highest-value repo-controlled support lane:
- broader runtime slices need fresh, low-ambiguity operator evidence
- it reduces drift between “implemented” and “currently evidenced”
- it stays directly useful while G2 waits on external credentials

### Third: G4
Because the release/productization layer is already strong:
- the remaining high-value increment is lifecycle completion
- this is more important than further summary-panel expansion
- it becomes most valuable once runtime/source breadth is credible enough to distribute

### Fourth: G2
Because the repo-controlled part is now complete and the remainder is an external trigger:
- SIASA now explicitly distinguishes configured, externally blocked, failed, and live-evidenced credential-gated sources
- the next G2 step is not another internal ambiguity fix but actual credential onboarding plus one governed live activation run
- this can reprioritize sharply upward as soon as credentials exist

### Fifth: G5
Because it is strategically meaningful but not yet the default need:
- it is a major architecture uplift
- it should follow explicit operating-model demand
- otherwise it risks premature complexity

---

## 4. Program-level Go / No-Go criteria

### G1 Go / No-Go
Go when:
- the next broader slice is bounded and operationally meaningful
- live evidence can be produced with honest degraded-mode semantics
- verification remains fail-closed by default and explicit under override

No-Go when:
- the broader slice would mostly generate noise without usable evidence truth
- runtime instability is so high that the package would not produce a reviewable bounded outcome

### G2 Go / No-Go
Go when:
- valid credentials / registrations are available
- the source can be activated in governed live runs with explicit evidence

No-Go when:
- the only likely output is “adapter technically enabled” without reliable operational value

### G4 Go / No-Go
Go when:
- runtime/source breadth is no longer the dominant program bottleneck
- there is a real need to close the external review/distribution path

No-Go when:
- the package would mainly add governance ceremony ahead of operational substance

### G5 Go / No-Go
Go when:
- the target operating model explicitly requires multi-user/server-backed deployment
- persistence, roles, and reviewer workflows are now real product requirements

No-Go when:
- local/static governed bundles remain the intended operating model for the current phase

---

## 5. Steering conclusion for project lead

If the question is “what are the next really big packages?”, the answer is:
- the next true major block is G1 runtime breadth expansion
- the strongest external unlock is G2 credentialed source activation
- the biggest governance-completion package after that is G4 approval-to-distribution closure
- G5 remains strategically important but intentionally deferred until the operating model demands it

Short form:
- Biggest value lever now: G1
- Biggest external unlock: G2
- Biggest lifecycle closure lever: G4
- Biggest architectural lever, but later: G5
