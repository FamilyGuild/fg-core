# FamilyGuild Core - Agent Guidelines

## Scope

`fg-core/` is the planned thin foundation app for FamilyGuild.

It should provide only the shared shell needed by the current MVP:

- one family workspace,
- family/member setup,
- trusted member switching,
- settings shell,
- module navigation,
- general dashboard shell,
- enabled module entry for KidLand.

## Current MVP Constraint

Do not build production login/authentication for the first private family test.

Use trusted member switching because the founder's own family is the first test environment.

## Boundaries

- Keep FamilyGuild Core thin.
- Do not move KidLand domain logic into the core.
- Do not build full plugin/module marketplace behavior yet.
- Do not build a complex permission engine until a concrete workflow needs it.
- Ask before modifying sibling modules such as `kidland/` or `famledger/`.

## Source of Truth

- Workspace rules: `../AGENTS.md`
- Architecture: `../fg-docs/docs/architecture/modular-platform.md`
- MVP plan: `../fg-docs/docs/product/mvp-plan.md`
- Product strategy: `../fg-docs/docs/product/strategy.md`
