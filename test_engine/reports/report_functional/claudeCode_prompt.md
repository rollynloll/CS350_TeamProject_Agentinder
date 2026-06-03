# Claude Code Prompt: Assignment 4 — Functional Test Engine Experiment
# Agentinder / KAIST CS350 Team 6

---

## PRIMARY DIRECTIVE: DO NOT STOP

Do not stop under any circumstances until all completion conditions are met.

The only permitted reasons to stop:
- All items on the completion checklist are marked done
- Claude API calls are entirely unavailable (report to user immediately and wait)

Do not stop in any of the following situations:
- A generated test fails — analyze, record, and proceed to the next level
- A file creation error occurs — identify the cause and retry
- An unexpected result appears — record it and continue
- Clarification seems necessary — make your own judgment, proceed, and report upon completion

When blocked: find a solution independently. If no solution is found, choose the best available alternative, record the decision in `test_engine/report_functional/decisions.md`, and continue.

---

## PREREQUISITE: READ ALL DOCUMENTS BEFORE STARTING

Before any other action, read every file in the `docs/` folder.

Required documents:
- `docs/26S_CS350_SRS_Team_13.pdf` — Full functional requirements (all REQs and UCs)
- `docs/Agentinder_API_Specification_v2.docx` — REST API and WebSocket specification
- `docs/README.md` — Team composition, tech stack, development plan
- All other files found in `docs/`

After reading, compile the list of REQs selected for testing and their key numerical constants (weights, limits, timeouts, etc.) in `test_engine/report_functional/doc_summary.md`. Only then proceed.

If the `docs/` folder does not exist, search the entire project root for documentation files.

---

## ROLE AND EXPERIMENT STRUCTURE

This task serves two simultaneous purposes.

**Role 1 — Experimenter:**
Call the Claude API (`claude-sonnet-4-20250514`) to generate functional test code. Execute the generated code and evaluate its correctness.

**Role 2 — Subject of Assignment 4:**
Directly conduct the experiment: "Can AI perform software test engineering?" Use progressively complex test generation requests to identify where AI fails.

**Core experimental question:**
Can the Claude API read SRS requirements and autonomously write correct test cases? What kinds of mistakes does it make as complexity increases?

---

## WORKING DIRECTORY

First determine the project root (use `ls`, `pwd`).
All files must be created inside `test_engine/` at the project root.

```
test_engine/
├── functional/                  # Final functional test engine (output)
│   ├── test_req_0201.py
│   ├── test_req_0204.py
│   ├── ...
│   └── run_all.py
├── generated/                   # Raw generated code from Claude API
│   ├── level_1_attempt_1.py
│   ├── level_1_attempt_2.py     # On retry
│   ├── level_2_attempt_1.py
│   └── ...
└── report_functional/           # Assignment 4 report location
    ├── doc_summary.md
    ├── level_design.md
    ├── decisions.md
    └── assignment4_report.md
```

---

## OBJECTIVES

### Objective 1: Design Complexity Levels

Define the complexity levels at which test code generation will be requested from the Claude API.

Level design criteria:
- **Level 1:** Single REQ, happy path only, expected values explicitly given in prompt
- **Level 2:** Single REQ, happy path + boundary cases, expected values given
- **Level 3:** Single REQ, all three case types, expected values given
- **Level 4:** Single REQ, case types named, expected values to be derived from SRS
- **Level 5:** Two REQs combined, case types named, expected values self-derived
- **Level 6:** Three or more REQs combined, case design left to AI, expected values self-derived
- **Level 7 and above:** Design additional levels of complexity that you judge to carry meaningful failure risk

For each level, record in `report_functional/level_design.md` the predicted likelihood and reason for AI failure at that level.

### Objective 2: Run the Experiment

For each level, in order:
1. Write the prompt for that level and call the Claude API
2. Save generated code to `generated/level_N_attempt_M.py`
3. Execute the generated test code against the actual implementation
4. Evaluate correctness using the criteria below
5. On failure, analyze the result, retry, or proceed to the next level

### Objective 3: Finalize the Functional Test Engine

From the tests that passed, select the highest-quality outputs, or write final versions directly, and save them to `functional/`. Generated code may be used as-is, corrected based on failure analysis, or replaced with a manual implementation. The full suite must be executable via `functional/run_all.py`.

### Objective 4: Write the Assignment 4 Report

After all experiments are complete, write `report_functional/assignment4_report.md`.

---

## CONSTRAINTS

### Constraint 1: Documents First
All expected values in test cases must be grounded in SRS documentation. Do not estimate expected values without a documented basis. Each test file must include the REQ ID and SRS section number as a comment at the top.

