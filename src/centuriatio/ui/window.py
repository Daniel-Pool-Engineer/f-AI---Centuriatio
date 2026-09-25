import pygame

from centuriatio.ui.menu_bars import BottomMenuBar, RightMenuBar

from centuriatio.village.map import create_test_map
from centuriatio.village.renderer import VillageMapRenderer

pygame.init()

village_map = create_test_map()
renderer = VillageMapRenderer()

screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
pygame.display.set_caption("Centuriatio")

clock = pygame.time.Clock()
bottom_menu = BottomMenuBar()
right_menu = RightMenuBar()
is_panning = False
last_mouse_position: tuple[int, int] | None = None
MIN_ZOOM = 0.4
MAX_ZOOM = 1.0
ZOOM_STEP = 1.1


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


resize_menus()
center_camera()

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
    # ...

    #screen.fill("white")  # Fill the display with a solid color


    # Render the graphics here.
    renderer.draw(
        screen,
        village_map,
        show_grid=True,
        show_labels=True,
    )
    right_menu.draw(screen)
    bottom_menu.draw(screen)

    pygame.display.flip()  # Refresh on-screen display
    clock.tick(60)         # wait until next frame (at 60 FPS)