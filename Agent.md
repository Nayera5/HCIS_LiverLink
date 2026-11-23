# CLAUDE.md

## Project Reference

The full project specification lives in [LiverLink.md](LiverLink.md).

Do not load it by default. Read `LiverLink.md` only when you need project details — requirements, features, data model, architecture, or domain context for HCIS LiverLink — to complete a task.


## Development rules

- Don't invent requirements. If something isn't documented, ask.
- Don't add major frameworks, dependencies, or architectural changes without
  explaining the reason and getting agreement first.
- Prefer small, explicit changes over large refactors.
- At end of the chat give a summary of what files did u change.
- When a decision is made, record it in `decisions.md`
  (date, decision, reason) and update the Tech stack table above.
- Before creating any new files, ask for my permission first and provide a simple, clear explanation of the purpose of each file.
<!-- - Keep `Features.md` (feature inventory) up to date: when a feature is added, changed or completed, update its
  row (or add one with the next ID in its category, no duplicates) and the "Last updated" date. -->
- make the code as simple and understandable as possible.

## When implementing a feature, follow this workflow:

1. **Understand first:** Inspect the existing codebase, architecture, relevant files, and dependencies before making changes. Ask questions if requirements are unclear.
2. **Plan:** Propose a short implementation plan, identify affected files, edge cases, and risks. Wait for my approval before starting substantial changes.
3. **Implement carefully:** Follow existing conventions, keep changes focused, avoid unnecessary refactoring, and preserve existing behavior.
4. **Handle errors and security:** Validate inputs, handle expected failures, enforce authorization where needed, and never expose secrets.
5. **Protect existing work:** Check Git status first. Never discard, overwrite, commit, push, or revert my changes without permission. Never perform destructive database operations without explicit approval.
6. **Test:** Run relevant tests, linting, type checks, and builds. Add tests for the feature and fix issues caused by your changes.
7. **Explain:** Summarize what was implemented, which files changed, what did u change in the code, important design decisions, commands/tests run, and any remaining issues.

Do not claim that something works or that a test passed unless you have verified it. Prefer simple, maintainable solutions that fit the existing project instead of introducing unnecessary dependencies or complexity.
