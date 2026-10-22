from math import hypot

import pygame

# backend imports
from backend.agent.daynight import Clock
from backend.agent.agent import VillagerAgent, VillagerContext
from backend.agent.profile import CITIZEN, FIREFIGHTER, ELECTRICIAN, DOCTOR
from backend.simulation_state import WorldState
from backend.simulation_loop import BackendSimulation

# frontend imports
from frontend.ui.menu_bars import BottomMenuBar, RightMenuBar
from frontend.village.map import create_test_map
from frontend.village.navigation import route
from frontend.village.renderer import VillageMapRenderer
from frontend.village.sprite import VillagerSprite
from frontend.village.villagers import SHELTER_ID, VillagerManager

pygame.init()

# the LLM needs the keys in .env, without them Maria uses her fallback action
try:
    from backend.agent.client import LLMClient
    llm_client = LLMClient()
except Exception as exc:
    print(f"LLM not available, Maria will use fallback actions: {exc}")
    llm_client = None

OUTAGE_DURATION_DAYS = 3        # fixed for now, a duration selector can replace this later
OUTAGE_AREA = "whole village"

world_state = WorldState()
backend_sim = BackendSimulation(world_state, llm_client)
backend_sim.start()

village_map = create_test_map()

screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
pygame.display.set_caption("Centuriatio")

renderer = VillageMapRenderer()

clock = pygame.time.Clock()   # frame timer (60 FPS)
sim_clock = Clock()           # in-game day/night clock from the backend
is_panning = False
last_mouse_position: tuple[int, int] | None = None
MAX_ZOOM = 1.0
ZOOM_STEP = 1.1
info_font = pygame.font.Font(None, 20)

# the disruption currently injected into the village (None = normal day)
active_disruption: str | None = None
outage_start_day = 1  # in-game day the outage started on

right_menu = RightMenuBar()
villagers = VillagerManager(village_map)

# Maria is controlled by the backend AI agent
maria_agent = VillagerAgent("m1", "Maria", CITIZEN, llm_client=llm_client)
maria = VillagerSprite(village_map.villager_spawn)
maria_location = "home_a"
maria_previous_action: str | None = None
maria_cooldown = 0.0
maria_current_task = "Waiting"
maria_selected = False


def reset_maria() -> None:
    # put Maria back home with no history
    global maria, maria_location, maria_previous_action, maria_cooldown, maria_current_task
    maria = VillagerSprite(village_map.villager_spawn)
    maria_location = "home_a"
    maria_previous_action = None
    maria_cooldown = 0.0
    maria_current_task = "Waiting"


def outage_day() -> int:
    # 1 on the day the outage started
    return sim_clock.day_number - outage_start_day + 1


def period_label() -> str:
    # e.g. "Normal Day 1" or "Outage Night 2"
    if active_disruption == "Power Outage":
        return f"Outage {sim_clock.day_night} {outage_day()}"
    return f"Normal {sim_clock.day_night} {sim_clock.day_number}"


def log(text: str) -> None:
    # add a line to the journal with the in-game time
    right_menu.add_entry(f"[{sim_clock.get_time()}] {text}")


def log_period() -> None:
    # add a header when a new period starts
    right_menu.add_entry(f"--- {period_label()} ---")


def handle_disruption(name: str, is_active: bool) -> None:
    # called by the X-Factor menu when a disruption starts or ends
    global active_disruption, outage_start_day, maria_cooldown
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
        # Villagers log their own departure individually
        for message in villagers.set_power_outage(is_active):
            log(message)
        maria_cooldown = 0.0
        if not is_active:
            log("Power restored, villagers go back to their routine")


def reset_simulation() -> None:
    # start everything over from Normal Day 1
    global villagers, active_disruption
    sim_clock.reset()
    villagers = VillagerManager(village_map)
    reset_maria()
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

_overlay_surface = None

def draw_overlay(alpha: int) -> None:
    global _overlay_surface
    if _overlay_surface is None or _overlay_surface.get_size() != screen.get_size():
        _overlay_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    
    _overlay_surface.fill((10, 15, 40, alpha))
    screen.blit(_overlay_surface, (0, 0))


def apply_maria_action(action) -> None:
    global maria_previous_action, maria_current_task, maria_location
    print(f"Maria: {action.action} -> {action.target_location} | {action.journal}")

    if action.journal and action.action != maria_previous_action:
        log(f"Maria: {action.journal}")

    maria_previous_action = action.action
    maria_current_task = action.action.replace("_", " ").title()
    if action.target_location:
        destination = action.target_location.replace("_", " ").title()
        maria_current_task = f"{maria_current_task} - {destination}"
    if action.target_location and action.target_location != maria_location:
        try:
            maria.set_path(route(village_map, maria_location, action.target_location))
            maria_location = action.target_location
        except (ValueError, KeyError) as exc:
            print(f"  route failed: {exc}")


