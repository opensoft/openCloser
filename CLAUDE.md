<!-- SPECKIT START -->
Before changing this repository, read `.specify/memory/constitution.md` when present.
For feature-specific technologies, project structure, shell commands, and
other implementation details, read the current plan:
`specs/002-mock-call-real-crm/plan.md` (Slice 2 — Mock Call, Real CRM).
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
