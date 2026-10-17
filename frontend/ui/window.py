from math import hypot

import pygame

#frontend imports
from frontend.ui.menu_bars import BottomMenuBar, RightMenuBar
from frontend.village.map import create_test_map
from frontend.village.renderer import VillageMapRenderer
from frontend.village.navigation import route
from frontend.village.sprite import VillagerSprite

#Backend imports
from backend.agent.agent import VillagerAgent, VillagerContext
from backend.agent.client import LLMClient
from backend.agent.profile import CITIZEN

pygame.init()

village_map = create_test_map()
renderer = VillageMapRenderer()
maria = VillagerSprite(village_map.villager_spawn)
maria_agent = VillagerAgent("m1", "Maria", CITIZEN, llm_client=LLMClient())
maria_location = "home_a"
maria_previous_action: str | None = None
maria_cooldown = 0.0
maria_current_task = "Waiting"
maria_selected = False

screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
pygame.display.set_caption("Centuriatio")

clock = pygame.time.Clock()
bottom_menu = BottomMenuBar()
right_menu = RightMenuBar()
is_panning = False
last_mouse_position: tuple[int, int] | None = None
MAX_ZOOM = 1.0
ZOOM_STEP = 1.1
info_font = pygame.font.Font(None, 20)


def resize_menus() -> None:
    # keep menu bars proportional when the window changes size
    size = screen.get_size()
    bottom_menu.resize(size)
    right_menu.resize(size)


def map_view_size() -> tuple[int, int]:
    """return the unobstructed viewport size above and left of the menus"""
    return max(1, right_menu.rect.left), max(1, bottom_menu.rect.top)


def minimum_zoom() -> float:
    """fit the map's horizontal boundaries to the unobstructed viewport"""
    viewport_width, _ = map_view_size()
    map_width, _ = village_map.world_size
    return viewport_width / map_width


def clamp_camera() -> None:
    """keep the map within the unobstructed viewport at the current zoom"""
    min_zoom = minimum_zoom()
    renderer.set_zoom(min(max(renderer.zoom, min_zoom), max(MAX_ZOOM, min_zoom)))
    viewport_width, viewport_height = map_view_size()
    map_width, map_height = village_map.world_size
    visible_width = viewport_width / renderer.zoom
    visible_height = viewport_height / renderer.zoom
    if visible_width >= map_width:
        camera_x = (map_width - visible_width) / 2
    else:
        camera_x = min(max(renderer.camera_x, 0.0), map_width - visible_width)
    if visible_height >= map_height:
        camera_y = (map_height - visible_height) / 2
    else:
        camera_y = min(max(renderer.camera_y, 0.0), map_height - visible_height)
    renderer.set_camera(
        camera_x,
        camera_y,
    )


def center_camera() -> None:
    """center the map within the unobstructed viewport"""
    viewport_width, viewport_height = map_view_size()
    map_width, map_height = village_map.world_size
    renderer.set_camera(
        (map_width - viewport_width / renderer.zoom) / 2,
        (map_height - viewport_height / renderer.zoom) / 2,
    )
    clamp_camera()


def zoom_at(position: tuple[int, int], direction: int) -> None:
    """zoom around a screen position while keeping its world location fixed"""
    old_zoom = renderer.zoom
    new_zoom = old_zoom * (ZOOM_STEP if direction > 0 else 1 / ZOOM_STEP)
    min_zoom = minimum_zoom()
    new_zoom = min(max(new_zoom, min_zoom), max(MAX_ZOOM, min_zoom))
    if new_zoom == old_zoom:
        return

    mouse_x, mouse_y = position
    world_x = renderer.camera_x + mouse_x / old_zoom
    world_y = renderer.camera_y + mouse_y / old_zoom
    renderer.set_zoom(new_zoom)
    renderer.set_camera(
        world_x - mouse_x / new_zoom,
        world_y - mouse_y / new_zoom,
    )
    clamp_camera()


def maria_screen_position() -> tuple[int, int]:
    return renderer.world_to_screen((int(maria.x), int(maria.y)))


def maria_hit_test(position: tuple[int, int]) -> bool:
    if bottom_menu.rect.collidepoint(position) or right_menu.rect.collidepoint(position):
        return False
    sprite_x, sprite_y = maria_screen_position()
    return hypot(position[0] - sprite_x, position[1] - sprite_y) <= maria.radius + 5


