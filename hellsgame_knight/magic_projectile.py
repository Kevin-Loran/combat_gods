"""
magic_projectile.py — Projetil Magico do jogador.

Spritesheet: assets/Projetil/Water Effect and Bullet 16x16.png (77x31 px)
3 frames detectados por analise de alpha:
  Frame 0  x=17  w= 8  formacao
  Frame 1  x=31  w=11  em voo
  Frame 2  x=49  w=11  energizado / proximo ao impacto
"""

import pygame
import os
from settings import SCREEN_WIDTH

_PROJ_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "assets", "Projetil"
)

PROJ_SPEED        = 380   # px/s — velocidade horizontal
PROJ_DISPLAY_SIZE = 80    # px — tamanho de exibicao quadrado
PROJ_FRAME_DUR    = 0.09  # s  — duracao de cada frame (ciclo de 0.27s)
PROJ_COOLDOWN     = 5.0   # s  — cooldown entre disparos

# Limites exatos de cada frame (detectados por alpha)
_FRAME_RECTS = [
    pygame.Rect(17, 0,  8, 31),
    pygame.Rect(31, 0, 11, 31),
    pygame.Rect(49, 0, 11, 31),
]

_RAW_FRAMES: list | None = None


def _ensure_frames() -> list:
    """Fatia e escala os 3 frames do projetil (lazy, cached)."""
    global _RAW_FRAMES
    if _RAW_FRAMES is not None:
        return _RAW_FRAMES

    path = os.path.join(_PROJ_DIR, "Water Effect and Bullet 16x16.png")
    try:
        sheet = pygame.image.load(path).convert_alpha()
        w, h  = sheet.get_size()
        print(
            f"[magic_proj] {w}x{h} px — {len(_FRAME_RECTS)} frames "
            f"escalados para {PROJ_DISPLAY_SIZE}x{PROJ_DISPLAY_SIZE}",
            flush=True,
        )
        raw = [
            pygame.transform.scale(
                sheet.subsurface(r),
                (PROJ_DISPLAY_SIZE, PROJ_DISPLAY_SIZE),
            )
            for r in _FRAME_RECTS
        ]
    except Exception as e:
        print(f"[magic_proj] ERRO ao carregar spritesheet: {e}", flush=True)
        fb = pygame.Surface((PROJ_DISPLAY_SIZE, PROJ_DISPLAY_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(
            fb, (80, 180, 255, 220),
            (PROJ_DISPLAY_SIZE // 2, PROJ_DISPLAY_SIZE // 2),
            PROJ_DISPLAY_SIZE // 2,
        )
        raw = [fb, fb, fb]

    _RAW_FRAMES = raw
    return _RAW_FRAMES


def load_projectile_icon(size: tuple) -> pygame.Surface:
    """Carrega e escala o icone do projetil para a HUD."""
    path = os.path.join(_PROJ_DIR, "icone_projetil.png")
    try:
        surf = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(surf, size)
    except Exception as e:
        print(f"[magic_proj] ERRO ao carregar icone: {e}", flush=True)
        fb = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.circle(fb, (80, 180, 255), (size[0] // 2, size[1] // 2), min(size) // 2)
        return fb


class MagicProjectile:
    """
    Um unico projetil animado com 3 frames.

    Uso em game.py:
        proj = MagicProjectile(spawn_x, spawn_y, player.facing)
        proj.update(dt)
        if proj.hitbox.colliderect(boss.hitbox):
            boss.take_damage(1)
            proj.done = True
        if proj.done:
            # descartar
    """

    def __init__(self, x: int, y: int, direction: int):
        """
        direction: 1 (direita) | -1 (esquerda) — mesmo valor de player.facing
        """
        self.x    = float(x)
        self.y    = float(y)
        self.dir  = direction
        self.done = False
        self._timer = 0.0

        raw = _ensure_frames()
        # Espelha horizontalmente se for para a esquerda
        if direction == -1:
            self._frames = [pygame.transform.flip(f, True, False) for f in raw]
        else:
            self._frames = list(raw)

        self._n = len(self._frames)

        # Hitbox de colisao menor que o sprite (colisao mais justa)
        self.hitbox = pygame.Rect(0, 0, 20, 20)
        self._sync_hitbox()

    def update(self, dt: float) -> None:
        self.x      += self.dir * PROJ_SPEED * dt
        self._timer += dt
        self._sync_hitbox()

        # Descarta ao sair da tela
        if self.x < -80 or self.x > SCREEN_WIDTH + 80:
            self.done = True

    def draw(self, screen: pygame.Surface) -> None:
        if self.done:
            return
        idx   = int(self._timer / PROJ_FRAME_DUR) % self._n
        frame = self._frames[idx]
        rect  = frame.get_rect()
        rect.center = (int(self.x), int(self.y))
        screen.blit(frame, rect)

    def _sync_hitbox(self) -> None:
        self.hitbox.center = (int(self.x), int(self.y))
