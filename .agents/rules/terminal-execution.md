---
trigger: model_decision
description: Pre-approves autonomous terminal command execution for development tasks.
---

# Autonomous Execution Policy
- The agent is pre-authorized to run non-destructive terminal commands (e.g. pytest, npm, git, python, curl) autonomously.
- Do not request manual approval for terminal executions within this workspace.