"""
main.py — Entry point with full state machine.
States: "menu" | "battle_select" | "game"
Fade-to-black overlay for all transitions.
"""
import pygame
import sys
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE

_FADE_SPEED = 420   # alpha units per second


class _Fade:
    def __init__(self, screen):
        self._surf  = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._surf.fill((0, 0, 0))
        self._alpha = 255
        self._dir   = 0   # -1 = fading in (clearing), +1 = fading out (darkening)

    def fade_out(self):
        """Start fading to black."""
        self._alpha = 0
        self._dir   = 1

    def fade_in(self):
        """Start revealing from black."""
        self._alpha = 255
        self._dir   = -1

    @property
    def is_black(self) -> bool:
        return self._alpha >= 255

    def update(self, dt) -> bool:
        """Returns True when the current fade movement completes."""
        if self._dir == 0:
            return False
        self._alpha += self._dir * _FADE_SPEED * dt
        if self._dir == -1 and self._alpha <= 0:
            self._alpha = 0
            self._dir   = 0
            return True
        if self._dir == 1 and self._alpha >= 255:
            self._alpha = 255
            self._dir   = 0
            return True
        return False

    def draw(self, screen):
        a = int(self._alpha)
        if a > 0:
            self._surf.set_alpha(a)
            screen.blit(self._surf, (0, 0))


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    from main_menu import MainMenuState, BattleSelectState
    from game import Game

    menu   = MainMenuState()
    select = BattleSelectState()
    game   = None

    state         = "menu"
    next_state    = None
    pending_arena = "minotaur"
    fade          = _Fade(screen)
    fade.fade_in()       # open with fade-in from black

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        # ── Events ───────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if next_state is not None:  # mid-transition: ignore input
                continue

            if state == "menu":
                action = menu.handle(event)
                if action == "play":
                    next_state = "game"
                    fade.fade_out()
                elif action == "select_battle":
                    next_state = "battle_select"
                    fade.fade_out()
                elif action == "quit":
                    pygame.quit()
                    sys.exit()

            elif state == "battle_select":
                action = select.handle(event)
                if action == "play":
                    pending_arena = "minotaur"
                    next_state    = "game"
                    fade.fade_out()
                elif action == "play_night":
                    pending_arena = "night"
                    next_state    = "game"
                    fade.fade_out()
                elif action == "play_sombrio":
                    pending_arena = "sombrio"
                    next_state    = "game"
                    fade.fade_out()
                elif action == "back":
                    next_state = "menu"
                    fade.fade_out()

            elif state == "game" and game is not None:
                result = game.handle_event(event)
                if result == "quit":
                    next_state = "menu"
                    fade.fade_out()
                elif result == "exit_game":
                    pygame.quit()
                    sys.exit()

        # ── Update ───────────────────────────────────────────────────────────
        keys = pygame.key.get_pressed()

        if state == "menu":
            menu.update(dt)
        elif state == "battle_select":
            select.update(dt)
        elif state == "game" and game is not None:
            game.update(keys, dt, fps=clock.get_fps())

        # Fade transition: when screen goes fully black, switch state
        if fade.update(dt) and fade.is_black and next_state is not None:
            state      = next_state
            next_state = None
            if state == "menu":
                menu.reset()
            elif state == "battle_select":
                select.reset()
            elif state == "game":
                game = Game(screen, arena_type=pending_arena)
            fade.fade_in()

        # ── Draw ─────────────────────────────────────────────────────────────
        if state == "menu":
            menu.draw(screen)
        elif state == "battle_select":
            select.draw(screen)
        elif state == "game" and game is not None:
            game.draw()
        else:
            screen.fill((0, 0, 0))

        fade.draw(screen)
        pygame.display.flip()


if __name__ == "__main__":
    main()
