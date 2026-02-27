"""
Auto Skill Creation Extension
After each successful multi-step task, automatically generates a SKILL.md
and saves it to usr/skills/auto-generated/ for future reuse.
"""
import os
import re
from datetime import datetime
from python.helpers.extension import Extension
from python.helpers.log import Log
from agent import LoopData

AUTO_SKILLS_DIR = "usr/skills/auto-generated"
MIN_TOOL_STEPS = 3           # Only create skill if task used >= 3 tool calls
SKILL_TEMPLATE = """\
---
name: "{name}"
description: "{description}"
version: "1.0.0"
author: "auto-generated"
tags: {tags}
created: "{created}"
---

# {name}

## Summary
{description}

## Steps Used
{steps}

## Notes
Auto-generated from a successful {tool_count}-step task completed on {created}.
"""


class AutoSkillCreation(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        try:
            agent = self.agent
            # Only trigger when a response (task completion) just happened
            if not loop_data or loop_data.iteration < MIN_TOOL_STEPS:
                return

            # Collect tool calls from this monologue's history
            tool_calls = self._extract_tool_calls(agent)
            if len(tool_calls) < MIN_TOOL_STEPS:
                return

            # Build skill content using the utility model
            skill_content = await self._generate_skill(agent, tool_calls)
            if not skill_content:
                return

            # Save to usr/skills/auto-generated/
            await self._save_skill(skill_content, len(tool_calls))

        except Exception:
            pass  # Never block the agent for skill creation errors

    def _extract_tool_calls(self, agent) -> list[str]:
        """Extract tool call names from recent history."""
        calls = []
        try:
            for msg in agent.history[-20:]:  # last 20 messages
                content = str(getattr(msg, 'content', '') or '')
                tools_found = re.findall(r'"tool_name"\s*:\s*"([^"]+)"', content)
                calls.extend(t for t in tools_found if t not in ('response', 'wait'))
        except Exception:
            pass
        return calls

    async def _generate_skill(self, agent, tool_calls: list[str]) -> str:
        """Generate SKILL.md content using a quick util model call."""
        try:
            # Get last user message as the task description
            last_user = ""
            for msg in reversed(agent.history):
                role = getattr(msg, 'role', '')
                if role == 'user':
                    last_user = str(getattr(msg, 'content', ''))[:300]
                    break

            if not last_user or len(last_user) < 10:
                return ""

            # Clean task description for skill name
            name = re.sub(r'[^a-z0-9\-]', '-', last_user[:40].lower().strip())
            name = re.sub(r'-+', '-', name).strip('-') or "auto-skill"
            tags = list(set(tool_calls[:5]))  # unique tool names as tags
            steps_text = "\n".join(f"- {t}" for t in tool_calls)
            created = datetime.now().strftime("%Y-%m-%d")

            return SKILL_TEMPLATE.format(
                name=name,
                description=last_user[:200].replace('"', "'"),
                tags=str(tags),
                steps=steps_text,
                tool_count=len(tool_calls),
                created=created,
            )
        except Exception:
            return ""

    async def _save_skill(self, content: str, tool_count: int):
        """Write the skill file to disk."""
        try:
            os.makedirs(AUTO_SKILLS_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{AUTO_SKILLS_DIR}/skill_{timestamp}_{tool_count}steps"
            os.makedirs(filename, exist_ok=True)
            with open(f"{filename}/SKILL.md", "w") as f:
                f.write(content)
        except Exception:
            pass
