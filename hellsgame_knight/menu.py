"""
menu.py — Pause and Game Over menus.
Visual: botões pixel-art dourados, consistente com o HUD do jogo.
Navegação: ↑↓ (ou W/S) + Enter/Space para confirmar. P/ESC fecha pausa.
"""
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE

_BTN_W   = 210
_BTN_H   = 36
_BTN_GAP = 10


# ─────────────────────────────────────────────────────────────────────────────
# BUTTON
# ─────────────────────────────────────────────────────────────────────────────

class _Button:
    """Botão pixel-art estilo metálico dourado."""

    def __init__(self, label: str):
        self.label = label
        self._font = pygame.font.SysFont("monospace", 16, bold=True)
        self._norm = self._bake(False)
        self._sel  = self._bake(True)
        self.rect  = pygame.Rect(0, 0, _BTN_W, _BTN_H)

    def _bake(self, selected: bool) -> pygame.Surface:
        surf = pygame.Surface((_BTN_W, _BTN_H), pygame.SRCALPHA)

        outer = (48, 32,  0) if selected else (22, 14,  0)
        inner = (245, 190, 38) if selected else (148, 105, 18)
        fill  = (115,  75,  5) if selected else (50,   33,  2)
        tc    = (255, 242, 148) if selected else (198, 173, 96)

        pygame.draw.rect(surf, outer, (0, 0, _BTN_W, _BTN_H), border_radius=5)
        pygame.draw.rect(surf, inner, (1, 1, _BTN_W - 2, _BTN_H - 2), border_radius=4)
        pygame.draw.rect(surf, fill,  (3, 3, _BTN_W - 6, _BTN_H - 6), border_radius=3)

        shine = pygame.Surface((_BTN_W - 12, 3), pygame.SRCALPHA)
        shine.fill((255, 252, 205, 58 if selected else 20))
        surf.blit(shine, (6, 5))

        lbl = self._font.render(self.label, True, tc)
        surf.blit(lbl, lbl.get_rect(center=(_BTN_W // 2, _BTN_H // 2)))
        return surf

    def draw(self, screen: pygame.Surface, cx: int, cy: int, selected: bool):
        self.rect.center = (cx, cy)
        screen.blit(self._sel if selected else self._norm, self.rect)
        if selected:
            # Triângulo indicador à esquerda (►)
            tx = self.rect.left - 14
            pts = [(tx, cy), (tx - 9, cy - 6), (tx - 9, cy + 6)]
            pygame.draw.polygon(screen, (255, 215, 48), pts)

    def hit(self, pos) -> bool:
        return self.rect.collidepoint(pos)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _overlay(screen: pygame.Surface, alpha: int = 165):
    ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, alpha))
    screen.blit(ov, (0, 0))


def _panel(screen: pygame.Surface, pw: int, ph: int) -> tuple[int, int]:
    px = SCREEN_WIDTH  // 2 - pw // 2
    py = SCREEN_HEIGHT // 2 - ph // 2
    surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
    surf.fill((8, 5, 1, 238))
    pygame.draw.rect(surf, (152, 108, 20), (0, 0, pw, ph), 2, border_radius=8)
    pygame.draw.rect(surf, (68,  46,  4),  (3, 3, pw - 6, ph - 6), 1, border_radius=6)
    screen.blit(surf, (px, py))
    return px, py


# ─────────────────────────────────────────────────────────────────────────────
# PAUSE MENU
# ─────────────────────────────────────────────────────────────────────────────

class PauseMenu:
    """Menu de pausa. Tecla P ou ESC para abrir/fechar."""

    _LABELS = ("RESUME", "RESTART", "EXIT")

    def __init__(self):
        self._sel     = 0
        self._buttons = [_Button(l) for l in self._LABELS]
        self._font_t  = pygame.font.SysFont("monospace", 40, bold=True)
        self._font_s  = pygame.font.SysFont("monospace", 12)

    def reset(self):
        self._sel = 0

    def handle(self, event: pygame.event.Event) -> str | None:
        """Retorna o label em minúsculas ao confirmar, None caso contrário."""
        if event.type != pygame.KEYDOWN:
            return None
        k = event.key
        if k in (pygame.K_UP, pygame.K_w):
            self._sel = (self._sel - 1) % len(self._buttons)
        elif k in (pygame.K_DOWN, pygame.K_s):
            self._sel = (self._sel + 1) % len(self._buttons)
        elif k in (pygame.K_RETURN, pygame.K_SPACE):
            return self._LABELS[self._sel].lower()
        return None

    def draw(self, screen: pygame.Surface):
        _overlay(screen, 158)

        pw, ph = 268, 252
        px, py = _panel(screen, pw, ph)
        cx = SCREEN_WIDTH // 2

        title = self._font_t.render("PAUSED", True, (240, 200, 52))
        screen.blit(title, title.get_rect(centerx=cx, top=py + 20))

        pygame.draw.line(screen, (118, 83, 14),
                         (px + 18, py + 72), (px + pw - 18, py + 72))

        btn_y0 = py + 112
        for i, btn in enumerate(self._buttons):
            btn.draw(screen, cx, btn_y0 + i * (_BTN_H + _BTN_GAP), i == self._sel)


# ─────────────────────────────────────────────────────────────────────────────
# GAME OVER MENU
# ─────────────────────────────────────────────────────────────────────────────

class GameOverMenu:
    """Tela de Game Over com fade-in e navegação por teclado."""

    _LABELS = ("RESTART", "EXIT")

    def __init__(self):
        self._sel     = 0
        self._buttons = [_Button(l) for l in self._LABELS]
        self._font_t  = pygame.font.SysFont("monospace", 44, bold=True)
        self._font_s  = pygame.font.SysFont("monospace", 12)
        self._timer   = 0.0

    def reset(self):
        self._sel   = 0
        self._timer = 0.0

    def update(self, dt: float):
        self._timer = min(1.0, self._timer + dt * 1.6)

    def handle(self, event: pygame.event.Event) -> str | None:
        if self._timer < 0.55:
            return None
        if event.type != pygame.KEYDOWN:
            return None
        k = event.key
        if k in (pygame.K_UP, pygame.K_w):
            self._sel = (self._sel - 1) % len(self._buttons)
        elif k in (pygame.K_DOWN, pygame.K_s):
            self._sel = (self._sel + 1) % len(self._buttons)
        elif k in (pygame.K_RETURN, pygame.K_SPACE):
            return self._LABELS[self._sel].lower()
        return None

    def draw(self, screen: pygame.Surface):
        t = self._timer

        # Overlay com fade
        ov_alpha = min(168, int(t * 220))
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, ov_alpha))
        screen.blit(ov, (0, 0))

        if t < 0.18:
            return

        pw, ph = 278, 220
        px, py = _panel(screen, pw, ph)
        cx = SCREEN_WIDTH // 2

        title = self._font_t.render("GAME OVER", True, (218, 32, 32))
        screen.blit(title, title.get_rect(centerx=cx, top=py + 18))

        pygame.draw.line(screen, (118, 18, 18),
                         (px + 18, py + 70), (px + pw - 18, py + 70))

        btn_y0 = py + 112
        for i, btn in enumerate(self._buttons):
            btn.draw(screen, cx, btn_y0 + i * (_BTN_H + _BTN_GAP), i == self._sel)


