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
        text_color: Color = (240, 242, 245),
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
        on_control: Callable[[str], None] | None = None,
        disruptions: tuple[str, ...] = DEFAULT_DISRUPTIONS,
    ) -> None:
        super().__init__(
            background=(55, 64, 82),
            border=(125, 140, 170),
        )
        # called as on_disruption(name, is_active) when a disruption starts or ends
        self.on_disruption = on_disruption
        # called as on_control("pause" | "speed" | "reset")
        self.on_control = on_control
        self.active_disruption: str | None = None
        self.status_text = ""
        self._title_surface = None
        self._status_surface = None
        self._last_status_text = ""

        self.disruption_buttons = [
            Button(name, on_click=lambda name=name: self.toggle_disruption(name))
            for name in disruptions
        ]

        # simulation controls
        self.pause_button = Button("Pause", on_click=lambda: self._control("pause"))
        self.speed_button = Button("Speed 1x", on_click=lambda: self._control("speed"))
        self.reset_button = Button("Reset", on_click=lambda: self._control("reset"))

        self.buttons = [
            *self.disruption_buttons,
            self.pause_button,
            self.speed_button,
            self.reset_button,
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

        for button in self.disruption_buttons:
            button.is_active = button.label == self.active_disruption

    def clear_disruption(self) -> None:
        # turn off the active disruption without sending a notification (used by reset)
        self.active_disruption = None
        for button in self.disruption_buttons:
            button.is_active = False

    def set_control_state(self, paused: bool, speed: int) -> None:
        # update the control button labels to match the clock
        self.pause_button.label = "Resume" if paused else "Pause"
        self.speed_button.label = f"Speed {speed}x"

    def set_status(self, text: str) -> None:
        # text shown in the top-left corner, e.g. "Normal Day 1 · 10:30"
        self.status_text = text

    def _control(self, name: str) -> None:
        if self.on_control is not None:
            self.on_control(name)

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

        if self._title_surface is None:
            self._title_surface = self.font.render("X-Factor menu", True, self.text_color)

        label_rect = self._title_surface.get_rect(
            midtop=(self.rect.centerx, self.rect.top + self.padding // 2)
        )
        surface.blit(self._title_surface, label_rect)

        # day/time status on the left
        if self.status_text:
            if self.status_text != self._last_status_text:
                self._status_surface = self.font.render(self.status_text, True, self.text_color)
                self._last_status_text = self.status_text

                
            surface.blit(self._status_surface, (self.rect.left + self.padding * 2, self.rect.top + self.padding // 2))

        for button in self.buttons:
            button.draw(surface)


class RightMenuBar(FloatingMenuBar):
    """menu bar spanning twenty percent of the window along the right edge"""

    width_ratio = 0.20
    padding = 12
    entry_gap = 6

    def __init__(self, max_entries: int = 100) -> None:
        super().__init__(
            background=(55, 64, 82),
            border=(125, 140, 170),
        )
        self.entry_font = pygame.font.Font(None, 20)
        self.max_entries = max_entries
        self.entries: list[str] = []  # newest entry first

        self._title_surface = None
        self._entry_cache: dict [ str, pygame.Surface] ={}

    def add_entry(self, text: str) -> None:
        """add a line to the bottom of the villager journal"""
        self.entries.append(text)
        # Remove the oldest entry if we exceed the max
        if len(self.entries) > self.max_entries:
            self.entries.pop(0)

    def clear(self) -> None:
        # remove every journal entry (used by reset)
        self.entries.clear()
        self._entry_cache.clear()

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
        
        if self._title_surface is None:
            self._title_surface = self.font.render("Villager Journal", True, self.text_color)
            
        label_rect = self._title_surface.get_rect(
            midtop=(self.rect.centerx, self.rect.top + self.font.get_linesize() // 2)
        )
        surface.blit(self._title_surface, label_rect)

        previous_clip = surface.get_clip()
        surface.set_clip(self.rect.inflate(-4, -4))

        text_width = self.rect.width - self.padding * 2
        line_height = self.entry_font.get_linesize()
        start_y = label_rect.bottom + self.padding
        max_y = self.rect.bottom - self.padding
        
        # 1. Flatten entries into wrapped lines (keeping track of where gaps go)
        all_lines = []
        for entry in self.entries:
            wrapped = self._wrap_text(entry, text_width)
            for i, line in enumerate(wrapped):
                # is this the last line of the entry? (so we add a gap after)
                is_last_line = (i == len(wrapped) - 1)
                all_lines.append((line, is_last_line))
        
        # 2. Work backwards from the bottom to see which lines fit on screen
        lines_to_draw = []
        current_y = max_y
        
        for line, is_last in reversed(all_lines):
            needed_height = line_height + (self.entry_gap if is_last else 0)
            if current_y - needed_height < start_y:
                break # We ran out of vertical space
            lines_to_draw.append((line, is_last))
            current_y -= needed_height
            
        # 3. Reverse back to chronological order (oldest -> newest) and draw
        lines_to_draw.reverse()
        
        y = start_y
        for line, is_last in lines_to_draw:
            if line not in self._entry_cache:
                self._entry_cache[line] = self.entry_font.render(line, True, self.text_color)
            
            surface.blit(self._entry_cache[line], (self.rect.left + self.padding, y))
            y += line_height
            if is_last:
                y += self.entry_gap

        surface.set_clip(previous_clip)