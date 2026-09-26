"""floating menu bars rendered on top of the application surface"""

from __future__ import annotations

from collections.abc import Callable

import pygame

from frontend.ui.button import Button


Color = tuple[int, int, int]

# only one x-factor for now, add more names here later if needed
DEFAULT_DISRUPTIONS: tuple[str, ...] = ("Power Outage",)


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
    padding = 10
    button_gap = 12
    max_button_width = 170
    max_button_height = 44

    def __init__(
        self,
        on_disruption: Callable[[str, bool], None] | None = None,
        disruptions: tuple[str, ...] = DEFAULT_DISRUPTIONS,
    ) -> None:
        super().__init__(
            background=(114, 183, 249),
            border=(127, 83, 246),
        )
        # called as on_disruption(name, is_active) when a disruption starts or ends
        self.on_disruption = on_disruption
        self.active_disruption: str | None = None
        self.buttons = [
            Button(name, on_click=lambda name=name: self.toggle_disruption(name))
            for name in disruptions
        ]

    def toggle_disruption(self, name: str) -> None:
        """start the clicked disruption, or end it if it is already active"""
        previous = self.active_disruption

        if previous is not None:
            self.active_disruption = None
            self._notify(previous, False)

        if previous != name:
            self.active_disruption = name
            self._notify(name, True)

        for button in self.buttons:
            button.is_active = button.label == self.active_disruption

    def _notify(self, name: str, is_active: bool) -> None:
        if self.on_disruption is not None:
            self.on_disruption(name, is_active)

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
        self._layout_buttons()

    def _layout_buttons(self) -> None:
        """place the buttons in a centered row under the menu title"""
        if not self.buttons:
            return

        title_height = self.font.get_linesize()
        top = self.rect.top + self.padding + title_height
        available_height = self.rect.bottom - self.padding - top
        button_height = max(1, min(self.max_button_height, available_height))

        count = len(self.buttons)
        available_width = self.rect.width - (self.padding * 2)
        button_width = (available_width - self.button_gap * (count - 1)) / count
        button_width = max(1, min(self.max_button_width, int(button_width)))

        row_width = button_width * count + self.button_gap * (count - 1)
        x = self.rect.centerx - row_width // 2
        y = top + (available_height - button_height) // 2

        for button in self.buttons:
            button.rect = pygame.Rect(x, y, button_width, button_height)
            x += button_width + self.button_gap

    def handle_event(self, event: pygame.event.Event) -> None:
        for button in self.buttons:
            button.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        label = self.font.render("X-Factor menu", True, self.text_color)
        label_rect = label.get_rect(
            midtop=(self.rect.centerx, self.rect.top + self.padding // 2)
        )
        surface.blit(label, label_rect)

        for button in self.buttons:
            button.draw(surface)


class RightMenuBar(FloatingMenuBar):
    """menu bar spanning twenty percent of the window along the right edge"""

    width_ratio = 0.20
    padding = 12
    entry_gap = 6

    def __init__(self, max_entries: int = 100) -> None:
        super().__init__(
            background=(105, 161, 65),
            border=(127, 83, 246),
        )
        self.entry_font = pygame.font.Font(None, 20)
        self.max_entries = max_entries
        self.entries: list[str] = []  # newest entry first

    def add_entry(self, text: str) -> None:
        """add a line to the top of the villager journal"""
        self.entries.insert(0, text)
        del self.entries[self.max_entries:]

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

    def _wrap_text(self, text: str, max_width: int) -> list[str]:
        """split text into lines that fit inside max_width pixels"""
        lines: list[str] = []
        current = ""
        for word in text.split():
            candidate = word if not current else f"{current} {word}"
            if self.entry_font.size(candidate)[0] <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        label = self.font.render("Villager Journal", True, self.text_color)
        # label = pygame.transform.rotate(label, 90)
        label_rect = label.get_rect(
            midtop=(self.rect.centerx, self.rect.top + self.font.get_linesize() // 2)
        )
        surface.blit(label, label_rect)

        # keep journal text from spilling outside the panel
        previous_clip = surface.get_clip()
        surface.set_clip(self.rect.inflate(-4, -4))

        text_width = self.rect.width - self.padding * 2
        line_height = self.entry_font.get_linesize()
        y = label_rect.bottom + self.padding

        for entry in self.entries:
            for line in self._wrap_text(entry, text_width):
                if y + line_height > self.rect.bottom - self.padding:
                    surface.set_clip(previous_clip)
                    return
                text = self.entry_font.render(line, True, self.text_color)
                surface.blit(text, (self.rect.left + self.padding, y))
                y += line_height
            y += self.entry_gap

        surface.set_clip(previous_clip)