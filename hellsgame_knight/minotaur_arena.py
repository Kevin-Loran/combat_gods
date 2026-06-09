"""
minotaur_arena.py — Arena original do Minotauro (demon woods / floresta infernal).

Arena do Minotauro — demon woods / floresta infernal.

Layout original:
  Plataforma única (chão completo) — sem plataformas flutuantes.
  Player spawn : (120, 439)
  Boss  spawn  : (800, 439)

Background: parallax de 4 camadas (demon woods).
  Fallback procedural se as imagens não forem encontradas.
"""

import pygame
import os
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, ASSETS_DIR

# ── Constantes (idênticas ao game.py original) ─────────────────────────────────
PLATFORM_IMG_H = 111
TOP_INSET      = 10
SOLID_TOP      = SCREEN_HEIGHT - PLATFORM_IMG_H + TOP_INSET   # 439

PLAYER_SPAWN = (120, SOLID_TOP)
BOSS_SPAWN   = (800, SOLID_TOP)

# Mesmos arquivos e fatores do PARALLAX_LAYERS original de game.py
_PARALLAX_FILES = [
    ("parallax-demon-woods-bg.png",          0.1),
    ("parallax-demon-woods-far-trees.png",   0.3),
    ("parallax-demon-woods-mid-trees.png",   0.6),
    ("parallax-demon-woods-close-trees.png", 0.9),
]


# ── Layer de parallax (lógica idêntica à ParallaxLayer do game.py original) ─────

class _ParallaxLayer:
    def __init__(self, image: pygame.Surface, factor: float):
        self.factor   = factor
        self.offset_x = 0.0
        orig_w, orig_h = image.get_size()
        scale          = SCREEN_HEIGHT / orig_h
        new_w          = int(orig_w * scale)
        self.image     = pygame.transform.scale(image, (new_w, SCREEN_HEIGHT))
        self.img_w     = new_w

    def update(self, player_vel_x: float, dt: float):
        self.offset_x += player_vel_x * self.factor * dt
        self.offset_x %= self.img_w

    def draw(self, surface: pygame.Surface):
        x = -int(self.offset_x)
        while x < SCREEN_WIDTH:
            surface.blit(self.image, (x, 0))
            x += self.img_w


def _make_fallback_bg() -> pygame.Surface:
    """Fundo procedural escuro (mesmo que _make_fallback_background do game.py)."""
    surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    for y in range(SCREEN_HEIGHT):
        t = y / SCREEN_HEIGHT
        r = int(15 + t * 55)
        g = int(3  + t * 4)
        pygame.draw.line(surf, (r, g, 3), (0, y), (SCREEN_WIDTH, y))
    return surf


# ── Arena ─────────────────────────────────────────────────────────────────────

class MinotaurArena:
    """
    Arena original do Minotauro — demon woods.

    Interface esperada por game.py:
        .parallax_layers — list[_ParallaxLayer]  (.update / .draw)
        .fallback_bg     — Surface | None         (usado se parallax vazio)
        .platforms       — pygame.sprite.Group
        .player_spawn    — (x, y)
        .boss_spawn      — (x, y)
        .floor_y         — int
    """

    def __init__(self):
        self.parallax_layers = self._load_parallax()

        # fallback_bg usado apenas se imagens não forem encontradas
        self.fallback_bg = (
            None if self.parallax_layers
            else _make_fallback_bg()
        )

        self.platforms    = self._build_platforms()
        self.player_spawn = PLAYER_SPAWN
        self.boss_spawn   = BOSS_SPAWN
        self.floor_y      = SOLID_TOP

        print(
            f"[minotaur_arena] Arena criada — "
            f"player_spawn={PLAYER_SPAWN}  boss_spawn={BOSS_SPAWN}  "
            f"parallax_layers={len(self.parallax_layers)}",
            flush=True,
        )

    def _load_parallax(self) -> list:
        layers = []
        for fname, factor in _PARALLAX_FILES:
            path = os.path.join(ASSETS_DIR, fname)
            if not os.path.exists(path):
                continue
            try:
                img = pygame.image.load(path).convert_alpha()
                layers.append(_ParallaxLayer(img, factor))
            except pygame.error as e:
                print(f"[minotaur_arena] Erro ao carregar {fname}: {e}", flush=True)
        return layers

    def _build_platforms(self) -> pygame.sprite.Group:
        from platforms import Platform

        group = pygame.sprite.Group()

        # Chão principal — exatamente como no PLATFORM_DATA original
        group.add(Platform(0, SCREEN_HEIGHT - PLATFORM_IMG_H, 1))

        # Paredes invisíveis — idênticas ao _build_level original
        for wx in (-TILE_SIZE, SCREEN_WIDTH):
            wall            = pygame.sprite.Sprite()
            wall.image      = pygame.Surface((TILE_SIZE, SCREEN_HEIGHT), pygame.SRCALPHA)
            wall.image.fill((0, 0, 0, 0))
            wall.rect       = pygame.Rect(wx, 0, TILE_SIZE, SCREEN_HEIGHT)
            wall.solid_rect = pygame.Rect(wx, 0, TILE_SIZE, SCREEN_HEIGHT)
            group.add(wall)

        return group
