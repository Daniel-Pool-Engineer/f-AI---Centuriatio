"""pygame renderer for the village map"""

from __future__ import annotations

import pygame

from .map import Building, VillageMap


Color = tuple[int, int, int]


class VillageMapRenderer:
    """draws the village map"""

    background_color: Color = (225, 228, 218)
    grid_color: Color = (214, 217, 207)

    main_road_color: Color = (68, 72, 80)
    local_road_color: Color = (91, 95, 102)

    sidewalk_color: Color = (191, 187, 173)

    entrance_color: Color = (250, 190, 54)
    spawn_color: Color = (42, 116, 70)

    text_color: Color = (35, 38, 42)
    window_color: Color = (225, 239, 245)
    door_color: Color = (75, 58, 48)
    shadow_color: Color = (170, 173, 164)

    building_colors: dict[str, Color] = {
        "house": (193, 137, 105),
        "apartment": (157, 128, 181),
        "shop": (220, 175, 78),
        "office": (105, 148, 190),
        "public": (124, 169, 127),
    }

    def __init__(
        self,
        *,
        camera: tuple[float, float] = (0, 0),
        zoom: float = 0.5,
    ) -> None:
        self.camera_x, self.camera_y = camera
        self.zoom = zoom
        self.font = pygame.font.Font(None, 18)

    def set_camera(self, x: float, y: float) -> None:
        self.camera_x = x
        self.camera_y = y

    def set_zoom(self, zoom: float) -> None:
        if zoom <= 0:
            raise ValueError("zoom must be positive")
        self.zoom = zoom

    def world_to_screen(self, point: tuple[int, int]) -> tuple[int, int]:
        x, y = point

        return (
            round((x - self.camera_x) * self.zoom),
            round((y - self.camera_y) * self.zoom),
        )

    def _rect_to_screen(
        self,
        bounds: tuple[int, int, int, int],
    ) -> pygame.Rect:
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
        show_labels: bool = True,
    ) -> None:
        surface.fill(self.background_color)

        if show_grid:
            self._draw_grid(surface, village_map)

        for road in village_map.roads:
            if road.road_type == "main":
                color = self.main_road_color
            else:
                color = self.local_road_color

            pygame.draw.rect(
                surface,
                color,
                self._rect_to_screen(road.bounds),
            )

        for sidewalk in village_map.sidewalks:
            pygame.draw.rect(
                surface,
                self.sidewalk_color,
                self._rect_to_screen(sidewalk.bounds),
            )

        for building in village_map.buildings:
            self._draw_building(
                surface,
                building,
                show_labels=show_labels,
            )

        spawn = self.world_to_screen(village_map.villager_spawn)

        pygame.draw.circle(
            surface,
            self.spawn_color,
            spawn,
            max(6, round(12 * self.zoom)),
        )

    def _draw_building(
        self,
        surface: pygame.Surface,
        building: Building,
        *,
        show_labels: bool,
    ) -> None:
        bounds = self._rect_to_screen(building.bounds)

        color = self.building_colors.get(
            building.building_type,
            (145, 145, 145),
        )

        # small shadow behind the building
        shadow = bounds.move(
            max(2, round(5 * self.zoom)),
            max(2, round(5 * self.zoom)),
        )

        pygame.draw.rect(
            surface,
            self.shadow_color,
            shadow,
            border_radius=max(2, round(5 * self.zoom)),
        )

        # building
        pygame.draw.rect(
            surface,
            color,
            bounds,
            border_radius=max(2, round(5 * self.zoom)),
        )

        pygame.draw.rect(
            surface,
            self.text_color,
            bounds,
            width=max(1, round(2 * self.zoom)),
            border_radius=max(2, round(5 * self.zoom)),
        )

        self._draw_windows(surface, bounds)

        # door
        entrance = self.world_to_screen(building.entrance)

        door_width = max(4, round(12 * self.zoom))
        door_height = max(6, round(18 * self.zoom))

        door = pygame.Rect(
            entrance[0] - door_width // 2,
            entrance[1] - door_height,
            door_width,
            door_height,
        )

        pygame.draw.rect(surface, self.door_color, door)

        # entrance marker
        pygame.draw.circle(
            surface,
            self.entrance_color,
            entrance,
            max(2, round(4 * self.zoom)),
        )

        if show_labels and self.zoom >= 0.45:
            label = self.font.render(
                building.id.replace("-", " ").title(),
                True,
                self.text_color,
            )

            label_rect = label.get_rect(
                midbottom=(bounds.centerx, bounds.top - 4)
            )

            surface.blit(label, label_rect)

    def _draw_windows(
        self,
        surface: pygame.Surface,
        bounds: pygame.Rect,
    ) -> None:
        window_width = max(4, round(10 * self.zoom))
        window_height = max(4, round(8 * self.zoom))

        if bounds.width < window_width * 2:
            return

        if bounds.height < window_height * 2:
            return

        spacing_x = max(
            window_width + 3,
            round(22 * self.zoom),
        )

        spacing_y = max(
            window_height + 3,
            round(20 * self.zoom),
        )

        start_x = bounds.left + round(15 * self.zoom)
        start_y = bounds.top + round(20 * self.zoom)

        y = start_y

        while y + window_height < bounds.bottom - round(18 * self.zoom):
            x = start_x

            while x + window_width < bounds.right - round(15 * self.zoom):
                window = pygame.Rect(
                    x,
                    y,
                    window_width,
                    window_height,
                )

                pygame.draw.rect(
                    surface,
                    self.window_color,
                    window,
                )

                pygame.draw.rect(
                    surface,
                    self.text_color,
                    window,
                    width=1,
                )

                x += spacing_x

            y += spacing_y

    def _draw_grid(
        self,
        surface: pygame.Surface,
        village_map: VillageMap,
    ) -> None:
        width, height = village_map.world_size
        cell_size = village_map.grid.cell_size

        left, top = self.world_to_screen((0, 0))
        right, bottom = self.world_to_screen((width, height))

        for x in range(0, width + cell_size, cell_size):
            screen_x, _ = self.world_to_screen((x, 0))

            pygame.draw.line(
                surface,
                self.grid_color,
                (screen_x, top),
                (screen_x, bottom),
            )

        for y in range(0, height + cell_size, cell_size):
            _, screen_y = self.world_to_screen((0, y))

            pygame.draw.line(
                surface,
                self.grid_color,
                (left, screen_y),
                (right, screen_y),
            )