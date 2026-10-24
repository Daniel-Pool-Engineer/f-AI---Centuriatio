"""villagers that walk between buildings along the sidewalks"""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import pygame

from .map import Building, Sidewalk, VillageMap
from .renderer import VillageMapRenderer
from backend.agent.agent import VillagerAgent, VillagerContext
from backend.agent.profile import CITIZEN, FIREFIGHTER, ELECTRICIAN, DOCTOR


Color = tuple[int, int, int]
Vec = tuple[float, float]

SHELTER_ID = "school"  # where villagers go during a power outage
CROSSWALK_GAP = 100    # sidewalks this close are connected by a road crossing

# name, home building, color (building ids match backend/map/graph.py)
STARTING_VILLAGERS = [
    ("m1", "Maria", "home_a", (200, 40, 40), CITIZEN),
    ("v_ana", "Dr. Ana", "home_a", (220, 60, 60), DOCTOR),        # Doctor
    ("v_ben", "Ben", "home_b", (40, 120, 220), FIREFIGHTER),      # First Responder
    ("v_carla", "Carla", "home_b", (240, 140, 20), ELECTRICIAN),  # Electrician
    ("v_diego", "Diego", "home_c", (30, 160, 90), CITIZEN),       # Citizen
    ("v_elena", "Elena", "home_d", (170, 60, 190), CITIZEN),      # Citizen
    ("v_felix", "Felix", "home_b", (20, 20, 20), CITIZEN),        # Citizen
]

SCRIPTED_NPCS = [
    ("npc_1", "Sam", "home_c", (100, 200, 150)),
    ("npc_2", "Lily", "home_d", (200, 100, 250)),
    ("npc_3", "Jack", "home_b", (150, 150, 50)),
    ("npc_4", "Chloe", "home_a", (250, 150, 150)),
    ("npc_5", "Tom", "home_c", (50, 200, 200)),
]

def _rect_gap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    # distance between two rectangles (0 if they touch)
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    dx = max(0, bx - (ax + aw), ax - (bx + bw))
    dy = max(0, by - (ay + ah), ay - (by + bh))
    return max(dx, dy)


def _centerline_point(sidewalk: Sidewalk, point: Vec) -> Vec:
    # closest point on the middle line of a sidewalk
    x, y, width, height = sidewalk.bounds
    px, py = point
    if width >= height:
        return (min(max(px, x), x + width), y + height / 2)
    return (x + width / 2, min(max(py, y), y + height))


class SidewalkNetwork:
    """finds walking routes between buildings"""

    def __init__(self, village_map: VillageMap) -> None:
        self.by_id = {s.id: s for s in village_map.sidewalks}
        self.adjacency: dict[str, set[str]] = {s.id: set() for s in village_map.sidewalks}

        # connections listed in the map
        for sidewalk in village_map.sidewalks:
            for other_id in sidewalk.connections:
                self.adjacency[sidewalk.id].add(other_id)
                self.adjacency[other_id].add(sidewalk.id)

        # sidewalks on opposite sides of a road act as crosswalks
        for a in village_map.sidewalks:
            for b in village_map.sidewalks:
                if a.id != b.id and _rect_gap(a.bounds, b.bounds) <= CROSSWALK_GAP:
                    self.adjacency[a.id].add(b.id)

    def sidewalk_path(self, start: str, goal: str) -> list[str]:
        # shortest list of sidewalks from start to goal
        if start == goal:
            return [start]
        seen = {start}
        queue = deque([[start]])
        while queue:
            route = queue.popleft()
            for next_id in self.adjacency[route[-1]]:
                if next_id == goal:
                    return route + [next_id]
                if next_id not in seen:
                    seen.add(next_id)
                    queue.append(route + [next_id])
        return [start, goal]

    def route(self, start: Vec, start_sidewalk: str, building: Building) -> list[tuple[Vec, str]]:
        # list of (point, sidewalk id) to walk through to reach a building
        waypoints: list[tuple[Vec, str]] = []
        point = start
        for sidewalk_id in self.sidewalk_path(start_sidewalk, building.sidewalk_id):
            point = _centerline_point(self.by_id[sidewalk_id], point)
            waypoints.append((point, sidewalk_id))

        # walk to the spot beside the entrance, then step inside
        final = self.by_id[building.sidewalk_id]
        waypoints.append((_centerline_point(final, building.entrance), final.id))
        waypoints.append(((float(building.entrance[0]), float(building.entrance[1])), final.id))
        return waypoints