def draw_maria_info() -> None:
    lines = (
        "Maria",
        f"Role: {maria_agent.role.replace('_', ' ').title()}",
        f"Task: {maria_current_task}",
    )
    padding = 8
    line_height = info_font.get_linesize()
    text_surfaces = [info_font.render(line, True, (245, 246, 250)) for line in lines]
    width = max(text.get_width() for text in text_surfaces) + padding * 2
    height = line_height * len(lines) + padding * 2
    viewport_width, viewport_height = map_view_size()
    width = min(width, max(1, viewport_width - 8))
    height = min(height, max(1, viewport_height - 8))

    sprite_x, sprite_y = maria_screen_position()
    left = min(
        max(sprite_x - width // 2, 4),
        viewport_width - width - 4,
    )
    top = min(
        max(sprite_y - maria.radius - height - 8, 4),
        viewport_height - height - 4,
    )
    popup = pygame.Rect(left, top, width, height)
    pygame.draw.rect(screen, (31, 35, 48), popup, border_radius=6)
    pygame.draw.rect(screen, (180, 190, 210), popup, width=1, border_radius=6)
    for index, text in enumerate(text_surfaces):
        screen.blit(text, (left + padding, top + padding + index * line_height))


resize_menus()
center_camera()
dt_seconds = 0.0

while True:
    # Process player inputs.
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
        if event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            resize_menus()
            clamp_camera()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == pygame.BUTTON_LEFT:
            on_maria = maria_hit_test(event.pos)
            maria_selected = on_maria
            over_menu = (
                bottom_menu.rect.collidepoint(event.pos)
                or right_menu.rect.collidepoint(event.pos)
            )
            if not on_maria and not over_menu:
                is_panning = True
                last_mouse_position = event.pos
        if event.type == pygame.MOUSEBUTTONUP and event.button == pygame.BUTTON_LEFT:
            is_panning = False
            last_mouse_position = None
        if event.type == pygame.MOUSEMOTION and is_panning and last_mouse_position is not None:
            previous_x, previous_y = last_mouse_position
            mouse_x, mouse_y = event.pos
            renderer.set_camera(
                renderer.camera_x - (mouse_x - previous_x) / renderer.zoom,
                renderer.camera_y - (mouse_y - previous_y) / renderer.zoom,
            )
            clamp_camera()
            last_mouse_position = event.pos

        if event.type == pygame.MOUSEWHEEL:
            mouse_position = pygame.mouse.get_pos()
            over_menu = (
                bottom_menu.rect.collidepoint(mouse_position)
                or right_menu.rect.collidepoint(mouse_position)
            )
            if not over_menu:
                zoom_at(mouse_position, event.y)


        bottom_menu.handle_event(event)
        right_menu.handle_event(event)

    # Do logical updates here.
    # ...

    #screen.fill("white")  # Fill the display with a solid color
    maria.update(dt_seconds)
    maria_cooldown -= dt_seconds
    if not maria.path and maria_cooldown <= 0:
        maria_cooldown = 2.0
        ctx = VillagerContext(
            villager_id="m1",
            name="Maria",
            location_id=maria_location,
            day=1,
            phase="day",
            crisis_active=False,
            crisis_day=0,
            crisis_duration=0,
            crisis_area=None,
            power_on=True,
            previous_action=maria_previous_action,
        )
        action = maria_agent.decide(ctx)
        print(f"Maria: {action.action} -> {action.target_location} | {action.journal}")
        maria_previous_action = action.action
        maria_current_task = action.action.replace("_", " ").title()
        if action.target_location:
            destination = action.target_location.replace("_", " ").title()
            maria_current_task = f"{maria_current_task} - {destination}"
        if action.target_location and action.target_location != maria_location:
            try:
                maria.set_path(route(village_map, maria_location, action.target_location))
                maria_location = action.target_location
            except ValueError as exc:
                print(f"  route failed: {exc}")

    # Render the graphics here.
    renderer.draw(
        screen,
        village_map,
        show_grid=True,
        show_labels=True,
    )
    renderer.draw_sprite(screen, maria)
    if maria_selected or maria_hit_test(pygame.mouse.get_pos()):
        draw_maria_info()
    right_menu.draw(screen)
    bottom_menu.draw(screen)

    pygame.display.flip()  # Refresh on-screen display
    dt_seconds = clock.tick(60) / 1000.0