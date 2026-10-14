from __future__ import annotations
from collections import deque
from .map import Point, Rect, Sidewalk, VillageMap


def _gate(a: Rect, b: Rect) -> Point:
    # midpoint of the shared area between two touching rects
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ox1, ox2 = max(ax, bx), min(ax + aw, bx + bw)
    oy1, oy2 = max(ay, by), min(ay + ah, by + bh)
    if ox1 <= ox2 and oy1 <= oy2:
        return (ox1 + ox2) // 2, (oy1 + oy2) // 2
    cx = max(ax, min(bx, ax + aw))
    cy = max(ay, min(by, ay + ah))
    dx = max(bx, min(ax, bx + bw))
    dy = max(by, min(ay, by + bh))
    return (cx + dx) // 2, (cy + dy) // 2


def _sidewalk_path(village_map: VillageMap, start_id: str, goal_id: str) -> list[Sidewalk]:
    # BFS the sidewalk graph between two buildings' sidewalks
    start_sid = village_map.building(start_id).sidewalk_id
    goal_sid = village_map.building(goal_id).sidewalk_id
    if start_sid == goal_sid:
        return [village_map.sidewalk(start_sid)]
    seen = {start_sid}
    q: deque[list[str]] = deque([[start_sid]])
    while q:
        trail = q.popleft()
        for nxt in village_map.sidewalk(trail[-1]).connections:
            if nxt in seen:
                continue
            if nxt == goal_sid:
                chain = trail + [nxt]
                return [village_map.sidewalk(s) for s in chain]
            seen.add(nxt)
            q.append(trail + [nxt])
    raise ValueError(f"No sidewalk route from {start_id} to {goal_id}")


def route(village_map: VillageMap, start_id: str, goal_id: str) -> list[Point]:
    # return world-space waypoints that stay on sidewalks
    start_building = village_map.building(start_id)
    goal_building = village_map.building(goal_id)
    if start_id == goal_id:
        return [start_building.entrance]
    sidewalks = _sidewalk_path(village_map, start_id, goal_id)
    waypoints: list[Point] = [start_building.entrance]
    for i in range(len(sidewalks) - 1):
        waypoints.append(_gate(sidewalks[i].bounds, sidewalks[i + 1].bounds))
    waypoints.append(goal_building.entrance)
    return waypoints