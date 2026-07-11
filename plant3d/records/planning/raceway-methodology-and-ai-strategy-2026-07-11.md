# Raceway 3D Methodology Review & AI Strategy

Date: 2026-07-11
Author: Claude (architect/researcher), at KR's request
Audience: KR + Codex
Status: research RFC — analysis and staged proposals, not an instruction to build

> Two questions from KR: (1) independently assess our current raceway-drawing methodology against how PDMS/E3D, SP3D, Bentley, and Revit do it, and propose improvements fitted to our use case; (2) research how AI (on-prem or online) can give the product a significant edge, including an updated status check on vendor AI products. Sources are cited inline; vendor claims were verified by web research on 2026-07-11.

---

## Part 1 — Our methodology vs. the incumbents

### 1.1 What we have today (honest recap)

Palette (family/size/service/EL) → Start → click centerline nodes on a locked elevation plane → finish; select/move/delete/undo nodes; anchor a node to a plant3d model object (adopts the object's elevation); parametric proxy rendered from catalogue dimensions (bottom-reference plane, rails/rungs upward); save/reload/delete through the raceway JSON API; source-frame persistence; live length/bend/warning feedback; dirty-state tracking.

### 1.2 How the incumbents author raceway, and what each got right

**AVEVA PDMS/E3D.** Catalogue/spec-driven routing (like piping branches); the decisive concept is the **cableway network**: cableways/trays are modeled first as a connected network, then cables are *batch-routed through that network* by shortest path with fill checking. This is exactly the raceway-first philosophy our reset adopted — the market leader in plant design agrees with our pivot. Weaknesses: heavyweight UI, high training cost, checks are batch-run rather than live. AVEVA's own 2026 AI push (below) confirms routing automation is where they see the value.

**Hexagon SP3D/Smart 3D.** Route-by-path with automatic spec-driven fitting insertion; straight sections are split to manufacturing lengths *at drawing/report time* — i.e., **route is truth, parts are derived**, the same principle we adopted. Its signature strength is **associativity**: trays hold relationships to structure, so moving a beam moves the tray. Our `anchor` field is the seed of the same idea; live re-resolution is the (correctly deferred) endgame.

**Bentley Raceway and Cable Management (BRCM).** The closest functional analogue to our target: purpose-built raceway networks with automatic drops/risers, cable routing through the network with **fill and segregation checks**, raceway schedules and **cable pull cards** as first-class deliverables. Lesson: the deliverable set (schedules, fill reports, pull cards) is what buyers evaluate — our Phase F/9 BOQ direction is right, and pull cards should eventually join the list.

**Autodesk Revit MEP.** Cable tray drawn in plan view at a set elevation with width/height, **fittings auto-inserted at direction changes**, service-based coloring/filters. Natively weak on cable management (filled by third parties — see Augmenta below). Lesson: Revit's plan-view + fixed-elevation workflow is the same 2.5D discipline we chose — independently validated.

### 1.3 Gap analysis → ranked methodology improvements

Everything below fits the existing staging; none of it revives autorouting.

| # | Improvement | Why | Effort/stage |
|---|---|---|---|
| M-1 | **Ortho/axis lock + angle snap while drawing** | Plant trays run orthogonal to plant grid; free clicking produces sloppy geometry every incumbent avoids. We already have ortho-assist concepts in the EHT tool — same optional-and-explicit rule. | Small; next UX pass |
| M-2 | **Typed segment entry while drawing** (length + direction, or dx/dy) with per-segment dimension readout | Engineers think in distances ("6 m east, then riser"); E3D/S3D both allow coordinate/distance entry. Cheap and reads as professional-grade. | Small; next UX pass |
| M-3 | **Junction/branch semantics** — snapping a run's end/start node onto an existing run creates a shared node (tee) and splits the target run's edge | **The most important one.** Real networks are graphs, not isolated polylines; without shared nodes, Phase H cable assignment has no network to traverse. E3D cableways and BRCM are network-first for this reason. Schema is ready (stable node keys exist precisely for this). | Medium; should be the next *authoring* mode |
| M-4 | Riser command (elevation change at a node) | Already planned (v2); BRCM's auto-drop is its mature form. | Medium; planned |
| M-5 | **Parallel-offset duplicate** of a run (lateral spacing, N copies) | Multi-tier tray racks are the norm in plants; this single command replaces the most repetitive real-world task. | Small-medium |
| M-6 | Plan-view camera preset + EL grid while drawing | Top-down authoring is how every incumbent's users actually lay out trays. | Small |
| M-7 | Auto-fitting materialization at bends | Already planned Phase F/9 — keep as staged; borrowed pattern from Revit/S3D. | Planned |
| M-8 | Associative re-resolution of anchors; auto-support spacing; fill from assigned cables | Correctly deferred; S3D/BRCM parity items for later. | Deferred |

Recommendation: M-1, M-2, M-6 as one "drawing feel" pass; M-3 as its own pass (it touches schema semantics: node sharing/junction kind); M-5 after M-3 (offset copies should share junction logic).

### 1.4 What a web/cloud application can do that desktop incumbents structurally cannot

Restating and extending the earlier analysis (cable-routing vision RFC §3), with one important 2026 correction:

1. **Zero-install, link-based review** — any stakeholder opens the live model in a browser; no licenses/installs/GPU workstations. Still true and still decisive for EPC review cycles.
2. **One integrated data model** — line list → heat-loss calc → tracer/cold-cable sizing → SLD → BOQ/schedule → 3D raceway → (future) cable assignment in one database. Incumbents split this across E3D/BRCM + Excel + ETAP + document tools. This chain, not any single feature, is the product.
3. **Ambient live compliance** (per-route HUD → project health panel) vs. the incumbents' batch checkers.
4. **Scenario branching** — cheap draft snapshots, side-by-side comparison; single-timeline desktop tools can't.
5. **Explainable suggestions + accept/reject telemetry** — a fleet-wide learning loop desktop per-seat licensing can't aggregate (this becomes the AI flywheel, Part 2).
6. **Live multi-user collaboration** — still the biggest long-term differentiator, still correctly gated behind infra decisions.
7. **Continuous deployment** — weekly product improvement vs. annual desktop releases.
8. **⚠ Correction:** "browser-based" alone is no longer a differentiator — **Augmenta's ACP runs entirely in the browser** and is commercial. The moat must come from items 2, 5, and Part 2's deployment flexibility, not from "web" per se.

---

## Part 2 — AI strategy

### 2.1 Vendor AI status (verified 2026-07-11) — the "nobody has launched AI" assumption is now outdated

| Vendor | Status (mid-2026) | Relevance to us |
|---|---|---|
| **Augmenta** (startup) | **Commercially shipped.** ACP 2.0 (June 2026): AI-native, browser-based, *agentic* electrical raceway/conduit design — overhead + underground, real-time clash vs. full 3D background, Revit-integrated; claims 25% faster design, 15% less material. | **The pace-setter and closest comp** — but targets commercial buildings / electrical contractors / NEC / prefab VDC, not industrial EPC plants |
| **AVEVA** | **Commercially launched Jan 2026:** first AI wave in Unified Engineering — industrial AI assistant, **generative pipe routing** (Pre-FEED/FEED), AURA AI companion, AI drawing automation | Closest incumbent move in *our* plant domain; piping first, raceway/cable not yet |
| **Bentley** | Bentley Copilot (LLM-agnostic) embedded in next-gen apps; OpenSite+ (civil) in limited availability; Copilot to OpenRoads/OpenRail early 2026 | Assistant-style AI, civil-first; nothing raceway |
| **Hexagon** | HxGN Alix assistant rolling across the ALI portfolio; EcoSys 9.4 AI (Jan 2026) for project performance | Ops/PM-side AI; Smart 3D has no published AI routing |
| **Autodesk** | Revit 2026 ships stronger MEP auto-routing (duct/pipe around obstructions) under the "Autodesk AI" umbrella; cable-tray AI left to ecosystem plugins | Platform is ceding our niche to partners like Augmenta |
| **ETAP/Schneider** | Electrical **digital twin** with NVIDIA Omniverse for AI-factory power, grid-to-chip (Mar 2025); OpenUSD alliance with AVEVA (Nov 2025) | Simulation-side, data-center focus — adjacent, not authoring |

Read on the market: the window where "AI in electrical 3D design" was empty has **closed** in commercial buildings (Augmenta) and is closing in plant piping (AVEVA). It is **still open in industrial-plant electrical raceway + heat tracing + IEC markets** — our exact niche. Nobody grounds AI on an integrated calc-to-BOQ engineering chain, and nobody offers it on-prem.

### 2.2 Where our edge actually is

1. **Evidence-grounded AI, not generative-first.** Every calculation in eTrace already persists its basis/evidence JSON (a discipline we've enforced since the SR/MI/cold-cable engine). An assistant that *narrates, checks, and cross-references stored evidence* ("why was 3C×2.5 selected for this branch? what changes if route length doubles?") has near-zero hallucination surface and matches engineering sign-off culture. None of the vendor copilots can do this because none of them owns the calculation chain.
2. **The data flywheel we can start owning now.** Our decided principle — *software suggests, engineer accepts/edits* — is also the perfect training-data generator. Every suggestion shown, accepted, rejected, or edited is a labeled example. Cloud-native means we can (with consent) learn across projects; per-seat desktop tools structurally cannot. **The cheapest "be ahead" move is to design the telemetry schema before the first suggestion feature ships**, so no early signal is lost.
3. **On-prem / offline AI as a procurement differentiator.** Our target markets (Middle East NOCs, Asian EPCs, European operators) routinely prohibit uploading plant models to third-party clouds — export control and confidentiality. Augmenta is cloud-only; vendor copilots are hyperscaler-bound. An **AI gateway seam** (provider-agnostic, same pattern as `project_gateway`) that can run against a local model (vLLM/Ollama-served open-weights) *or* a cloud API makes "AI even inside your fence" a bid-winning line item.
4. **The raceway graph we are already building is the AI substrate.** Learned route-cost ranking, fill/clash risk prediction, and network synthesis all require exactly what Phases F–I produce: a connected graph with explicit costs and explainable suggestions. **Our current staging *is* the AI-readiness plan.** No pivot needed — that is the strategic reassurance from this research.

### 2.3 Staged AI roadmap (gated, no MVP disruption)

**Tier 0 — design now, costs almost nothing:**
- Suggestion telemetry schema (suggestion id, context features, shown/accepted/rejected/edited, edit delta) — adopt with the *first* suggestion feature, whichever it is.
- Keep the evidence-JSON discipline absolute (it is the future RAG corpus).
- One decision record: AI access goes through a provider-agnostic `ai_gateway` seam; on-prem capable; no domain logic coupled to any AI vendor.

**Tier 1 — first shippable AI (post-MVP, weeks not months, low risk):**
- **Natural-language model query**: "isolate all power trays on EL +106.5 with more than 3 bends" → intent parsed to our existing filter/layer/selection DSL. Viewer infrastructure already exists; this is the highest wow-per-effort feature in the whole list and none of the incumbents' viewers do it.
- **Evidence narrator**: explain any sizing/selection/BOQ line from stored evidence, with citations to the manual/design guide.
- **Line-list intake copilot**: column-mapping and anomaly flags (outlier temps, impossible lengths) on Excel upload — the messiest real-world step in every project, human-confirmed per our rules.
- Help/FAQ assistant grounded on our own manuals.

**Tier 2 — ML on the graph (after Phase H exists):**
- Learned re-ranking of Dijkstra route candidates from Tier-0 telemetry.
- Fill/congestion/clash-risk prediction as ambient warnings.

**Tier 3 — network synthesis (gated on Phases H–I being proven):**
- Generative raceway topology proposals: given DB/JB/equipment locations, propose 2–3 network alternatives **with BOQ/cost deltas and reasons**; engineer picks one and edits. This is the Augmenta-class capability, delivered for industrial plants, explainable, and optionally on-prem. Only attempted once the graph + cost model exist — the same discipline that made us reject premature autorouting still applies to premature *AI* autorouting.

**What we deliberately do NOT do:** train custom geometry foundation models; chase "agentic" marketing before Tier 1 earns trust; let any AI output commit a design without explicit acceptance (our existing product principle already covers this); couple to one AI vendor.

### 2.4 Honest risk notes

- Augmenta could pivot to industrial plants; AVEVA could extend generative routing from pipe to raceway. Our defense is speed on the integrated chain plus the IEC/EHT domain data they don't have — not secrecy.
- Tier 1 features need an LLM budget and a confidentiality stance per deployment; the gateway seam is what keeps both choices reversible.
- AI features must never jump the MVP queue: nothing in this document precedes the raceway MVP phases already agreed.

---

## Recommended next actions (in order, none disruptive)

1. KR/Codex: read this RFC; agree/disagree on M-1..M-6 sequencing (M-3 junctions is the one with schema implications and the one I'd prioritize).
2. Codex, when the next suggestion-like feature lands (even ortho-snap "did the user keep it?"): add the Tier-0 telemetry event table alongside it.
3. Add decision record `0007-ai-gateway-seam.md` when (and only when) the first Tier-1 feature is scheduled — the decision content is §2.2/§2.3 of this file.
4. I can draft, as parallel work on request: the viewer-extension contract one-pager (already offered in claude-notes §16), a Tier-1 NL-query intent-DSL design note, or the M-3 junction semantics design note for Codex.

## Sources

- [Augmenta ACP 2.0 release (June 2026)](https://www.globenewswire.com/news-release/2026/06/17/3313424/0/en/Augmenta-Releases-ACP-2-0-the-Complete-AI-Native-Design-Environment-Built-to-Multiply-Electrical-VDC-Team-Output-and-Capacity.html) · [Augmenta electrical](https://www.augmenta.ai/electrical) · [AEC Magazine on Augmenta's agentic electrical design](https://aecmag.com/mep/agentic-ai-accelerates-electrical-design/) · [ConstructConnect on Augmenta in pre-construction (Feb 2026)](https://canada.constructconnect.com/dcn/news/technology/2026/02/how-augmentas-ai-is-rewriting-electrical-pre-construction)
- [AVEVA AI for Unified Engineering press release (Jan 2026)](https://www.aveva.com/en/about/news/press-releases/2026/aveva-unveils-new-artificial-intelligence-offering-across-its-unified-engineering-solution/) · [AVEVA industrial AI for engineering](https://www.aveva.com/en/solutions/digital-transformation/artificial-intelligence/industrial-ai-for-engineering/) · [AVEVA blog: AI-driven Unified Engineering](https://www.aveva.com/en/perspectives/blog/the-future-of-ai-driven-unified-engineering-is-here/)
- [Bentley Copilot docs](https://docs.bentley.com/LiveContent/web/OpenSite+-vlatest/Help/en/topics/bentley_ai_copilot.html) · [Bentley AI applications news](https://www.bentley.com/news/bentley-systems-advances-infrastructure-ai-with-new-applications-and-industry-collaboration/) · [AEC Magazine: Bentley shapes its AI future](https://aecmag.com/ai/bentley-systems-shapes-its-ai-future/)
- [Hexagon HxGN Alix launch](https://hexagon.com/company/newsroom/press-releases/2024/hexagon-launches-hxgn-alix) · [Hexagon EcoSys 9.4 AI release (Jan 2026)](https://hexagon.com/company/newsroom/press-releases/2026/hexagon-advances-enterprise-project-performance-with-ai)
- [Revit 2026 what's new (MEP auto-routing)](https://archilabs.ai/posts/whats-new-in-revit-2026) · [Autodesk Revit MEP](https://www.autodesk.com/products/revit/mep)
- [ETAP + Schneider + NVIDIA electrical digital twin (Mar 2025)](https://etap.com/company/news/in-the-news/2025/03/13/etap-introduces-world-s-first-electrical-digital-twin-to-simulate-ai-factory-power-from-grid-to-chip-level-using-nvidia-omniverse)

---

## Codex Addendum — AI Edge and Immediate Product Implications

Date: 2026-07-11
Author: Codex
Status: additive strategy note after reading Claude's RFC; not a coding
instruction by itself

### C-1. My independent read

Claude's core conclusion is right: the market has moved faster than the old
"nobody has AI in this space" assumption. Augmenta is especially important
because it proves that browser-based AI raceway/conduit generation is already
commercially credible; AVEVA proves that the industrial incumbents are moving
AI into engineering design, not only document search; Bentley proves that
copilot-style assistance is becoming normal UI, not a novelty. I spot-checked
the vendor pages on 2026-07-11: Augmenta positions ACP around automated
raceway modeling, clash-free routing, Revit import/export, live clash review,
and browser access; AVEVA describes generative/predictive design intelligence
inside Unified Engineering/E3D Design; Bentley documents Bentley Copilot in
OpenSite+.

The strategic lesson is not "copy them." It is: build where our data model is
hard for them to copy quickly.

### C-2. The product moat should be the engineering chain, not the viewer

Our moat is the closed loop:

1. engineering input data,
2. SR/MI/cold-cable sizing evidence,
3. SLD topology,
4. cable schedule and BOQ,
5. 3D raceway graph,
6. cable assignment,
7. pull card / installation package,
8. engineering change trace.

Desktop incumbents have powerful geometry kernels, but their engineering
evidence is usually split across Excel, ETAP, cable-management packages,
drawings, and human memory. AI on top of disconnected files becomes a search
assistant. AI on top of our integrated chain can become an engineering
co-worker that explains consequences.

The first AI features should therefore answer consequence questions, not draw
dramatic geometry:

- "Which cables are affected if this tray moves from EL 105.0 to EL 106.5?"
- "Which branch circuits exceed the voltage-drop margin if the route grows by
  15 m?"
- "Show raceway runs where fill, segregation, bends, or pull length are
  becoming risky."
- "Generate a pull-card draft for this routing revision and cite the schedule
  rows used."

This is harder for Augmenta/desktop tools because they do not own the
calculation-to-installation chain.

### C-3. Practical AI architecture for a one-person-plus-agents team

Do not start with model training. Start with three small seams:

1. `ai_gateway`: provider abstraction, deployment policy, audit log, prompt
   template registry, response schema validation.
2. `suggestion_event`: every recommendation shown to the engineer records
   context, proposed action, accepted/rejected/edited outcome, and edit delta.
3. `evidence_bundle`: deterministic server-side packers that collect the
   exact calculation rows, object ids, standards references, route metrics, and
   warnings an AI is allowed to see.

This gives us an agent platform without pretending we have a large AI team.
The engineering engine remains deterministic; AI works on top of curated
evidence and proposes actions.

### C-4. What I would do differently from competitors

- **Explainability first:** every suggestion should cite project evidence and
  name uncertainty. "I think" is not acceptable for sign-off; "based on these
  schedule rows, these route lengths, and these limits" is acceptable.
- **On-prem capable from day one of AI:** make the gateway provider-agnostic so
  cloud APIs and local LLM servers are deployment choices, not rewrites.
- **Action proposals, not auto-commits:** AI can create a proposed route,
  filter, report, or revision bundle, but the engineer accepts it explicitly.
- **Engineering-memory accumulation:** the system should remember accepted
  project conventions: preferred tray corridors, standard elevations, service
  segregation habits, client-specific pull-card formats, and review comments.
- **Agent roles as product roles:** estimator agent, routing-check agent,
  pull-card agent, reviewer agent, change-impact agent. Each has a narrow
  schema and can be tested.

### C-5. Immediate coding implication for Raceway

Claude's M-1/M-2/M-6 sequencing is the right near-term move. Before AI can
suggest or learn useful routing behavior, the manual authoring tool must
produce clean engineering intent:

- orthogonal/axis-locked segments,
- typed segment entry,
- explicit riser/bend semantics,
- eventually shared junction nodes.

That is not just UX polish. It is training-data hygiene. Sloppy free-click
polylines create noisy examples; clean axis-locked, intent-labeled segments
create the graph an AI can safely learn from later.

### C-6. Extra sources spot-checked by Codex

- [Augmenta Electrical](https://www.augmenta.ai/electrical)
- [AVEVA Industrial AI for engineering](https://www.aveva.com/en/solutions/digital-transformation/artificial-intelligence/industrial-ai-for-engineering/)
- [Bentley Copilot docs](https://docs.bentley.com/LiveContent/web/OpenSite+-vlatest/Help/en/topics/bentley_ai_copilot.html)

---

## Status log (living document — append as items move)

| Date | Item | Status |
|---|---|---|
| 2026-07-11 | Codex addendum C-1…C-6 appended | Converged; `evidence_bundle` seam and consequence-questions-first adopted into shared strategy (claude-notes §18) |
| 2026-07-11 | M-1 ortho assist + M-2 typed segment entry (first slice) | **Shipped** (`a87115c`); ortho deliberately skips anchored points (training-data hygiene per C-5) |
| 2026-07-11 | M-3 junctions | Adopted as **Stage 8A** in the execution plan (graph projection, crossings ≠ connections, explicit acceptance); pre-coding notes in claude-notes §18 (tolerance constant, riser-kind policy) |
| 2026-07-11 | Viewer extension contract one-pager | **Written** (`viewer-extension-contract-2026-07-11.md`); G-1 partially shipped as `modelAnchorFromViewerEvent`; full G-1 (surface normal) + G-2 (pointer-move) reserved |
| 2026-07-12 | M-3 junctions — first slice | **Shipped**: `raceway/graph.py` projection (10 mm named tolerance, geometry-derived kinds, deterministic), `Connect Node` endpoint-join workflow, crossing/zero-length warnings; mid-run tee/split deferred deliberately; Claude review in claude-notes §19 (N-09 durable-key rule, N-10 near-miss warning) |
| 2026-07-12 | Stage 9 BOQ v0 — schedule payload | **Shipped** (`raceway/schedule.py` + `/layers/<id>/schedule/`): runs/segments/fitting-placeholders/groups/totals with UUID traceability and machine-readable assumptions; N-09/N-10 closed. Claude payload-shape review in claude-notes §21: add piece/offcut counts (S-1), generation envelope (S-2), graph-quality summary (S-3), tee-omission line (S-4) **before** HTML/CSV UI |
| — | M-4 riser command / M-5 parallel offset / M-6 plan view | Open; M-4 partially superseded by multi-elevation authoring (typed `±EL` segments) |
| — | Tier-0 telemetry schema (`suggestion_event`) | Open — adopt with the first suggestion feature (ortho keep/undo signals may qualify) |
| — | `ai_gateway` decision record (0007) | Open — write when first Tier-1 feature is scheduled |