def update_agents(sim_dt: float) -> None:
    global maria_cooldown
    
    # Process results from the backend AI, the output of the batch system
    with world_state.lock:
        if world_state.is_data_ready:
            for v_id, action in world_state.new_actions.items():
                if v_id == "m1":
                    apply_maria_action(action)
                else:
                    villager = villagers.get_villager(v_id)
                    if villager:
                        print(f"{villager.name}: {action.action} -> {action.target_location}")
                        if action.journal:
                            log(f"{villager.name}: {action.journal}")
                        
                        villager.previous_action = action.action
                        
                        if action.target_location and action.target_location != villager.location_id:
                            try:
                                villagers.send_to(villager, action.target_location)
                                villager.wait_time = 999.0 # Freeze timer while walking
                            except (ValueError, KeyError) as exc:
                                print(f"  route failed for {villager.name}: {exc}")
                                villager.wait_time = 5.0
                        else:
                            if villager.agent.profile.role == "first_responder" and villager.location_id != "school":
                                choices = [b for b in villagers.buildings if b != villager.location_id]
                                next_patrol = villagers.rng.choice(choices)
                                try:
                                    villagers.send_to(villager, next_patrol)
                                    villager.wait_time = 999.0
                                except Exception:
                                    villager.wait_time = 5.0
                            else:
                                villager.wait_time = 5.0
            
            world_state.is_data_ready = False
            world_state.new_actions.clear()

    maria.update(sim_dt)
    maria_cooldown -= sim_dt

    if sim_clock.paused:
        return

    if not maria.path and maria_cooldown <= 0:
        if not backend_sim.is_queued("m1"):
            outage = active_disruption == "Power Outage"
            ctx = VillagerContext(
                villager_id="m1", name="Maria", location_id=maria_location,
                day=sim_clock.day_number, phase=sim_clock.day_night.lower(),
                crisis_active=outage, crisis_day=outage_day() if outage else 0,
                crisis_duration=OUTAGE_DURATION_DAYS if outage else 0,
                crisis_area=OUTAGE_AREA if outage else None,
                power_on=not outage, previous_action=maria_previous_action,
            )
            backend_sim.queue_agent("m1", maria_agent, ctx)
            maria_cooldown = 5.0

    for villager in villagers.villagers:
        if villager.is_scripted:
            continue
        if not villager.is_walking and villager.wait_time <= 0:
            if not backend_sim.is_queued(villager.agent_id):
                outage = active_disruption == "Power Outage"
                ctx = VillagerContext(
                    villager_id=villager.agent_id, 
                    name=villager.name, 
                    location_id=villager.location_id or "unknown",
                    day=sim_clock.day_number, 
                    phase=sim_clock.day_night.lower(),
                    crisis_active=outage, 
                    crisis_day=outage_day() if outage else 0,
                    crisis_duration=OUTAGE_DURATION_DAYS if outage else 0,
                    crisis_area=OUTAGE_AREA if outage else None,
                    power_on=not outage, 
                    previous_action=villager.previous_action,
                )
                # Send them to the backend queue
                backend_sim.queue_agent(villager.agent_id, villager.agent, ctx)
                villager.wait_time = 999.0

def maria_screen_position() -> tuple[int, int]:
    return renderer.world_to_screen((int(maria.x), int(maria.y)))


def maria_hit_test(position: tuple[int, int]) -> bool:
    if bottom_menu.rect.collidepoint(position) or right_menu.rect.collidepoint(position):
        return False
    sprite_x, sprite_y = maria_screen_position()
    return hypot(position[0] - sprite_x, position[1] - sprite_y) <= maria.radius + 5


def draw_maria() -> None:
    # Maria gets a yellow name tag so she stands out as the AI villager
    position = maria_screen_position()
    pygame.draw.circle(screen, maria.color, position, maria.radius)
    pygame.draw.circle(screen, (255, 255, 255), position, maria.radius, width=2)
    label = info_font.render("Maria (YOU)", True, (20, 20, 20))
    label_rect = label.get_rect(midbottom=(position[0], position[1] - maria.radius - 5))
    pygame.draw.rect(screen, (255, 230, 140), label_rect.inflate(6, 3), border_radius=3)
    screen.blit(label, label_rect)


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
    # advance the day/night clock (it handles pause and speed itself)
    for phase, _day in sim_clock.update(dt):
        villagers.set_night(phase == "Night")
        maria_cooldown = 0.0  # let Maria react to the new period
        log_period()
        log("Night falls, villagers head home" if phase == "Night" else "Morning, villagers start their day")

    # everything moves faster at 2x and stops when paused
    sim_dt = 0 if sim_clock.paused else dt * sim_clock.speed
    for message in villagers.update(sim_dt):
        log(message)
    update_agents(sim_dt)

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
    draw_maria()
    if maria_selected or maria_hit_test(pygame.mouse.get_pos()):
        draw_maria_info()
    right_menu.draw(screen)
    bottom_menu.draw(screen)

    pygame.display.flip()  # Refresh on-screen display