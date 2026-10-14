from __future__ import annotations

from backend.agent.agent import VillagerAgent, VillagerContext
from backend.agent.profile import RoleProfile

from .map import VillageMap
from .navigation import route
from .sprite import VillagerSprite

import threading

DAY_SECONDS = 30.0
NIGHT_SECONDS = 15.0


class Villager:
    # one villager driven by a role profile and an LLM agent

    def __init__(
        self,
        villager_id: str,
        name: str,
        profile: RoleProfile,
        home_id: str,
        llm_client,
        village_map: VillageMap,
    ) -> None:
        self.id = villager_id
        self.name = name
        self.home_id = home_id
        self.location_id = home_id
        self.agent = VillagerAgent(villager_id, name, profile, llm_client=llm_client)
        self.sprite = VillagerSprite(village_map.building(home_id).entrance)
        self.previous_action: str | None = None
        self.cooldown = 0.0
        self.day = 1
        self.phase = "day"
        self.clock = 0.0
        self._pending = False
        self._result = None

    def update(self, dt: float, village_map: VillageMap) -> None:
        self.sprite.update(dt)
        self.cooldown -= dt
        self._tick_clock(dt)

        if self._result is not None:
            self._apply_result(self._result, village_map)
            self._result = None
            self._pending = False

        if self.sprite.path or self.cooldown > 0 or self._pending:
            return

        self.cooldown = 2.0
        self._pending = True
        threading.Thread(
            target=self._decide_background,
            args=(self._context(),),
            daemon=True,
        ).start()

    def _decide_background(self, ctx: VillagerContext) -> None:
        # run the LLM call off the main thread and stash the result
        try:
            action = self.agent.decide(ctx)
            print(f"{self.name}: {action.action} -> {action.target_location} | {action.journal}")
            self._result = action
        except Exception as exc:
            print(f"{self.name} decision failed: {exc}")
            self._pending = False

    def _apply_result(self, action, village_map: VillageMap) -> None:
        # apply a completed decision on the main thread
        self.previous_action = action.action
        if action.target_location and action.target_location != self.location_id:
            try:
                self.sprite.set_path(
                    route(village_map, self.location_id, action.target_location)
                )
                self.location_id = action.target_location
            except ValueError as exc:
                print(f"  {self.name} route failed: {exc}")

    def _tick_clock(self, dt: float) -> None:
        #advance the day/night clock
        self.clock += dt
        if self.phase == "day" and self.clock >= DAY_SECONDS:
            self.phase, self.clock = "night", 0.0
        elif self.phase == "night" and self.clock >= NIGHT_SECONDS:
            self.phase, self.clock = "day", 0.0
            self.day += 1

    def _context(self) -> VillagerContext:
        #build the snapshot the agent sees each decision
        return VillagerContext(
            villager_id=self.id,
            name=self.name,
            location_id=self.location_id,
            day=self.day,
            phase=self.phase,
            crisis_active=False,
            crisis_day=0,
            crisis_duration=0,
            crisis_area=None,
            power_on=self.phase == "day",
            previous_action=self.previous_action,
        )