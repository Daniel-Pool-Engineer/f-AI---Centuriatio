from __future__ import annotations
from math import hypot
from .map import Point

class VillagerSprite:
    # a red circle that walks a list of world-space waypoints

    radius = 6
    color = (200, 40, 40)

    def __init__(self, position: Point, speed: float = 200.0) -> None:
        self.x, self.y = position
        self.speed = speed
        self.path: list[Point] = []

    def set_path(self, waypoints: list[Point]) -> None:
        # replace the current path with a fresh list of waypoints
        self.path = list(waypoints)

    def update(self, dt: float) -> None:
        # advance along the path by speed * dt world units
        remaining = self.speed * dt
        while remaining > 0 and self.path:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            dist = hypot(dx, dy)
            if dist <= remaining:
                self.x, self.y = tx, ty
                remaining -= dist
                self.path.pop(0)
            else:
                self.x += dx / dist * remaining
                self.y += dy / dist * remaining
                remaining = 0.0