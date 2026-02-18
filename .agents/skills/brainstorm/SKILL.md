---
name: brainstorm
description: "Brainstorm - Trellis-Orchestrated Requirements Discovery"
---

# Brainstorm - Trellis-Orchestrated Requirements Discovery

Use this skill to turn vague development ideas into a Trellis-ready task package that can be executed via `$start` (and `$parallel` when available).

## Positioning

- This is the Trellis-local brainstorm workflow.
- It is optimized for `.trellis` orchestration and `task.py` pipelines.
- In mixed environments (global + Trellis), this local skill is the Trellis-mode implementation.

Dispatch expectation in mixed environments:

- If `.trellis/` and this file both exist, route `$brainstorm` here by default.
- Use global brainstorm only as explicit override (for example, `--global` style dispatch in your runtime).

## Outputs (Trellis Mode)

Target output package:

```text
$TASK_DIR/
├── prd.md           # requirements and acceptance criteria
├── info.md          # technical design (required for moderate/complex tasks)
├── implement.jsonl  # implementation context injection
├── check.jsonl      # review/check context injection
└── task.json        # task metadata
```

## Command and Script Contract

Use only rc5 Python scripts (no legacy `.sh` scripts):

```bash
python3 ./.trellis/scripts/task.py <command>
```

---

## Core Principles

1. Task-first: ensure a task exists before deep discussion.
2. Action-before-asking: discover facts locally before asking user.
3. One-question-at-a-time: no question bursts.
4. Research-first for technical choices.
5. Root-cause-first: explain why scenarios happen.
6. Diverge then converge: explore edges first, finalize MVP second.
7. Keep outputs executable: produce concrete artifacts, not abstract notes.

---

## Step 0: Ensure Task Exists [AI]

If no active task exists, create one:

```bash
TASK_DIR=$(python3 ./.trellis/scripts/task.py create "brainstorm: <short goal>" --slug <slug>)
```

Seed `prd.md` immediately with known facts:

```markdown
# brainstorm: <short goal>

## Goal

<what + why>

## What I already know

- <facts>

## Assumptions (temporary)

- <assumption>

## Open Questions

- <blocking/preference questions only>

## Requirements (draft)

- <item>

## Acceptance Criteria (draft)

- [ ] <criterion>

## Out of Scope (draft)

- <item>
```

---

## Step 1: Auto-Context Pass [AI]

Before asking questions, inspect repo/docs:

- likely modules/files
- existing patterns and conventions
- constraints and dependencies
- related docs/specs

Write findings back into `prd.md` (`What I already know`, `Technical Notes`).

---

## Step 2: Complexity and Path Selection [AI]

Classify:

- Trivial: one-line obvious fix
- Simple: clear scope, 1-2 files
- Moderate: multi-file with some ambiguity
- Complex: architecture decisions and tradeoffs

Path decision:

- Trivial/Simple: direct path is allowed after one confirmation.
- Moderate/Complex: full brainstorm path is required.

Decision prompt shape:

```text
I assess this as <level>.
A) Direct path (minimal overhead)
B) Full brainstorm path (recommended for this case)
```

---

## Step 3: Question Gate [AI]

Ask only high-value questions.

Gate A: Can this be derived from repo/docs/research?
- If yes, do not ask.

Gate B: Is it a meta question?
- If yes, do not ask.

Gate C: Is it blocking or preference?
- Ask only these two categories.

---

## Step 4: Research-First Mode [AI]

Trigger when choosing architecture/approach/library/protocol.

Research deliverables:

1. Existing implementations
2. Reusable patterns
3. Potential conflicts
4. 2-3 feasible approaches

Record in PRD:

```markdown
## Research Notes

### Existing Implementations
- <path>: <relevance>

### Reusable Patterns
- <pattern>: <path>

### Potential Conflicts
- <risk>

### Feasible Approaches
- A: <summary>
- B: <summary>
- C: <summary optional>
```

---

## Step 5: Expansion Sweep (Diverge) [AI]

Before converging, check:

- Future evolution
- Adjacent scenario consistency
- Failure and edge behavior

Explicitly ask which items belong in MVP vs out-of-scope.

---

## Step 6: Q&A Loop (Converge) [AI]

Rules:

- one question per message
- multiple choice preferred
- after each answer, immediately update PRD

For each answered item:

- move from `Open Questions` to `Requirements`
- add/update `Acceptance Criteria`
- refine `Out of Scope`

---

## Step 7: Approach Selection and Excluded Scenarios [AI]

Present 2-3 options with recommendation:

```markdown
## Decision Candidate

### Approach A (Recommended)
- How:
- Pros:
- Cons:

### Approach B
- How:
- Pros:
- Cons:
```

Capture decision in ADR-lite format:

```markdown
## Decision (ADR-lite)

Context: ...
Decision: ...
Consequences: ...
```

Also record excluded scenarios:

```markdown
## Excluded Scenarios
- <scenario>: excluded because <root-cause validation>
```

---

## Step 8: Final Confirmation [AI]

Before task activation, confirm:

- Goal
- Requirements
- Acceptance criteria
- Out of scope
- Technical approach
- Small-PR breakdown

Confirmation template:

```markdown
Here is the finalized scope:

Goal: ...
Requirements: ...
Acceptance Criteria: ...
Out of Scope: ...
Technical Approach: ...

If this is correct, I will prepare Trellis artifacts and hand off to execution.
```

---

## Step 9: Materialize Trellis Artifacts [AI]

## 9.1 Initialize jsonl context

```bash
python3 ./.trellis/scripts/task.py init-context "$TASK_DIR" <frontend|backend|fullstack>
```

## 9.2 Add task-specific context

For each relevant spec/pattern:

```bash
python3 ./.trellis/scripts/task.py add-context "$TASK_DIR" implement "<path>" "<reason>"
python3 ./.trellis/scripts/task.py add-context "$TASK_DIR" check "<path>" "<reason>"
```

## 9.3 `info.md` policy

- Required for Moderate/Complex tasks.
- Optional for Trivial/Simple tasks.

`info.md` template:

```markdown
# Technical Design: <Task>

## Selected Approach

<decision>

## Alternatives Considered

- <alternative>: <why not chosen>

## Architecture

<sectioned design>

## Files to Modify

- <path>: <change>

## Reusable Patterns

- <path>: <how reused>

## Risks and Mitigations

- <risk>: <mitigation>
```

## 9.4 Validate and activate task

```bash
python3 ./.trellis/scripts/task.py validate "$TASK_DIR"
python3 ./.trellis/scripts/task.py start "$TASK_DIR"
```

---

## Step 10: Handoff and Execution Routing [AI]

Handoff summary must include:

- task path
- generated artifacts
- selected approach
- major risks
- recommended next command

Routing policy:

1. Default execution: `$start`
2. If `.agents/skills/parallel/SKILL.md` exists, `$parallel` may be offered
3. If parallel skill is missing, do not recommend `$parallel`; keep `$start`

Handoff message shape:

```text
Brainstorm complete.
Task: <TASK_DIR>
Artifacts: prd.md, info.md (if required), implement.jsonl, check.jsonl, task.json

Recommended next step:
- $start
- or $parallel (only if parallel skill exists)
```

---

## Anti-Patterns (Hard Avoid)

- asking user for facts available in repo
- asking for approach choice before presenting concrete options
- skipping excluded-scenario record
- leaving PRD stale during long dialogues
- using legacy `.sh` script commands

---

## Related Commands

- `$start`: execute implementation flow using current task
- `$finish-work`: pre-commit completeness checklist
- `$update-spec`: capture learned executable contracts
