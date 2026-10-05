---
name: compact-commerce-ui
description: Orchestrate the system-wide commerce-ui CLI and its versioned template packs to create or redesign readable, modular HTML reports, ecommerce dashboards, SaaS workbenches, analytics panels, and plugin interfaces. Use when an Agent needs HTML generation, report UI, template selection or creation, independent sidebar views, responsive components, self-contained image delivery, or deterministic HTML validation. This Skill owns business-to-ViewModel planning; commerce-ui template packs are the only HTML renderers.
---

# Compact Commerce UI CLI Orchestration

Select a suitable installed template pack, turn source evidence into that pack's versioned ViewModel, then let the CLI render and validate the HTML. If no suitable pack exists, create and install a reusable pack through the CLI lifecycle. Do not handcraft or copy HTML, CSS, JavaScript, templates, or validators into this Skill or a downstream business Skill.

## Source Of Truth

This Skill is distributed with the `commerce-ui` CLI. The path returned by `commerce-ui skill source` is the only editable source of truth. Agent Skill directories contain only CLI-managed links or copies. Never maintain an independent Agent-local fork.

The independently versioned npm package is `@petercjl/commerce-ui`. Domain shells register this component and delegate to its CLI; they keep this package's business resources canonical. Installation requires Node.js 20+ and Python 3.10+ with `jsonschema`. Run `commerce-ui runtime install --yes` when the required Python imports are missing. This creates a managed user environment. Package updates use `commerce-ui update check|install`; shell-owned installations update through their shell. Git-owned development sources update through Git.

Bundled template defaults update with the npm package. Custom packs and their backups live outside the installed package under the user data/state roots; `COMMERCE_UI_DATA_ROOT` may select a data root. Use the template lifecycle to create or update custom packs while preserving their contracts.

When an Agent can execute `commerce-ui` but does not have this Skill installed, discover and install it with:

```bash
commerce-ui skill source --json
commerce-ui skill status --target-dir <agent-skill-root>
commerce-ui skill install --target-dir <agent-skill-root>
```

Use `--agent codex`, `--agent agents`, `--agent openclaw`, or `--agent sealseek` for the built-in roots. Use `commerce-ui skill update` only for a managed copy; linked installations read this source immediately. Restart or refresh the Agent's Skill catalog when that host snapshots Skill metadata per session.

## Composition Interface

This Skill is the canonical Agent-facing capability named `compact-commerce-ui`; `commerce-ui` is its deterministic execution surface. A domain Skill that needs the shared HTML capability must resolve and load the current installed `compact-commerce-ui` Skill by exact name at execution time, then follow its current main flow. Do not copy a snapshot of these instructions into the domain Skill.

Loading a named Skill is an orchestration action, not an automatic dependency feature of the Agent Skills format. If the host provides a native Skill catalog or `load_skill` operation, use it. Otherwise resolve the exact Skill name from the host's advertised Skill catalog or configured Skill roots, read its complete `SKILL.md`, resolve its relative resources from that Skill directory, and execute it. Never select a similarly named Skill by fuzzy match.

Before rendering, the orchestrator must discover the live CLI rather than assume capabilities from an older prompt:

```bash
command -v commerce-ui
commerce-ui version --json
commerce-ui templates list --json
commerce-ui doctor
```

The composition contract is:

- **Logical capability:** `compact-commerce-ui`
- **Execution command:** `commerce-ui`
- **Required report contract:** the selected installed template pack's contract; the built-in default is `compact-workbench@1.0`
- **Input:** business evidence plus report intent, or a compatible Report ViewModel
- **Output:** a new ViewModel JSON file, a new self-contained HTML file, and validation results
- **Failure behavior:** report `DEPENDENCY_UNAVAILABLE`, `CLI_UNAVAILABLE`, or `CONTRACT_UNSUPPORTED`; do not silently embed a private renderer

An older domain Skill automatically benefits from compatible CLI improvements because it resolves `commerce-ui` from `PATH` and reads the live schema on every run. It benefits from updated orchestration guidance only when it loads this Skill at runtime. Incompatible contract changes are never automatic: keep the old contract available or update the domain Skill deliberately.

## Main Flow

1. **Check the execution surface.** Run `command -v commerce-ui`, `commerce-ui version --json`, and `commerce-ui doctor`. If the command is unavailable, report the missing dependency; do not silently recreate the renderer.
2. **Inspect the task and evidence.** Identify users, decisions, real top-level areas, metrics, tables, assets, time range, sources, limitations, and required actions. Never invent business conclusions to fill components.
3. **Select by semantic fit.** Run `commerce-ui templates list --json` and inspect candidate packs. Match the report's information architecture and content semantics, not merely its colors. Use the built-in `compact-workbench` for compact business workbenches with independent sidebar views. If no installed pack fits, follow **No Suitable Template Pack** below.
4. **Read the live contract.** Run `commerce-ui schema --template <template-id>` or copy it to a new path with `--output`. Treat the installed schema, pack manifest, and `commerce-ui contracts` output as authoritative.
5. **Design the ViewModel.** Map business content into the selected contract. Where the contract uses workbench navigation, top-level navigation items must be real independent views. Keep cards, tables, grids, and secondary controls inside their owning view. Add image assets with semantic roles and paths relative to the ViewModel when possible. For a conclusion-first report, apply the structured conclusion rule below before placing supporting metrics and evidence.
6. **Write a new JSON input.** Include the selected `contract` and all fields required by its live schema. Preserve data provenance or source hashes when reconciliation matters. Do not place secrets, credentials, or private filesystem paths in the resulting HTML.
7. **Render deterministically.** Run:

   ```bash
   commerce-ui render --input report.json --output report.html
   ```

   The CLI refuses to overwrite existing outputs. Select a new output path instead of bypassing this protection.
