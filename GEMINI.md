# Workspace Agent Instructions & Execution Policy

## Terminal & Tool Execution Policy
- Antigravity agent has pre-approval to execute builds, tests, git operations, migrations, and development server commands directly.
- Execute terminal commands autonomously without waiting or prompting the user for manual confirmation.
- Keep commands non-interactive (e.g., `-y`, `--yes`, `--non-interactive`) and avoid commands that block for stdin.