# ─────────────────────────────────────────────────────────────────────────────
# VICTORY MENU
# ─────────────────────────────────────────────────────────────────────────────

class VictoryMenu:
    """
    Menu pos-vitoria. Retorna acoes:
      'next_battle' | 'retry' | 'menu' | 'quit_game'
    Bosses intermediários mostram "NEXT BATTLE"; o boss final omite esse botão.
    """

    _LABELS_NORMAL  = ("NEXT BATTLE", "RETRY", "RETURN TO MENU", "QUIT")
    _ACTIONS_NORMAL = ("next_battle", "retry", "menu", "quit_game")

    _LABELS_FINAL   = ("RETURN TO MENU", "PLAY AGAIN", "QUIT")
    _ACTIONS_FINAL  = ("menu", "retry", "quit_game")

    def __init__(self):
        self._font_t  = pygame.font.SysFont("monospace", 48, bold=True)
        self._font_s  = pygame.font.SysFont("monospace", 12)
        self._timer   = 0.0
        self._sel     = 0
        self._labels  = self._LABELS_NORMAL
        self._actions = self._ACTIONS_NORMAL
        self._buttons = [_Button(l) for l in self._labels]

    def configure(self, is_final: bool):
        """Troca os botões conforme o boss ser final ou intermediário."""
        self._labels  = self._LABELS_FINAL  if is_final else self._LABELS_NORMAL
        self._actions = self._ACTIONS_FINAL if is_final else self._ACTIONS_NORMAL
        self._buttons = [_Button(l) for l in self._labels]
        self._sel     = 0

    def reset(self):
        self._sel     = 0
        self._timer   = 0.0
        self._labels  = self._LABELS_NORMAL
        self._actions = self._ACTIONS_NORMAL
        self._buttons = [_Button(l) for l in self._labels]

    def update(self, dt: float):
        self._timer = min(1.0, self._timer + dt * 1.4)

    def handle(self, event: pygame.event.Event) -> str | None:
        if self._timer < 0.45:
            return None

        if event.type == pygame.KEYDOWN:
            k = event.key
            if k in (pygame.K_UP, pygame.K_w):
                self._sel = (self._sel - 1) % len(self._buttons)
            elif k in (pygame.K_DOWN, pygame.K_s):
                self._sel = (self._sel + 1) % len(self._buttons)
            elif k in (pygame.K_RETURN, pygame.K_SPACE):
                return self._actions[self._sel]

        elif event.type == pygame.MOUSEMOTION:
            for i, btn in enumerate(self._buttons):
                if btn.hit(event.pos):
                    self._sel = i

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, btn in enumerate(self._buttons):
                if btn.hit(event.pos):
                    return self._actions[i]

        return None

    def draw(self, screen: pygame.Surface):
        t = self._timer

        # Fade-in overlay
        ov_alpha = min(162, int(t * 200))
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, ov_alpha))
        screen.blit(ov, (0, 0))

        if t < 0.18:
            return

        n  = len(self._buttons)
        pw = 300
        ph = 110 + (n - 1) * (_BTN_H + _BTN_GAP) + 44   # adapta à quantidade de botões
        px, py = _panel(screen, pw, ph)
        cx = SCREEN_WIDTH // 2

        # Title: gold drop-shadow + main text
        shadow = self._font_t.render("VITORIA!", True, (90, 60, 0))
        title  = self._font_t.render("VITORIA!", True, (255, 215, 30))
        tr     = title.get_rect(centerx=cx, top=py + 14)
        screen.blit(shadow, (tr.x + 2, tr.y + 2))
        screen.blit(title,  tr)

        pygame.draw.line(screen, (188, 148, 20),
                         (px + 18, py + 76), (px + pw - 18, py + 76))

        btn_y0 = py + 110
        for i, btn in enumerate(self._buttons):
            btn.draw(screen, cx, btn_y0 + i * (_BTN_H + _BTN_GAP), i == self._sel)
