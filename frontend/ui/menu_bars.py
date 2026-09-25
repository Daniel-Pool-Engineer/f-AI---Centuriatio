"""floating menu bars rendered on top of the application surface"""

from __future__ import annotations

import pygame


Color = tuple[int, int, int]


class FloatingMenuBar:
    """base class for a rounded menu bar"""

    def __init__(
        self,
        *,
        background: Color = (31, 35, 48),
        border: Color = (92, 101, 125),
        text_color: Color = (0, 0, 0),
    ) -> None:
        self.background = background
        self.border = border
        self.text_color = text_color
        self.font = pygame.font.Font(None, 24)
        self.rect = pygame.Rect(0, 0, 0, 0)

    def draw(self, surface: pygame.Surface) -> None:
        """draw the bar and its labels on the supplied surface"""
        pygame.draw.rect(
            surface,
            self.background,
            self.rect,
            border_radius=12,
        )
        pygame.draw.rect(
            surface,
            self.border,
            self.rect,
            width=2,
            border_radius=12,
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        """handle menu input, subclasses can add interactive controls"""


class BottomMenuBar(FloatingMenuBar):
    """menu bar spanning the bottom fifteen percent of the window"""

    height_ratio = 0.15

    def __init__(self) -> None:
        super().__init__(
            background=(114, 183, 249),
            border=(127, 83, 246),
        )

    def resize(self, surface_size: tuple[int, int]) -> None:
        width, height = surface_size
        bar_height = max(1, round(height * self.height_ratio))
        margin = max(8, round(height * 0.015))
        self.rect = pygame.Rect(
            margin,
            height - bar_height - margin,
            width - (margin * 2),
            bar_height,
        )

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        label = self.font.render("X-Factor menu", True, self.text_color)
        surface.blit(label, label.get_rect(center=self.rect.center))


class RightMenuBar(FloatingMenuBar):
    """menu bar spanning twenty percent of the window along the right edge"""

    width_ratio = 0.20

    def __init__(self) -> None:
        super().__init__(
            background=(105, 161, 65),
            border=(127, 83, 246),
        )

    def resize(self, surface_size: tuple[int, int]) -> None:
        width, height = surface_size
        bar_width = max(1, round(width * self.width_ratio))
        margin = max(8, round(width * 0.015))
        self.rect = pygame.Rect(
            width - bar_width - margin,
            margin,
            bar_width,
            height - (margin * 2),
        )

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        label = self.font.render("Villager Journal", True, self.text_color)
        # label = pygame.transform.rotate(label, 90)
        label_rect = label.get_rect(
            midtop=(self.rect.centerx, self.rect.top + self.font.get_linesize() // 2)
        )
        surface.blit(label, label_rect)