### Constraint 2: Experimental Integrity
Do not include correct implementations or specific implementation hints in Claude API prompts. The amount of information permitted in the prompt varies by level (see level design criteria). Generated code must be saved to `generated/` exactly as received. Do not modify it.

### Constraint 3: Consistent Evaluation Criteria
Generated test code is evaluated on four criteria:
- **Structural validity:** Does the file execute without SyntaxError or ImportError?
- **Case completeness:** Are all requested case types (happy path / boundary / exception) present?
- **Expected value accuracy:** Do expected values match those derivable from the SRS?
- **REQ coverage:** Does the test address the core conditions of the target REQ?

Failure on any one criterion constitutes a failed attempt.

### Constraint 4: Behavior After Failure
- Retry the same level with the same prompt up to two times
- If both retries fail, classify as a confirmed failure, record the analysis in `decisions.md`, and proceed to the next level
- If two consecutive levels both result in confirmed failure, terminate the experiment
- If the maximum level (10) is reached, terminate the experiment

### Constraint 5: Self-Verification
Upon completing each objective, verify the completion conditions independently. If any item is unmet, return to it immediately and complete it. Do not ask the user what to do next.

---

## FUNCTIONAL TEST FILE REQUIREMENTS

Final test files saved to `functional/` must follow this structure:

```
File header:
- REQ ID
- Full REQ description
- SRS section number

Each test function:
- Function name indicates case type (test_happy_path, test_boundary, test_edge_case)
- Docstring states the test intent and SRS basis
- Prints PASS or FAIL with reason

Execution:
- Individual: python functional/test_req_XXXX.py
- Full suite:  python functional/run_all.py
- Output: REQ ID + PASS/FAIL + reason on failure
```

---

## CLAUDE API CALL SPECIFICATION

- Model: `claude-sonnet-4-20250514`
- max_tokens: 2000
- System prompt: `"You are a software test engineer. Write Python test code for the given requirement. Output only raw Python code, no markdown fences, no explanation."`
- User prompt per level: include only the information permitted for that level
- Strip any markdown fences (```) from API responses before saving

---

## ASSIGNMENT 4 REPORT REQUIREMENTS

Write `report_functional/assignment4_report.md` in English.

**Section 1: Experiment Overview**
- Experiment subject: functional test engine generation
- Methodology: progressive complexity, Claude API prompting
- Rationale for REQ selection

**Section 2: Complexity Level Design**
- Table: Level | Information permitted in prompt | Target REQ(s) | Predicted failure risk
- Rationale for level ordering
- Predicted failure mode for each level

**Section 3: Results by Level**
- Table: Level | Attempts | Result | Key error
- Core portion of generated code per level (not full code)
- For each failure: which test case failed and why

**Section 4: Failure Point Analysis**
- Confirmed failure point
- Exact location in generated code that was wrong
- Classification: requirement misunderstanding / expected value error / case omission / structural error / other
- What prompt change would produce a passing result

**Section 5: The Future of Software Engineering** (concise; key issues only)
- Grounded in observations from this experiment
- What AI does and does not do well in test engineering
- Two to three key implications for the evolving role of software engineers
- Detailed discussion omitted (to be written separately by the author)

---

## EXECUTION ORDER

```
Step 0: Identify project root; create test_engine/ directory structure

Step 1: Read all docs/
        → Write report_functional/doc_summary.md

Step 2: Design complexity levels
        → Write report_functional/level_design.md

Step 3: Run experiment level by level
        → Call Claude API → save to generated/ → execute → evaluate
        → On failure: record in decisions.md → retry → proceed to next level
        → Stop when termination condition is reached

Step 4: Finalize functional/ test engine
        → Select or write final test files based on experiment results
        → Write and verify run_all.py

Step 5: Write report_functional/assignment4_report.md

Step 6: Self-verify completion checklist
        → Return to any unmet item and complete it
        → When all items are met, print final result summary
```

---

## COMPLETION CHECKLIST

- [ ] `test_engine/report_functional/doc_summary.md` exists
- [ ] `test_engine/report_functional/level_design.md` exists with per-level predictions
- [ ] `test_engine/report_functional/decisions.md` exists with failure analysis
- [ ] `test_engine/generated/` contains generated code files for each level
- [ ] `test_engine/functional/` contains 6 or more REQ-based test files
- [ ] `test_engine/functional/run_all.py` executes successfully and prints results
- [ ] `test_engine/report_functional/assignment4_report.md` contains all 5 sections, written in English
- [ ] Failure point is clearly identified and recorded in the report
- [ ] All generated code is preserved as-is in `generated/`