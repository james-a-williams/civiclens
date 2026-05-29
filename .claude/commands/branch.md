Suggest and create a new git branch for the current task.

Steps:
1. If the user has described what they're working on (in this message or recent context), use that. Otherwise ask: "What is this branch for?"
2. Based on the answer, suggest 2–3 branch names in `type/short-description-kebab-case` format using the correct prefix:
   - `feat/` — new features or capabilities
   - `fix/` — bug fixes
   - `docs/` — documentation, diagrams, ADRs
   - `data/` — new data sources, connectors, dbt models
   - `agent/` — Claude Code agent workflows and prompts
3. Present the options and ask the user to pick one (or accept a custom name).
4. Once confirmed, run: `git checkout -b <chosen-name>`
5. Confirm the branch was created with `git branch --show-current`.

Keep names short (3–5 words max), lowercase, hyphen-separated. No ticket numbers or dates unless the user provides them.
