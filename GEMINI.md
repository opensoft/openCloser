<!-- SPECKIT START -->
Before changing this repository, read `.specify/memory/constitution.md` when present.
For feature-specific technologies, project structure, shell commands, and
other implementation details, read the current plan.
<!-- SPECKIT END -->

# openCloser Agent Context

openCloser is a CRM-first AI communication platform for healthcare-oriented
outreach. Read these project docs before creating or implementing specs:

- `docs/prds/openCloser_MVP.md`
- `docs/prds/openCloser_PRD.md`
- `docs/architecture/openCloser_Architecture.md`
- `docs/prds/ALF_Outbound_Appointment_Setter_PRD.md`

Spec Kit lives under `.specify/`. Feature work uses linked git worktrees.

## OpenSpec/Speckit Bench Runtime

Run OpenSpec and Speckit shell commands from the `py-bench` container when it is
available. In that bench, the root checkout is
`/workspace/projects/openCloser` and linked feature worktrees live under
`/workspace/projects/openCloser-worktrees`.

<!-- OPENSPEC-SPECKIT-GLOBAL:START -->
## Shared OpenSpec/Speckit Protocol

This repo uses the user-global OpenSpec/Speckit workflow instead of duplicating
process rules in every repository.

- Global agent entrypoint: `/home/brett/.agents/AGENTS.md`
- Workflow protocol: `/home/brett/.agents/protocols/openspec-speckit-workflow.md`
- Bootstrap contract: `/home/brett/.agents/protocols/project-agent-bootstrap.md`

Repo-local sections below remain authoritative for project-specific commands,
runtime prerequisites, source-of-truth docs, tests, and deployment constraints.
<!-- OPENSPEC-SPECKIT-GLOBAL:END -->

## Spec Kit Workflow Rules

Follow this sequence for feature work. Use the slash-command spelling supported
by the current agent, but keep the same order:

```text
/speckit.specify <description>   # from root checkout
cd <WORKTREE_PATH>                # or source .specify/shell/ct.zsh, then run ct
/speckit.clarify
/speckit.plan
/speckit.checklist <topic>        # decision required before tasks
/speckit.tasks
/speckit.analyze

/speckit.implement
```

Treat the full sequence as mandatory by default. Do not skip `clarify`, `plan`,
`tasks`, `analyze`, or `implement` just because the feature appears
straightforward. Do not skip the checklist decision step. Only skip a phase when
the user explicitly approves the skip, a repository-specific rule explicitly
says to skip it, or that phase is already complete and still current for the
active feature in the correct worktree.

Before `/speckit.specify`, verify `pwd` is the root checkout and
`git rev-parse --abbrev-ref HEAD` is `main`. Do not run specify from a feature
worktree.

Before every later Spec Kit command, verify `pwd` is the intended feature
worktree and `git rev-parse --abbrev-ref HEAD` is the correct feature branch.
Use `ctp` or `.specify/extensions/git/scripts/bash/get-last-worktree.sh --json`
to confirm the recorded worktree path when available. If a command was run in
the wrong checkout, stop and repair the git/spec artifacts before continuing.

Do not go from plan to tasks without explicitly deciding whether a checklist is
needed. Run `/speckit.checklist <topic>` for any known quality gate or risk area
and repeat it for multiple topics when useful.

<!-- OPENSPEC-SPECKIT-CLARIFY:START -->
## Speckit Clarify Question Presentation

These rules apply whenever `/speckit-clarify` (or the `speckit-clarify` skill)
runs and override the skill's defaults:

- **Question cap:** raise the maximum number of clarification questions from 5
  to **25** per clarification session.
- **Block form for multi-question rounds:** when a clarification round contains
  **more than one question**, present every question together as a single
  block — never one question at a time.
- **File + terminal:** write the full block of questions to a Markdown file in
  the active feature directory (e.g. `<FEATURE_DIR>/clarify-questions.md`), and
  send to the terminal BOTH (1) the full block of questions in block form and
  (2) the path of that questions file. This applies in addition to any
  interactive question prompt that may also be used.
- A round containing only a single question may be asked inline and does not
  require a file.
<!-- OPENSPEC-SPECKIT-CLARIFY:END -->

<!-- OPENSPEC-SPECKIT-CHECKLIST:START -->
## Speckit Checklist Default Coverage

These rules apply whenever `/speckit-checklist` (or the `speckit-checklist`
skill) runs and override the skill's defaults:

- The authoritative skill is the **user-global** `speckit-checklist` skill
  (installed under each agent's global skills directory, e.g.
  `~/.claude/skills/speckit-checklist/`). This block is a repo-local reminder
  that the global skill exists and is the source of truth for checklist
  behavior.
- **No-argument invocation means maximum coverage.** When `/speckit-checklist`
  is invoked with no domain/focus argument, it MUST skip the clarifying-question
  step and generate the broadest and deepest checklist set possible: one
  checklist file per requirement-quality domain the feature touches, at formal
  release-gate rigor, with no item-count cap and full scenario-class coverage.
- When an explicit domain or focus argument IS supplied, the skill scopes the
  run to that argument as normal.
<!-- OPENSPEC-SPECKIT-CHECKLIST:END -->