8. **Validate.** Run `commerce-ui validate report.html`. Then inspect desktop and mobile rendering, relevant interaction behavior, image loading, minimum readable text, horizontal overflow, and print visibility. Repair the ViewModel when the content mapping is wrong; update the selected shared pack only when its reusable renderer or contract is wrong.
9. **Deliver.** Report the JSON and HTML paths, CLI version, template pack ID/version, contract version, validation results, data reconciliation, and any intentional deviation.

Always return to this main flow after a branch.

## Structured Conclusion Rule

When a report leads with a decision or recommendation, make the opening view's conclusion a set of distinct, labeled judgments. For a `compact-workbench@1.0` pack whose live schema supports `conclusion`, use its `conclusion` block with at least two items. Give each item one short conclusion, such as a priority, a watch item, or a decision boundary; place detailed evidence in subsequent metrics, tables, cards, or views. Keep the view title short enough to locate the subject rather than making it carry the whole answer.

Write each conclusion item as typed text segments. Use `emphasis: strong` for the pivotal action, category, or number; `emphasis: italic` for a meaningful hypothesis or qualification; and `tone` to distinguish a supported opportunity from a caution or risk. Color is semantic and selective, while unmarked text remains readable in the default color. The renderer escapes the text and supplies the typography. Do not insert HTML or Markdown styling into ViewModel strings.

Before rendering, check that a reader can identify the separate conclusions at a glance and that no item has become a paragraph of chained claims. After rendering, visually inspect the emphasized text and contrast on desktop, mobile, and print. If the selected pack's live schema lacks the required structured or inline emphasis capability, use the **Selected Contract Cannot Express A Reusable Requirement** branch; do not claim the styling is present merely because the ViewModel mentions it.

## Ownership Boundary

The Agent and this Skill own flexible decisions:

- translating raw business data into report semantics;
- deciding which top-level views are real;
- choosing suitable components and information order;
- separating evidence, inference, caveats, and actions;
- creating the ViewModel and reconciling its values.

The `commerce-ui` CLI owns deterministic implementation:

- HTML, CSS, JavaScript, design tokens, and component markup;
- one-menu-item/one-view routing, active state, hash, history, and mobile drawer;
- responsive grids, typography, image embedding, printing, and static validation;
- template discovery, protocol versioning, trusted pack installation, recoverable pack updates, and refusal to overwrite.

Do not duplicate CLI-owned code in analysis Skills. Prefer loading this orchestration Skill by exact name. A domain Skill may directly produce the declared ViewModel and call `commerce-ui` only when it intentionally pins the public CLI contract and does not need the orchestration guidance.

## Branches

### Existing Analysis Skill

Keep domain analysis and source extraction in that Skill. Its HTML node must load `compact-commerce-ui` at runtime, then supply the business evidence and report intent. Replace copied HTML templates and rendering scripts with a ViewModel adapter plus `commerce-ui render` and `commerce-ui validate`. Return to Main Flow Step 7.

### No Suitable Template Pack

Do not inject raw HTML into a ViewModel or create a private renderer inside a domain Skill. First confirm that the mismatch is structural and likely to recur, rather than a one-off content variation. Then create a new editable pack outside the installed library:

```bash
commerce-ui templates scaffold --id <pack-id> --contract <pack-id>@1.0 --output <new-pack-dir>
```

Adapt its manifest, strict schema, template, renderer, validator, and representative fixture as one versioned unit. Keep business-specific facts out of the reusable pack. Run `commerce-ui templates validate --path <new-pack-dir>`, inspect its fixture visually, review its executable local code, then install with `commerce-ui templates install --path <new-pack-dir> --trust-local-code YES`. Run `commerce-ui self-test` and return to Main Flow Step 3. Never overwrite an installed pack by filesystem copy.

### Selected Contract Cannot Express A Reusable Requirement

Do not patch generated HTML. For a backward-compatible reusable improvement, update the selected pack's schema, renderer, validator, fixture, and version together, validate it, then use `commerce-ui templates update --path <pack-dir> --trust-local-code YES`. For an incompatible ViewModel change, publish a new contract version and normally a new pack ID so older reports remain reproducible. Return to Main Flow Step 3.

### Explicit Alternate Style

If the user explicitly requests another style, select its installed template pack or named external workflow. Do not force Compact Commerce UI. If only brand colors or labels differ, express them through supported ViewModel fields rather than creating another pack. Return to Main Flow Step 3.

### Continuous Long-Form Document

Do not fake an article, landing page, evidence dossier, or print-first document with the workbench contract. Select a fitting installed pack; if this is a recurring HTML structure and none exists, follow **No Suitable Template Pack**. If the user explicitly chose another rendering system, use that execution surface instead.

## Completion Contract

A completed report must:

- declare an installed `commerce-ui` contract and record the CLI, template pack, and contract versions;
- contain only real views, data, assets, and working controls;
- keep exactly one top-level view visible on screen and all views available for print;
- preserve source totals, units, time range, caveats, and evidence meaning;
- present conclusion-first reports as labeled conclusion items with visible, semantic color, weight, and italic emphasis before their supporting evidence;
- be self-contained unless the user explicitly approves external dependencies;
- pass `commerce-ui validate` and an actual desktop/mobile interaction inspection.
