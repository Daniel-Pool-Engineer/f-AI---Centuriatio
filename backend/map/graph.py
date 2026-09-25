from collections import deque

# Nodes = buildings. Key is the id used everywhere in the code, basically variable name
# value is the display name in the UI renders
LOCATIONS = {
    "hospital":   "Hospital",
    "police":     "Police Station",
    "school":     "School",
    "fire":       "Fire Station",
    "grocery":    "Food Store",
    "electrical": "Electrical Plant",
    "home_a":     "Home A",
    "home_b":     "Home B",
    "home_c":     "Home C",
    "home_d":     "Home D",
    "work":       "Work"
}

# Edges = roads. Undirected, no weights.
# TODO: Expand more roads so that other places are accessible.
EDGES = [
    ("hospital",   "police"),
    ("hospital",   "school"),
    ("hospital",   "home_a"),
    ("hospital",   "home_d"),
    ("police",     "electrical"),
    ("police",     "home_a"),
    ("school",     "home_d"),
    ("school",     "grocery"),
    ("grocery",    "home_c"),
    ("grocery",    "home_d"),
    ("electrical", "home_a"),
    ("electrical", "home_b"),
    ("home_a",     "home_b"),
    ("home_b",     "home_c"),
    ("home_c",     "home_d"),
    ("home_a",     "work")
]


def build_adj():
    # Expand EDGES into an undirected adjacency list, once at import time.
    adj = {loc: [] for loc in LOCATIONS}
    for a, b in EDGES:
        adj[a].append(b)
        adj[b].append(a)
    return adj


class VillageMap:
    # Static village graph.
    locations = LOCATIONS
    adjacency = build_adj()

    @classmethod
    def neighbors(cls, loc_id):
        # Direct road connections from buildings.
        return cls.adjacency[loc_id]

    @classmethod
    def path(cls, start, goal):
        # BFS - returns the shortest road path as [start, ..., goal].
        if start == goal:
            return [start]

        seen = {start}
        q = deque([[start]])

        while q:
            route = q.popleft()
            node = route[-1]
            for nxt in cls.adjacency[node]:
                if nxt in seen:
                    continue
                if nxt == goal:
                    return route + [nxt]
                seen.add(nxt)
                q.append(route + [nxt])

        raise ValueError(f"No road path from {start!r} to {goal!r}")
