# t01-burnmap showcases

These examples show public, user-facing ways `t01-burnmap` is intended to help developers understand AI coding-agent spend.

## 1. Post-hoc budget-spike analysis

**Situation:** A coding session cost much more than expected.

**Workflow:**

- Sort sessions or prompts by estimated cost.
- Open the expensive item.
- Inspect tool calls and subagent activity.
- Look for retries, loops, or repeated context loading.

**Outcome:** Find the workflow pattern that caused the spike and adjust prompts, commands, or agent instructions.

## 2. Tool-level cost analysis

**Situation:** You suspect one tool is driving most token usage.

**Workflow:**

- Open the tools view.
- Sort tools by total estimated cost.
- Compare frequency, average cost, and total cost.

**Outcome:** Decide whether to rewrite tool instructions, reduce unnecessary calls, or move repeated work into scripts.

## 3. Duplicate-prompt discovery

**Situation:** You keep typing similar prompts across sessions.

**Workflow:**

- Group similar prompts by fingerprint or text preview.
- Review repeated high-cost requests.
- Convert stable repeats into reusable commands, templates, or skills.

**Outcome:** Turn recurring manual prompting into a cleaner workflow.

## 4. Weekly cost review

**Situation:** You want a lightweight review of coding-agent usage.

**Workflow:**

- Filter to the last week.
- Review total cost, expensive sessions, and repeated prompts.
- Export CSV for your notes if needed.

**Outcome:** Keep AI coding spend visible without sending your logs to a hosted analytics service.
