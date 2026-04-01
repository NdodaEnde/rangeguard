---
name: do-verify-move
description: Enforces the Do → Verify → Move workflow for every task
---

# Workflow Rule: Do → Verify → Move

## Core Principle
Never start the next task until the current task is verified and passing. Unverified work compounds into broken systems.

## Required Workflow

### 1. DO — Pick one task, implement it
- Mark the task `in_progress` in the todo list before writing any code.
- Only one task should be `in_progress` at a time.
- Stay focused on the single task. Do not drift into adjacent work.
- Read existing code before modifying. Understand the pattern before extending it.

### 2. VERIFY — Confirm the task works
Before marking a task as `completed`, you MUST run `/verify` or manually confirm:

**For Python modules (src/):**
- Run `python -m pytest tests/ -v` — all tests pass.
- Run `python -m flake8 src/ --max-line-length 100` — no lint errors.
- If no tests exist yet for this module, write at least one test before marking complete.
- Import the module in a Python shell to confirm no syntax/import errors.

**For configuration changes (config/):**
- Parse the YAML — must be valid.
- Verify all referenced camera IDs, zone names, and model paths are consistent.

**For API endpoints (src/api/):**
- Start the server and hit the endpoint with curl or the /docs page.
- Verify response schema matches the Pydantic model.

**For dashboard changes (dashboard/):**
- Open in browser, verify no console errors.
- Test WebSocket connection.

**For pipeline integration:**
- Run `python demo.py`, verify alerts fire correctly.
- Check that zone transitions produce expected events.

### 3. MOVE — Mark complete and pick the next task
- Mark the task `completed` only after verification passes.
- If verification fails, fix the issue and re-verify. Do not mark as completed.
- Pick the next task from the todo list and repeat.

## Anti-Patterns (Do Not Do)
- Do NOT mark multiple tasks completed in a batch without verifying each one.
- Do NOT skip verification because "it's a small change."
- Do NOT start a new task while the current one has failing tests.
- Do NOT write code without reading the existing code first.
- Do NOT create new files when editing existing files would suffice.
