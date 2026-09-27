"""villagers that walk between buildings along the sidewalks"""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field

import pygame

from .map import Building, Sidewalk, VillageMap
from .renderer import VillageMapRenderer


Color = tuple[int, int, int]
Vec = tuple[float, float]

SHELTER_ID = "public-hall"  # where villagers go during a power outage
CROSSWALK_GAP = 100         # sidewalks this close are connected by a road crossing

# name, home building, color
STARTING_VILLAGERS = [
    ("Ana", "house-west", (220, 60, 60)),
    ("Ben", "apartment-west", (40, 120, 220)),
    ("Carla", "apartment-west", (240, 140, 20)),
    ("Diego", "apartment-west", (30, 160, 90)),
    ("Elena", "house-west", (170, 60, 190)),
    ("Felix", "apartment-west", (20, 20, 20)),
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
    name: str
    home_id: str
    color: Color
    position: Vec
    sidewalk_id: str
    location_id: str | None            # building they are at, None while walking
    destination_id: str | None = None
    waypoints: list[tuple[Vec, str]] = field(default_factory=list)
    wait_time: float = 0.0             # seconds before leaving the current building
    offset: Vec = (0.0, 0.0)           # small shift so villagers don't overlap

    @property
    def is_walking(self) -> bool:
        return bool(self.waypoints)


class VillagerManager:
    """moves and draws every villager"""

    walk_speed = 140.0  # world units per second

    def __init__(self, village_map: VillageMap, rng: random.Random | None = None) -> None:
        self.network = SidewalkNetwork(village_map)
        self.buildings = {b.id: b for b in village_map.buildings}
        self.rng = rng or random.Random()
        self.power_outage = False
        self.font = pygame.font.Font(None, 16)
        self.villagers = [
            self._spawn(name, home_id, color) for name, home_id, color in STARTING_VILLAGERS
        ]

    def _spawn(self, name: str, home_id: str, color: Color) -> Villager:
        # start each villager at their home entrance
        home = self.buildings[home_id]
        return Villager(
            name=name,
            home_id=home_id,
            color=color,
            position=(float(home.entrance[0]), float(home.entrance[1])),
            sidewalk_id=home.sidewalk_id,
            location_id=home_id,
            wait_time=self.rng.uniform(0.5, 4.0),
            offset=(self.rng.uniform(-10, 10), self.rng.uniform(-10, 10)),
        )

    def set_power_outage(self, active: bool) -> None:
        # outage: everyone heads to the shelter, restored: they wander again soon
        self.power_outage = active
        for villager in self.villagers:
            if active:
                already_there = villager.location_id == SHELTER_ID and not villager.is_walking
                if not already_there:
                    self.send_to(villager, SHELTER_ID)
            else:
                villager.wait_time = self.rng.uniform(1.0, 4.0)

    def send_to(self, villager: Villager, building_id: str) -> None:
        building = self.buildings[building_id]
        villager.waypoints = self.network.route(villager.position, villager.sidewalk_id, building)
        villager.destination_id = building_id
        villager.location_id = None

    def _pick_destination(self, villager: Villager) -> str:
        # any building except the one they are in
        choices = [b for b in self.buildings if b != villager.location_id]
        return self.rng.choice(choices)

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

    def update(self, dt: float) -> list[str]:
        # move villagers, returns journal messages for anything that happened
        messages: list[str] = []
        for villager in self.villagers:
            if villager.is_walking:
                if self._walk(villager, dt):
                    villager.location_id = villager.destination_id
                    villager.destination_id = None
                    villager.wait_time = self.rng.uniform(3.0, 8.0)
                    messages.append(f"{villager.name} arrived at {villager.location_id}")
            elif not self.power_outage:
                # during an outage villagers stay put at the shelter
                villager.wait_time -= dt
                if villager.wait_time <= 0:
                    self.send_to(villager, self._pick_destination(villager))
        return messages

    def draw(self, surface: pygame.Surface, renderer: VillageMapRenderer) -> None:
        for villager in self.villagers:
            x, y = villager.position
            offset_x, offset_y = villager.offset

            screen_pos = renderer.world_to_screen(
                (x + offset_x, y + offset_y)
            )

            radius = max(5, round(9 * renderer.zoom))

            # body
            body_rect = pygame.Rect(
                screen_pos[0] - radius,
                screen_pos[1] - radius,
                radius * 2,
                radius * 2,
            )

            pygame.draw.circle(
                surface,
                villager.color,
                screen_pos,
                radius,
            )

            pygame.draw.circle(
                surface,
                (255, 255, 255),
                screen_pos,
                radius,
                width=2,
            )

            # small head
            head_pos = (
                screen_pos[0],
                screen_pos[1] - radius,
            )

            pygame.draw.circle(
                surface,
                (240, 200, 170),
                head_pos,
                max(3, radius // 2),
            )

            label = self.font.render(
                villager.name,
                True,
                (20, 20, 20),
            )

            label_rect = label.get_rect(
                midbottom=(
                    screen_pos[0],
                    screen_pos[1] - radius - 5,
                )
            )

            # little white background behind the name
            label_background = label_rect.inflate(6, 3)

            pygame.draw.rect(
                surface,
                (245, 245, 240),
                label_background,
                border_radius=3,
            )

            surface.blit(label, label_rect)