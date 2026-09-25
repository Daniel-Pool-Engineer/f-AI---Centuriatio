# static village-map data and the coordinate system used by the game world

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


CELL_SIZE = 16
"""world units per map cell"""

DEFAULT_MAP_CELLS = (256, 192)
"""width and height of the starter map in cells"""

Point = tuple[int, int]
Rect = tuple[int, int, int, int]
RoadType = Literal["main", "local"]
BuildingType = Literal["house", "apartment", "shop", "office", "public"]


TEST_MAP_FEATURE_OFFSET = (512, 512)


def _offset_point(point: Point) -> Point:
    offset_x, offset_y = TEST_MAP_FEATURE_OFFSET
    x, y = point
    return x + offset_x, y + offset_y


def _offset_rect(rect: Rect) -> Rect:
    offset_x, offset_y = TEST_MAP_FEATURE_OFFSET
    x, y, width, height = rect
    return x + offset_x, y + offset_y, width, height


@dataclass
class Grid:
    """cell grid used for layout and view calculations;

    designed for NPCs using world-unit positions instead of being restricted to cells
    """

    width: int
    height: int
    cell_size: int = CELL_SIZE
    left: int = 0
    top: int = 0
    grid: list[list[int]] = field(init=False)

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("grid dimensions must be positive")
        if self.cell_size <= 0:
            raise ValueError("cell size must be positive")
        self.grid = [[0] * self.width for _ in range(self.height)]

    @property
    def world_size(self) -> tuple[int, int]:
        """return the grid dimensions in world units"""
        return self.width * self.cell_size, self.height * self.cell_size

    def set_view(self, left: int, top: int, cell_size: int) -> None:
        """set the grid's display offset and visual cell size"""
        if cell_size <= 0:
            raise ValueError("Cell size must be positive")
        self.left = left
        self.top = top
        self.cell_size = cell_size

    def cell_to_world(self, cell: Point) -> Point:
        """convert a cell coordinate to the cell's top-left world position"""
        x, y = cell
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise ValueError(f"Cell is outside the grid: {cell}")
        return x * self.cell_size, y * self.cell_size


@dataclass(frozen=True)
class Road:
    """a static road segment represented by a world-space rectangle"""

    id: str
    bounds: Rect
    road_type: RoadType


@dataclass(frozen=True)
class Sidewalk:
    """a walkable sidewalk segment and its neighboring segments"""

    id: str
    bounds: Rect
    connections: tuple[str, ...] = ()


@dataclass(frozen=True)
class Building:
    """a building footprint connected to the pedestrian network by an entrance"""

    id: str
    building_type: BuildingType
    bounds: Rect
    entrance: Point
    sidewalk_id: str
    capacity: int = 1


@dataclass
class VillageMap:
    """the static world consumed by rendering and simulation systems"""

    grid: Grid
    roads: list[Road] = field(default_factory=list)
    sidewalks: list[Sidewalk] = field(default_factory=list)
    buildings: list[Building] = field(default_factory=list)
    villager_spawn: Point = (512, 512)

    @property
    def world_size(self) -> tuple[int, int]:
        return self.grid.world_size

    def sidewalk(self, sidewalk_id: str) -> Sidewalk:
        """return a sidewalk by ID or raise a useful error"""
        for sidewalk in self.sidewalks:
            if sidewalk.id == sidewalk_id:
                return sidewalk
        raise KeyError(f"Unknown sidewalk: {sidewalk_id}")

    def validate(self) -> None:
        """check references and basic bounds for a hand-authored map"""
        sidewalk_ids = {sidewalk.id for sidewalk in self.sidewalks}
        building_ids = {building.id for building in self.buildings}
        if len(building_ids) != len(self.buildings):
            raise ValueError("Building IDs must be unique")

        map_width, map_height = self.world_size

        def is_inside(bounds: Rect) -> bool:
            x, y, width, height = bounds
            return (
                x >= 0
                and y >= 0
                and x + width <= map_width
                and y + height <= map_height
            )

        for road in self.roads:
            if not is_inside(road.bounds):
                raise ValueError(f"Road {road.id} extends outside the map")

        for sidewalk in self.sidewalks:
            if not is_inside(sidewalk.bounds):
                raise ValueError(f"Sidewalk {sidewalk.id} extends outside the map")
            unknown = set(sidewalk.connections) - sidewalk_ids
            if unknown:
                raise ValueError(
                    f"Sidewalk {sidewalk.id} references unknown segments: {unknown}"
                )

        for building in self.buildings:
            if not is_inside(building.bounds):
                raise ValueError(f"Building {building.id} extends outside the map")
            if building.sidewalk_id not in sidewalk_ids:
                raise ValueError(
                    f"Building {building.id} references unknown sidewalk "
                    f"{building.sidewalk_id}"
                )
            if building.capacity <= 0:
                raise ValueError(f"Building {building.id} must have capacity")


def create_test_map() -> VillageMap:
    """small hand-authored test-map"""
    village_map = VillageMap(
        grid=Grid(*DEFAULT_MAP_CELLS),
        roads=[
            Road("main-east-west", _offset_rect((0, 480, 3072, 96)), "main"),
            Road("main-north-south", _offset_rect((960, 0, 96, 2048)), "main"),
            Road("local-north", _offset_rect((320, 192, 640, 64)), "local"),
            Road("local-south", _offset_rect((1056, 896, 672, 64)), "local"),
        ],
        sidewalks=[
            Sidewalk("northwest-main", _offset_rect((0, 448, 960, 32)), ("north-west", "south-west")),
            Sidewalk("northeast-main", _offset_rect((1056, 448, 992, 32)), ("north-east", "south-east")),
            Sidewalk("north-west", _offset_rect((928, 0, 32, 480)), ("northwest-main",)),
            Sidewalk("north-east", _offset_rect((1056, 0, 32, 480)), ("northeast-main",)),
            Sidewalk("south-west", _offset_rect((928, 576, 32, 832)), ("northwest-main","southwest-main")),
            Sidewalk("south-east", _offset_rect((1056, 576, 32, 832)), ("northeast-main","southeast-main")),
            Sidewalk("southwest-main", _offset_rect((0, 576, 960, 32)), ("north-west", "south-west")),
            Sidewalk("southeast-main", _offset_rect((1056, 576, 992, 32)), ("north-east", "south-east")),
        ],
        buildings=[
            Building("house-west", "house", _offset_rect((160, 280, 160, 112)), _offset_point((240, 392)), "northwest-main"),
            Building("apartment-west", "apartment", _offset_rect((480, 240, 240, 160)), _offset_point((600, 400)), "northwest-main", 12),
            Building("shop-west", "shop", _offset_rect((720, 640, 144, 112)), _offset_point((792, 640)), "south-west", 4),
            Building("office-east", "office", _offset_rect((1248, 240, 256, 160)), _offset_point((1376, 400)), "northeast-main", 20),
            Building("shop-east", "shop", _offset_rect((1568, 640, 144, 112)), _offset_point((1640, 640)), "south-east", 4),
            Building("public-hall", "public", _offset_rect((1120, 1040, 240, 176)), _offset_point((1240, 1040)), "south-east", 30),
        ],
        villager_spawn=_offset_point((100, 100)),
    )
    village_map.validate()
    return village_map
