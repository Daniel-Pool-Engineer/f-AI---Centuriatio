from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
import json
import logging

from backend.map.graph import VillageMap

logger = logging.getLogger(__name__)


# Creating an agent; role is a new profile.
@dataclass(frozen=True)
class RoleProfile:
    role: str
    permitted_actions: Set[str]
    identity_line: str
    role_guidance: str
    speed: float = 1.0
    fallback_action: str = "wait"
    fallback_journal: str = "{name} stayed put; no valid action was chosen."


@dataclass
class ActionRequest:
    action: str
    target_location: Optional[str] = None
    journal: str = ""


# Snapshot of the village state.
@dataclass
class VillagerContext:
    villager_id: str
    name: str
    location_id: str
    day: int
    phase: str  # "day" | "night"
    crisis_active: bool
    crisis_day: int  # 0 if no crisis
    crisis_duration: int
    crisis_area: Optional[str]
    power_on: bool
    previous_action: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


# Reusable agent; role behavior comes from profile + context.
class VillagerAgent:
    def __init__(
        self,
        villager_id: str,
        name: str,
        profile: RoleProfile,
        llm_client: Optional[Any] = None,
    ) -> None:
        self.villager_id = villager_id
        self.name = name
        self.profile = profile
        self.llm_client = llm_client

    @property
    def role(self) -> str:
        return self.profile.role

    @property
    def speed(self) -> float:
        return self.profile.speed

    def decide(self, ctx: VillagerContext) -> ActionRequest:
        prompt = self.build_prompt(ctx)
        try:
            raw = self._call_llm(prompt)
            action = self._parse(raw)
        except Exception as exc:
            logger.warning("Agent %s LLM failure: %s", self.villager_id, exc)
            return self.fallback(ctx)

        if action.action not in self.profile.permitted_actions:
            logger.info(
                "Agent %s requested disallowed action %r",
                self.villager_id, action.action,
            )
            return self.fallback(ctx)

        return action

    def fallback(self, ctx: VillagerContext) -> ActionRequest:
        return ActionRequest(
            action=self.profile.fallback_action,
            target_location=ctx.location_id,
            journal=self.profile.fallback_journal.format(name=self.name),
        )

    def build_prompt(self, ctx: VillagerContext) -> List[Dict[str, str]]:
        system = (
            f"{self.profile.identity_line}\n"
            f"Role: {self.profile.role}.\n"
            f"{self.profile.role_guidance}\n"
            "You must reply with a single JSON object and nothing else, "
            "matching this schema:\n"
            '{"action": "<one of the permitted actions>", '
            '"target_location": "<location id or null>", '
            '"journal": "<one short sentence>"}\n'
            "Do not explain. Do not add fields."
        )

        crisis_line = (
            f"Crisis: power outage, day {ctx.crisis_day} of {ctx.crisis_duration}, "
            f"affected area: {ctx.crisis_area}."
            if ctx.crisis_active
            else "Crisis: none."
        )

        user = (
            f"Villager: {self.name} (id={self.villager_id})\n"
            f"Location: {ctx.location_id}\n"
            f"Time: Day {ctx.day}, {ctx.phase}\n"
            f"{crisis_line}\n"
            f"Power: {'on' if ctx.power_on else 'off'}\n"
            f"Previous action: {ctx.previous_action or 'none'}\n"
            f"Permitted actions: {sorted(self.profile.permitted_actions)}\n"
            f"Valid locations: {sorted(VillageMap.locations)}\n"
            "If the action involves going somewhere, set target_location"
            " to one of the valid locations. Otherwise use null.\n"
            "Choose the next action."
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        if self.llm_client is None:
            raise RuntimeError("No LLM client configured")
        return self.llm_client.chat(messages)

    @staticmethod
    def _parse(raw: str) -> ActionRequest:
        data = json.loads(raw)
        if "action" not in data:
            raise ValueError(f"Missing 'action' in agent output: {data!r}")
        return ActionRequest(
            action=str(data["action"]).strip(),
            target_location=data.get("target_location") or None,
            journal=str(data.get("journal", "")).strip(),
        )
