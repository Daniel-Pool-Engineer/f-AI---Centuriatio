from __future__ import annotations

import pygame

from pathlib import Path

from .map import Building, VillageMap


Color = tuple[int, int, int]


class VillageMapRenderer:
    """draw a :class:`VillageMap` using camera position and zoom level"""

    background_color: Color = (228, 231, 220)
    grid_color: Color = (211, 215, 204)
    main_road_color: Color = (74, 78, 86)
    local_road_color: Color = (94, 98, 105)
    sidewalk_color: Color = (188, 185, 171)
    entrance_color: Color = (250, 190, 54)
    spawn_color: Color = (42, 116, 70)
    text_color: Color = (30, 34, 38)
    building_colors: dict[str, Color] = {
        # Houses
        "home_a": (196, 145, 105),      # warm brown
        "home_b": (185, 185, 190),      # light gray apartment
        "home_c": (170, 120, 145),      # muted pink
        "home_d": (125, 155, 190),      # muted blue

        # Public / community buildings
        "hospital": (235, 235, 228),    # off-white
        "fire": (178, 65, 55),          # fire-station red
        "police": (75, 95, 130),        # dark blue
        "school": (205, 175, 75),       # yellow
        "grocery": (190, 145, 75),      # warm tan
        "electrical": (125, 130, 128),  # gray utility building

        # Work / office
        "work": (145, 155, 165),        # gray-blue office
    }
    building_border_colors: dict[str, Color] = {
        "home_a": (130, 85, 60),
        "home_b": (105, 105, 110),
        "home_c": (115, 75, 95),
        "home_d": (75, 100, 130),

        "hospital": (180, 180, 175),
        "fire": (125, 40, 35),
        "police": (45, 60, 85),
        "school": (145, 120, 45),
        "grocery": (135, 95, 45),
        "electrical": (80, 85, 84),
        "work": (90, 100, 110),
    }

    def __init__(
        self,
        *,
        camera: tuple[float, float] = (0, 0),
        zoom: float = 0.5,
    ) -> None:
        self.camera_x, self.camera_y = camera
        self.zoom = zoom
        self.font = pygame.font.Font(None, 16)

        # Adds PNG Icons from Assets
        self.building_icons = {}

        icon_folder = Path(__file__).parent.parent / "assets" / "buildings"

        icon_names = [
            "house",
            "apartment",
            "hospital",
            "grocery",
            "school",
            "fire",
            "police",
            "electrical",
            "office",
        ]

        for icon_name in icon_names:
            path = icon_folder / f"{icon_name}.png"

            if path.exists():
                self.building_icons[icon_name] = pygame.image.load(path).convert_alpha()

    def set_camera(self, x: float, y: float) -> None:
        """move the camera to a world-space position"""
        self.camera_x = x
        self.camera_y = y

    def set_zoom(self, zoom: float) -> None:
        """set the render scale, 1.0 means one world unit per pixel"""
        if zoom <= 0:
            raise ValueError("zoom must be positive")
        self.zoom = zoom

    def world_to_screen(self, point: tuple[int, int]) -> tuple[int, int]:
        """convert a world-space point into screen coordinates"""
        x, y = point
        return (
            round((x - self.camera_x) * self.zoom),
            round((y - self.camera_y) * self.zoom),
        )

    def _rect_to_screen(self, bounds: tuple[int, int, int, int]) -> pygame.Rect:
        x, y, width, height = bounds
        screen_x, screen_y = self.world_to_screen((x, y))
        return pygame.Rect(
            screen_x,
            screen_y,
            max(1, round(width * self.zoom)),
            max(1, round(height * self.zoom)),
        )

    def draw(
        self,
        surface: pygame.Surface,
        village_map: VillageMap,
        *,
        show_grid: bool = False,
        show_labels: bool = False,
    ) -> None:
        """draw the map in layers from background to entrances"""
        surface.fill(self.background_color)

        if show_grid:
            self._draw_grid(surface, village_map)

        for road in village_map.roads:
            color = (
                self.main_road_color
                if road.road_type == "main"
                else self.local_road_color
            )
            pygame.draw.rect(surface, color, self._rect_to_screen(road.bounds))

        for sidewalk in village_map.sidewalks:
            pygame.draw.rect(
                surface,
                self.sidewalk_color,
                self._rect_to_screen(sidewalk.bounds),
            )

        for building in village_map.buildings:
            self._draw_building(surface, building, show_labels=show_labels)

        spawn = self.world_to_screen(village_map.villager_spawn)
        pygame.draw.circle(surface, self.spawn_color, spawn, max(8, round(16 * self.zoom)))

    def _draw_building(
        self,
        surface: pygame.Surface,
        building: Building,
        *,
        show_labels: bool,
    ) -> None:
        bounds = self._rect_to_screen(building.bounds)
        color = self.building_colors.get(building.id, (145, 145, 145))
        pygame.draw.rect(surface, color, bounds, border_radius=max(1, round(4 * self.zoom)))
        
        border_color = self.building_border_colors.get(building.id, self.text_color)
        pygame.draw.rect(surface, border_color, bounds, width=2)

        # Adds the PNG Icon to the Building
        icon_name = building.id

        if building.id.startswith("home"):
            icon_name = building.building_type

        if building.id == "work":
            icon_name = "office"

        icon = self.building_icons.get(icon_name)

        if icon is not None:
            icon_size = int(min(bounds.width, bounds.height) * 0.45)

            icon = pygame.transform.smoothscale(
                icon,
                (icon_size, icon_size),
            )

            icon_rect = icon.get_rect(
                center=bounds.center
            )

            surface.blit(icon, icon_rect)

        entrance = self.world_to_screen(building.entrance)
        pygame.draw.circle(
            surface,
            self.entrance_color,
            entrance,
            max(2, round(5 * self.zoom)),
        )

        if show_labels:
            label = self.font.render(building.id, True, self.text_color)
            surface.blit(label, (bounds.left + 3, bounds.top + 3))

    def _draw_grid(self, surface: pygame.Surface, village_map: VillageMap) -> None:
        width, height = village_map.world_size
        cell_size = village_map.grid.cell_size
        left, top = self.world_to_screen((0, 0))
        right, bottom = self.world_to_screen((width, height))

        for x in range(0, width + cell_size, cell_size):
            screen_x, _ = self.world_to_screen((x, 0))
            pygame.draw.line(surface, self.grid_color, (screen_x, top), (screen_x, bottom))

        for y in range(0, height + cell_size, cell_size):
            _, screen_y = self.world_to_screen((0, y))
            pygame.draw.line(surface, self.grid_color, (left, screen_y), (right, screen_y))

    def draw_sprite(self, surface: pygame.Surface, sprite) -> None:
        x,y = self.world_to_screen((int(sprite.x), int(sprite.y)))
        pygame.draw.circle(surface, sprite.color, (x,y), sprite.radius)