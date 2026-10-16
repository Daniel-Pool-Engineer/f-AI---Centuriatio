import pygame

from backend.agent.daynight import Clock

from frontend.ui.menu_bars import BottomMenuBar, RightMenuBar

from frontend.village.map import create_test_map
from frontend.village.renderer import VillageMapRenderer
from frontend.village.villagers import SHELTER_ID, VillagerManager

pygame.init()

village_map = create_test_map()
renderer = VillageMapRenderer()

screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
pygame.display.set_caption("Centuriatio")

clock = pygame.time.Clock()   # frame timer (60 FPS)
sim_clock = Clock()           # in-game day/night clock from the backend
is_panning = False
last_mouse_position: tuple[int, int] | None = None
MIN_ZOOM = 0.4
MAX_ZOOM = 1.0
ZOOM_STEP = 1.1

# the disruption currently injected into the village (None = normal day)
active_disruption: str | None = None
outage_start_day = 1  # in-game day the outage started on

right_menu = RightMenuBar()
villagers = VillagerManager(village_map)


def period_label() -> str:
    # e.g. "Normal Day 1" or "Outage Night 2"
    if active_disruption == "Power Outage":
        number = sim_clock.day_number - outage_start_day + 1
        return f"Outage {sim_clock.day_night} {number}"
    return f"Normal {sim_clock.day_night} {sim_clock.day_number}"


def log(text: str) -> None:
    # add a line to the journal with the in-game time
    right_menu.add_entry(f"[{sim_clock.get_time()}] {text}")


def log_period() -> None:
    # add a header when a new period starts
    right_menu.add_entry(f"--- {period_label()} ---")


def handle_disruption(name: str, is_active: bool) -> None:
    # called by the X-Factor menu when a disruption starts or ends
    global active_disruption, outage_start_day
    if is_active:
        active_disruption = name
        outage_start_day = sim_clock.day_number
        log_period()
        log(f"X-Factor injected: {name}")
    else:
        log(f"{name} has ended")
        active_disruption = None
        log_period()

    if name == "Power Outage":
        villagers.set_power_outage(is_active)
        if is_active:
            log(f"Villagers are heading to the {SHELTER_ID}")
        else:
            log("Power restored, villagers go back to their routine")


def reset_simulation() -> None:
    # start everything over from Normal Day 1
    global villagers, active_disruption
    sim_clock.reset()
    villagers = VillagerManager(village_map)
    active_disruption = None
    bottom_menu.clear_disruption()
    right_menu.clear()
    log_period()
    log("Simulation started")


def handle_control(name: str) -> None:
    # called by the Pause / Speed / Reset buttons
    if name == "pause":
        sim_clock.control_pause()
        log("Simulation paused" if sim_clock.paused else "Simulation resumed")
    elif name == "speed":
        sim_clock.speedup(2 if sim_clock.speed == 1 else 1)
    elif name == "reset":
        reset_simulation()
    bottom_menu.set_control_state(sim_clock.paused, sim_clock.speed)


bottom_menu = BottomMenuBar(on_disruption=handle_disruption, on_control=handle_control)


def resize_menus() -> None:
    # keep menu bars proportional when the window changes size
    size = screen.get_size()
    bottom_menu.resize(size)
    right_menu.resize(size)


def clamp_camera() -> None:
    """keep the camera inside the map bounds when the viewport changes"""
    viewport_width, viewport_height = screen.get_size()
    map_width, map_height = village_map.world_size
    visible_width = viewport_width / renderer.zoom
    visible_height = viewport_height / renderer.zoom
    max_camera_x = max(0.0, map_width - visible_width)
    max_camera_y = max(0.0, map_height - visible_height)
    renderer.set_camera(
        min(max(renderer.camera_x, 0.0), max_camera_x),
        min(max(renderer.camera_y, 0.0), max_camera_y),
    )


def center_camera() -> None:
    """center the viewport in the middle of the map"""
    viewport_width, viewport_height = screen.get_size()
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
    new_zoom = min(max(new_zoom, MIN_ZOOM), MAX_ZOOM)
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


def draw_overlay(alpha: int) -> None:
    # darken the map (used for night and power outages)
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((10, 15, 40, alpha))
    screen.blit(overlay, (0, 0))


resize_menus()
center_camera()
log_period()
log("Simulation started")

while True:
    # real seconds since the last frame (also caps the game at 60 FPS)
    dt = clock.tick(60) / 1000

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
            if not bottom_menu.rect.collidepoint(event.pos) and not right_menu.rect.collidepoint(
                event.pos
            ):
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
    # advance the day/night clock (it handles pause and speed itself)
    for phase, _day in sim_clock.update(dt):
        villagers.set_night(phase == "Night")
        log_period()
        log("Night falls, villagers head home" if phase == "Night" else "Morning, villagers start their day")

    # villagers move faster at 2x and stop when paused
    sim_dt = 0 if sim_clock.paused else dt * sim_clock.speed
    for message in villagers.update(sim_dt):
        log(message)

    status = f"{period_label()}  ·  {sim_clock.get_time()}"
    if sim_clock.paused:
        status += "  ·  Paused"
    bottom_menu.set_status(status)

    # Render the graphics here.
    renderer.draw(
        screen,
        village_map,
        show_grid=True,
        show_labels=True,
    )
    if sim_clock.day_night == "Night":
        draw_overlay(90)
    if active_disruption == "Power Outage":
        draw_overlay(140)
    villagers.draw(screen, renderer)
    right_menu.draw(screen)
    bottom_menu.draw(screen)

    pygame.display.flip()  # Refresh on-screen display