@dataclass
class Villager:
    agent_id: str
    name: str
    home_id: str
    color: Color
    position: Vec
    sidewalk_id: str
    location_id: str | None   # building they are at, None while walking
    agent: VillagerAgent | None
    destination_id: str | None = None
    waypoints: list[tuple[Vec, str]] = field(default_factory=list)
    wait_time: float = 0.0   # seconds before leaving the current building
    offset: Vec = (0.0, 0.0)   # small shift so villagers don't overlap
    previous_action: str | None = None
    current_task: str = "Waiting"
    is_scripted: bool = False
    decision_cooldown: float = 0.0

    @property
    def is_walking(self) -> bool:
        return bool(self.waypoints)


class VillagerManager:
    """moves and draws every villager"""

    walk_speed = 140.0  # world units per second

    def __init__(self, village_map: VillageMap, rng: random.Random | None = None, llm_client: Any = None) -> None:
        self.network = SidewalkNetwork(village_map)
        self.buildings = {b.id: b for b in village_map.buildings}
        self.rng = rng or random.Random()
        self.llm_client = llm_client
        self.power_outage = False
        self.is_night = False
        self.font = pygame.font.Font(None, 16)
        self._label_cache: dict[str, pygame.Surface] = {}
        self.villagers = [
            self._spawn(v_id, name, home_id, color, profile)
            for v_id, name, home_id, color, profile in STARTING_VILLAGERS
        ]
        for v_id, name, home_id, color in SCRIPTED_NPCS:
            npc = self._spawn(v_id, name, home_id, color, None)
            npc.is_scripted = True
            npc.wait_time = self.rng.uniform(1.0, 5.0)
            self.villagers.append(npc)

    def _spawn(self, agent_id: str, name: str, home_id: str, color: Color, profile) -> Villager:
        home = self.buildings[home_id]
        agent = VillagerAgent(agent_id, name, profile, llm_client=self.llm_client) if profile is not None else None

        return Villager(
            agent_id=agent_id,
            name=name,
            home_id=home_id,
            color=color,
            position=(float(home.entrance[0]), float(home.entrance[1])),
            sidewalk_id=home.sidewalk_id,
            location_id=home_id,
            agent=agent,
            wait_time=self.rng.uniform(0.5, 4.0),
            offset=(self.rng.uniform(-10, 10), self.rng.uniform(-10, 10)),
        )
    def get_villager(self, agent_id: str) -> Villager | None:
        for v in self.villagers:
            if v.agent_id == agent_id:
                return v
        return None
    
    def set_night(self, is_night: bool) -> None:
        # night: villagers go home, morning: they start wandering again
        self.is_night = is_night
        if self.power_outage:
            return  # during an outage they stay at the shelter
        if is_night:
            self._send_everyone_home()
        else:
            self._wake_up()

    def _send_everyone_home(self) -> None:
        for villager in self.villagers:
            at_home = villager.location_id == villager.home_id and not villager.is_walking
            if not at_home:
                self.send_to(villager, villager.home_id)

    def _wake_up(self) -> None:
        # leave in a few seconds so they don't all walk out at once
        for villager in self.villagers:
            villager.wait_time = self.rng.uniform(1.0, 4.0)

    def send_to(self, villager: Villager, building_id: str) -> None:
        building = self.buildings[building_id]
        villager.waypoints = self.network.route(villager.position, villager.sidewalk_id, building)
        villager.destination_id = building_id
        villager.location_id = None

    def _walk(self, villager: Villager, dt: float) -> bool:
        # move along the waypoints, returns True when the trip is finished
        distance = self.walk_speed * dt
        while villager.waypoints and distance > 0:
            (target_x, target_y), sidewalk_id = villager.waypoints[0]
            x, y = villager.position
            gap = math.hypot(target_x - x, target_y - y)
            if gap <= distance:
                villager.position = (target_x, target_y)
                villager.sidewalk_id = sidewalk_id
                villager.waypoints.pop(0)
                distance -= gap
            else:
                villager.position = (
                    x + (target_x - x) / gap * distance,
                    y + (target_y - y) / gap * distance,
                )
                distance = 0
        return not villager.waypoints

    def set_power_outage(self, active: bool) -> list[str]:
        messages: list[str] = []
        self.power_outage = active
        
        if active:
            for villager in self.villagers:
                if villager.is_scripted:
                    # NPCs instantly head home to evacuate
                    self.send_to(villager, villager.home_id)
                    messages.append(f"{villager.name} is evacuating indoors")
                    continue

                if villager.is_walking:
                    # If they are walking, let them finish their current trip first
                    continue
                
                # If they are standing around, make them ask the AI what to do right now
                villager.wait_time = 0.0

                # Clear their old destination so they don't accidentally go back
                villager.destination_id = None 
                
                if villager.agent.profile.role == "citizen":
                    messages.append(f"{villager.name} is checking supplies")
        elif self.is_night:
            self._send_everyone_home()
        else:
            self._wake_up()
            
        return messages
    
    def update(self, dt: float) -> list[str]:
        """move villagers, returns journal messages for anything that happened"""
        messages: list[str] = []
        for villager in self.villagers:
            if villager.is_walking:
                if self._walk(villager, dt):
                    villager.location_id = villager.destination_id
                    villager.destination_id = None
                    villager.wait_time = self.rng.uniform(3.0, 8.0)
                    place = self.buildings[villager.location_id].display_name
                    messages.append(f"{villager.name} arrived at {place}")
            elif not self.is_night:
                if villager.wait_time > 0:
                    villager.wait_time -= dt
                elif villager.is_scripted and not self.power_outage:
                    # Scripted NPCs wander to random buildings periodically
                    if villager.wait_time <= 0:
                        choices = [b for b in self.buildings if b != villager.location_id]
                        dest = self.rng.choice(choices)
                        self.send_to(villager, dest)
                        villager.wait_time = self.rng.uniform(15.0, 30.0)
                        
        return messages
   
    def draw(self, surface: pygame.Surface, renderer: VillageMapRenderer) -> None:
        for villager in self.villagers:
            x, y = villager.position
            offset_x, offset_y = villager.offset

            screen_pos = renderer.world_to_screen((x + offset_x, y + offset_y))
            radius = max(5, round(9 * renderer.zoom))

            pygame.draw.circle(surface, villager.color, screen_pos, radius)
            pygame.draw.circle(surface, (255, 255, 255), screen_pos, radius, width=2)

            head_pos = (screen_pos[0], screen_pos[1] - radius)
            pygame.draw.circle(surface, (240, 200, 170), head_pos, max(3, radius // 2))

            if villager.name not in self._label_cache:
                if villager.is_scripted:
                    label_text = villager.name
                else:
                    role_display = villager.agent.profile.role.replace("_", " ").title()
                    label_text = f"{villager.name} ({role_display})"
                
                self._label_cache[villager.name] = self.font.render(label_text, True, (20, 20, 20))
            
            label = self._label_cache[villager.name]
            label_rect = label.get_rect(
                midbottom=(screen_pos[0], screen_pos[1] - radius - 5)
            )
            label_background = label_rect.inflate(6, 3)

            pygame.draw.rect(surface, (245, 245, 240), label_background, border_radius=3)
            surface.blit(label, label_rect)