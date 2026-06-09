"""
night_arena.py — Night Town Arena

Assets (pasta assets/arena_noite/):
    chao_arena_noite.png              → tiles de chão  (313 × 295)
    plataforma_arena_noite.png        → plataformas flutuantes (295 × 254)
    night-town-background-previewx2.png → background (1024 × 448)

Layout (960 × 540):
┌──────────────────────────────────────────────────────────────┐  y=0
│                    céu noturno + estrelas + lua               │
│                                                               │
│   [PLAT L]                               [PLAT R]            │  y=290
│   x=100..360                             x=640..900          │
│                                                               │
├──────────────────────────────────────────────────────────────┤  y=440
│              chão contínuo (tiles 160 × 150 px)              │
└──────────────────────────────────────────────────────────────┘  y=540

Parallax (back → front):
    [0] Céu + estrelas     factor=0.000   estático
    [1] Lua + halo         factor=0.000   estático
    [2] City background    factor=0.008   muito lento
    [3] Névoa de horizonte factor=0.000   estática
    [4] Névoa de chão      factor=0.000   estática
    [5] Sombra do topo     factor=0.000   estática
"""

import pygame
import os
import math
import random
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE

# ── Assets ───────────────────────────────────────────────────────────────────

_NIGHT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "assets", "arena_noite")

def _night_asset(*parts: str) -> str:
    return os.path.join(_NIGHT_DIR, *parts)


# ═══════════════════════════════════════════════════════════════════════════════
# LAYOUT — NÃO ALTERE (gameplay depende desses valores)
# ═══════════════════════════════════════════════════════════════════════════════

FLOOR_SOLID_Y = 440     # y: colisão do chão principal

FLOAT_SOLID_Y = 290     # y: colisão das plataformas flutuantes
FLOAT_W       = 260     # largura das plataformas (px)
FLOAT_L_X     = 100     # x: borda esquerda da plataforma esquerda
FLOAT_R_X     = 640     # x: borda esquerda da plataforma direita

PLAYER_SPAWN = (240, FLOOR_SOLID_Y)
BOSS_SPAWN   = (720, FLOOR_SOLID_Y)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES DE TILE
# ═══════════════════════════════════════════════════════════════════════════════

_FLOOR_H            = SCREEN_HEIGHT - FLOOR_SOLID_Y      # 100 px visíveis
_FLOOR_TILE_W       = 160                                 # 960 ÷ 160 = 6 exato
_FLOOR_TILE_H       = int(295 / 313 * _FLOOR_TILE_W)     # 150 px (proporção original)
_FLOOR_N_TILES      = SCREEN_WIDTH // _FLOOR_TILE_W       # 6 tiles = 960 px
_FLOOR_VISUAL_RAISE = 8   # px que o visual do chão sobe acima da linha de colisão

_PLAT_FULL_H    = int(254 / 295 * FLOAT_W)        # 189 px (proporção original)
_PLAT_VISIBLE_H = 72                               # px do topo da plataforma exibidos
_PLAT_INSET     = 14                               # px decorativos acima da colisão
_PLAT_SOLID_H   = 20                               # altura da zona de colisão (one_way)


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE DE SPRITES
# ═══════════════════════════════════════════════════════════════════════════════

_sprite_cache:  dict = {}
_sprites_tried: set  = set()


def _load(filename: str) -> pygame.Surface | None:
    if filename in _sprites_tried:
        return _sprite_cache.get(filename)
    _sprites_tried.add(filename)
    path = _night_asset(filename)
    if not os.path.exists(path):
        return None
    try:
        surf = pygame.image.load(path).convert_alpha()
        _sprite_cache[filename] = surf
        print(f"[night_arena] {filename} {surf.get_size()}", flush=True)
        return surf
    except pygame.error as e:
        print(f"[night_arena] erro {filename}: {e}", flush=True)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# PALETA NOTURNA
# ═══════════════════════════════════════════════════════════════════════════════

_SKY_TOP  = (  6,   4,  18)   # meia-noite profunda
_SKY_MID  = ( 16,  12,  42)   # índigo escuro
_SKY_HOR  = ( 28,  20,  62)   # violeta do horizonte (reflexo da cidade)
_FOG      = ( 70,  52, 110)   # névoa roxa
_STONE_L  = ( 68,  58,  92)   # pedra clara (tom noturno)
_STONE_M  = ( 48,  40,  68)   # pedra média
_STONE_D  = ( 32,  26,  48)   # pedra escura / sombra
_PLAT_TOP = (130, 100, 200)   # borda superior iluminada da plataforma
_PLAT_MID = ( 80,  62, 130)   # corpo da plataforma
_PLAT_BOT = ( 48,  36,  82)   # fundo da plataforma


# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACKS PROCEDURAIS
# ═══════════════════════════════════════════════════════════════════════════════

def _proc_floor_tile(w: int, h: int) -> pygame.Surface:
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surf, _STONE_M,  (0,  0, w, h))
    pygame.draw.rect(surf, _STONE_L,  (0,  0, w, max(1, h * 3 // 10)))
    pygame.draw.rect(surf, _STONE_D,  (0, h - max(1, h // 5), w, max(1, h // 5)))
    pygame.draw.rect(surf, (120, 100, 180), (0, 0, w, 2))  # brilho no topo
    for sx in range(0, w, 32):
        pygame.draw.line(surf, _STONE_D, (sx, 0), (sx, h), 1)
    return surf


def _proc_platform_tile(w: int, h: int) -> pygame.Surface:
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surf, _PLAT_MID, (0, 0, w, h))
    pygame.draw.rect(surf, _PLAT_TOP, (0, 0, w, 4))
    pygame.draw.rect(surf, _PLAT_BOT, (0, h - max(1, h // 4), w, max(1, h // 4)))
    glow = pygame.Surface((w, 6), pygame.SRCALPHA)
    glow.fill((160, 130, 255, 55))
    surf.blit(glow, (0, 0))
    return surf


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTRUTORES DE SUPERFÍCIE — BACKGROUND
# ═══════════════════════════════════════════════════════════════════════════════

def _build_sky() -> pygame.Surface:
    """Gradiente de céu noturno + campo de estrelas."""
    surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    for y in range(SCREEN_HEIGHT):
        t = y / SCREEN_HEIGHT
        if t < 0.55:
            t2 = t / 0.55
            r = int(_SKY_TOP[0] + t2 * (_SKY_MID[0] - _SKY_TOP[0]))
            g = int(_SKY_TOP[1] + t2 * (_SKY_MID[1] - _SKY_TOP[1]))
            b = int(_SKY_TOP[2] + t2 * (_SKY_MID[2] - _SKY_TOP[2]))
        else:
            t2 = (t - 0.55) / 0.45
            r = int(_SKY_MID[0] + t2 * (_SKY_HOR[0] - _SKY_MID[0]))
            g = int(_SKY_MID[1] + t2 * (_SKY_HOR[1] - _SKY_MID[1]))
            b = int(_SKY_MID[2] + t2 * (_SKY_HOR[2] - _SKY_MID[2]))
        pygame.draw.line(surf, (r, g, b), (0, y), (SCREEN_WIDTH, y))

    rng = random.Random(77)
    for _ in range(72):
        sx     = rng.randint(0, SCREEN_WIDTH - 1)
        sy     = rng.randint(0, int(SCREEN_HEIGHT * 0.52))
        bright = rng.randint(110, 220)
        radius = rng.choice([1, 1, 1, 1, 2])
        tint_b = min(255, bright + 35)
        pygame.draw.circle(surf, (bright - 20, bright - 25, tint_b), (sx, sy), radius)
    return surf


def _build_moon() -> pygame.Surface:
    """Lua + halo difuso — camada estática sobre o céu."""
    surf  = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    mx, my, mr = 820, 72, 28

    for gr in range(22, 0, -1):
        a = int(14 * (1.0 - gr / 22))
        pygame.draw.circle(surf, (200, 190, 255, a), (mx, my), mr + gr * 3)

    pygame.draw.circle(surf, (230, 222, 255), (mx, my), mr)
    pygame.draw.circle(surf, (245, 240, 255), (mx - 5, my - 5), mr - 8)
    return surf


def _build_city() -> pygame.Surface:
    """
    Background da cidade noturna.
    Usa night-town-background-previewx2.png (1024×448) escalado para preencher
    a tela verticalmente; aplica tint noturno leve para integrar ao céu.
    Fallback: silhueta de prédios procedural.
    """
    raw = _load("night-town-background-previewx2.png")
    if raw is not None:
        rw, rh   = raw.get_size()
        target_h = SCREEN_HEIGHT
        target_w = max(SCREEN_WIDTH, int(rw * target_h / rh))
        surf     = pygame.transform.scale(raw, (target_w, target_h))
        tint     = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
        tint.fill((8, 4, 22, 38))
        surf.blit(tint, (0, 0))
        return surf

    # Fallback procedural: silhueta de prédios
    surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    rng  = random.Random(31)
    x    = 0
    base = SCREEN_HEIGHT - 50
    while x < SCREEN_WIDTH + 100:
        bw  = rng.randint(38, 88)
        bh  = rng.randint(55, 195)
        by  = base - bh
        col = (rng.randint(16, 30), rng.randint(12, 24), rng.randint(28, 50), 225)
        pygame.draw.rect(surf, col, (x, by, bw, bh + 50))
        for wy in range(by + 8, by + bh - 8, 14):
            for wx in range(x + 5, x + bw - 5, 11):
                if rng.random() > 0.45:
                    wc = (215, 195, 138, rng.randint(70, 200))
                    pygame.draw.rect(surf, wc, (wx, wy, 5, 7))
        x += bw + rng.randint(0, 6)
    return surf


def _build_horizon_fog() -> pygame.Surface:
    """Névoa difusa na linha do horizonte da cidade."""
    fog_h = 90
    surf  = pygame.Surface((SCREEN_WIDTH, fog_h), pygame.SRCALPHA)
    for y in range(fog_h):
        t = abs(y - fog_h // 2) / (fog_h // 2)
        a = int(28 * (1.0 - t * t))
        pygame.draw.line(surf, (*_FOG, a), (0, y), (SCREEN_WIDTH - 1, y))
    return surf


def _build_ground_fog() -> pygame.Surface:
    """Névoa roxa densa rente ao chão — reforça o peso da arena."""
    fog_h = 58
    surf  = pygame.Surface((SCREEN_WIDTH, fog_h), pygame.SRCALPHA)
    for y in range(fog_h):
        t = 1.0 - y / fog_h
        a = int(52 * t * t)
        pygame.draw.line(surf, (90, 68, 140, a), (0, y), (SCREEN_WIDTH - 1, y))
    return surf


def _build_top_shadow() -> pygame.Surface:
    """Sombra no topo da tela — enquadramento cinematográfico."""
    h    = 60
    surf = pygame.Surface((SCREEN_WIDTH, h), pygame.SRCALPHA)
    for y in range(h):
        a = int(80 * (1.0 - y / h))
        pygame.draw.line(surf, (2, 1, 8, a), (0, y), (SCREEN_WIDTH - 1, y))
    return surf


# ═══════════════════════════════════════════════════════════════════════════════
# CAMADA DE PARALLAX
# ═══════════════════════════════════════════════════════════════════════════════

class _BgLayer:
    __slots__ = ("factor", "offset_x", "_surf", "_w", "_y")

    def __init__(self, surf: pygame.Surface, factor: float, y: int = 0):
        self.factor   = factor
        self.offset_x = 0.0
        self._surf    = surf
        self._w       = surf.get_width()
        self._y       = y

    def update(self, vel_x: float, dt: float):
        self.offset_x = (self.offset_x + vel_x * self.factor * dt) % self._w

    def draw(self, screen: pygame.Surface):
        x = -int(self.offset_x)
        while x < SCREEN_WIDTH:
            screen.blit(self._surf, (x, self._y))
            x += self._w


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTRUTORES DE SUPERFÍCIE — TILES DE GAMEPLAY
# ═══════════════════════════════════════════════════════════════════════════════

def _build_floor_surf() -> pygame.Surface:
    """
    Chão contínuo — 960 × 150 px, 6 tiles de 160 px cada.

    Técnica: mirror tiling (normal | espelho | normal | espelho…)
    A borda direita do tile original torna-se a borda esquerda do tile
    espelhado — as juntas são invisíveis e o padrão nunca repete de forma
    óbvia. 960 ÷ 160 = 6 exato → zero overflow, zero corte.
    """
    raw = _load("chao_arena_noite.png")
    if raw is not None:
        tile = pygame.transform.scale(raw, (_FLOOR_TILE_W, _FLOOR_TILE_H))
    else:
        tile = _proc_floor_tile(_FLOOR_TILE_W, _FLOOR_TILE_H)

    tile_mirror = pygame.transform.flip(tile, True, False)
    # Superfície OPACA: pixels transparentes do tile mostram a cor base de pedra
    # (sem SRCALPHA → nenhum "buraco" ou borda transparente visível)
    surf = pygame.Surface((SCREEN_WIDTH, _FLOOR_TILE_H))
    surf.fill(_STONE_M)

    for i in range(_FLOOR_N_TILES):
        t = tile_mirror if (i % 2) else tile
        surf.blit(t, (i * _FLOOR_TILE_W, 0))

    return surf


def _build_plat_surf() -> pygame.Surface:
    """
    Superfície da plataforma: imagem escalada para FLOAT_W de largura,
    recortada nos _PLAT_VISIBLE_H px superiores.

    Fade nos últimos 14 px inferiores do crop (BLEND_RGBA_MULT):
        alpha vai de 255 (topo do fade) → 0 (borda inferior)
    Elimina o corte rígido visível sem alterar a parte funcional do sprite.
    """
    raw = _load("plataforma_arena_noite.png")
    if raw is not None:
        scaled = pygame.transform.scale(raw, (FLOAT_W, _PLAT_FULL_H))
        crop_h = min(_PLAT_VISIBLE_H, _PLAT_FULL_H)
        surf   = pygame.Surface((FLOAT_W, crop_h), pygame.SRCALPHA)
        surf.blit(scaled, (0, 0))
    else:
        surf = _proc_platform_tile(FLOAT_W, _PLAT_VISIBLE_H)
        crop_h = _PLAT_VISIBLE_H

    # Fade suave na borda inferior — elimina corte rígido
    fade_h    = min(14, crop_h // 4)
    fade_surf = pygame.Surface((FLOAT_W, fade_h), pygame.SRCALPHA)
    for fy in range(fade_h):
        # a=255 no topo do fade (preserva), a=0 na borda (transparente)
        a = 255 - int(255 * fy / fade_h)
        pygame.draw.line(fade_surf, (255, 255, 255, a),
                         (0, fy), (FLOAT_W - 1, fy))
    surf.blit(fade_surf, (0, crop_h - fade_h),
              special_flags=pygame.BLEND_RGBA_MULT)

    return surf


# ═══════════════════════════════════════════════════════════════════════════════
# SPRITES DE GAMEPLAY
# ═══════════════════════════════════════════════════════════════════════════════

_FLOOR_SURF_CACHE: pygame.Surface | None = None
_PLAT_SURF_CACHE:  pygame.Surface | None = None


class NightFloorSprite(pygame.sprite.Sprite):
    """
    Sprite único do chão principal — cobre a tela inteira de x=0 a x=960.
    Colisão sólida em todas as direções (one_way=False).
    """
    one_way = False

    def __init__(self):
        super().__init__()
        global _FLOOR_SURF_CACHE
        if _FLOOR_SURF_CACHE is None:
            _FLOOR_SURF_CACHE = _build_floor_surf()
        surf            = _FLOOR_SURF_CACHE
        self.image      = surf
        # rect: sobe _FLOOR_VISUAL_RAISE px acima da colisão para que a superfície
        # visual da pedra se alinhe com os pés do personagem (y=FLOOR_SOLID_Y)
        self.rect       = pygame.Rect(0, FLOOR_SOLID_Y - _FLOOR_VISUAL_RAISE,
                                      SCREEN_WIDTH, _FLOOR_TILE_H)
        # solid_rect: linha de colisão real, inalterada em y=FLOOR_SOLID_Y
        self.solid_rect = pygame.Rect(0, FLOOR_SOLID_Y, SCREEN_WIDTH, _FLOOR_H)


class NightPlatform(pygame.sprite.Sprite):
    """
    Plataforma flutuante — one_way=True (pousável por cima, atravessável por baixo).

    Geometria:
        image_y     = FLOAT_SOLID_Y - _PLAT_INSET   (início visual da plataforma)
        solid_rect  = y=FLOAT_SOLID_Y, h=20 px       (linha de colisão)
    """
    one_way = True

    def __init__(self, x: int):
        super().__init__()
        global _PLAT_SURF_CACHE
        if _PLAT_SURF_CACHE is None:
            _PLAT_SURF_CACHE = _build_plat_surf()
        img    = _PLAT_SURF_CACHE
        img_h  = img.get_height()
        img_y  = FLOAT_SOLID_Y - _PLAT_INSET
        self.image      = img
        self.rect       = pygame.Rect(x, img_y, FLOAT_W, img_h)
        # _PLAT_SOLID_H = 20 px (apenas a superfície de pouso) — reduz chance de
        # o jogador ser bloqueado ao saltar de baixo para cima na plataforma
        self.solid_rect = pygame.Rect(x, FLOAT_SOLID_Y, FLOAT_W, _PLAT_SOLID_H)


# ═══════════════════════════════════════════════════════════════════════════════
# CACHES DE BACKGROUND
# ═══════════════════════════════════════════════════════════════════════════════

_SKY_CACHE    = None
_MOON_CACHE   = None
_CITY_CACHE   = None
_HFOG_CACHE   = None
_GFOG_CACHE   = None
_TOP_CACHE    = None


# ═══════════════════════════════════════════════════════════════════════════════
# ARENA PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class NightArena:
    """
    Arena Noturna — Night Town.

    Interface compatível com game.py:
        .parallax_layers — list  (cada item tem .update(vel_x, dt) e .draw(screen))
        .fallback_bg     — None
        .platforms       — pygame.sprite.Group
        .player_spawn    — (x, y)
        .boss_spawn      — (x, y)
        .floor_y         — int
    """

    def __init__(self):
        global _SKY_CACHE, _MOON_CACHE, _CITY_CACHE
        global _HFOG_CACHE, _GFOG_CACHE, _TOP_CACHE

        if _SKY_CACHE  is None: _SKY_CACHE  = _build_sky()
        if _MOON_CACHE is None: _MOON_CACHE = _build_moon()
        if _CITY_CACHE is None: _CITY_CACHE = _build_city()
        if _HFOG_CACHE is None: _HFOG_CACHE = _build_horizon_fog()
        if _GFOG_CACHE is None: _GFOG_CACHE = _build_ground_fog()
        if _TOP_CACHE  is None: _TOP_CACHE  = _build_top_shadow()

        hfog_y = FLOOR_SOLID_Y - 160 - _HFOG_CACHE.get_height() // 2
        gfog_y = FLOOR_SOLID_Y - _GFOG_CACHE.get_height()

        self.parallax_layers = [
            _BgLayer(_SKY_CACHE,  0.000),              # céu + estrelas
            _BgLayer(_MOON_CACHE, 0.000),              # lua
            _BgLayer(_CITY_CACHE, 0.008),              # cidade ao fundo
            _BgLayer(_HFOG_CACHE, 0.000, hfog_y),     # névoa horizonte
            _BgLayer(_GFOG_CACHE, 0.000, gfog_y),     # névoa de chão
            _BgLayer(_TOP_CACHE,  0.000),              # sombra do topo
        ]

        self.fallback_bg  = None
        self.platforms    = self._build_platforms()
        self.player_spawn = PLAYER_SPAWN
        self.boss_spawn   = BOSS_SPAWN
        self.floor_y      = FLOOR_SOLID_Y

        loaded  = [k for k, v in _sprite_cache.items() if v is not None]
        missing = [k for k in _sprites_tried if _sprite_cache.get(k) is None]
        print(
            f"[night_arena] Arena criada — "
            f"player={PLAYER_SPAWN}  boss={BOSS_SPAWN}  "
            f"platforms={len(self.platforms)}  "
            f"sprites={loaded}  fallback={missing}",
            flush=True,
        )

    def _build_platforms(self) -> pygame.sprite.Group:
        """
        Ordem de inserção = ordem de renderização (pygame.sprite.Group).

        0. Chão principal  (NightFloorSprite)   — one_way=False
        1. Plataformas     (NightPlatform ×2)   — one_way=True
        2. Paredes laterais invisíveis
        """
        group = pygame.sprite.Group()

        # 0. Chão
        group.add(NightFloorSprite())

        # 1. Plataformas flutuantes
        group.add(NightPlatform(FLOAT_L_X))
        group.add(NightPlatform(FLOAT_R_X))

        # 2. Paredes laterais invisíveis
        wall_w = TILE_SIZE
        for wx in (-wall_w, SCREEN_WIDTH):
            wall            = pygame.sprite.Sprite()
            wall.image      = pygame.Surface((wall_w, SCREEN_HEIGHT), pygame.SRCALPHA)
            wall.image.fill((0, 0, 0, 0))
            wall.rect       = pygame.Rect(wx, 0, wall_w, SCREEN_HEIGHT)
            wall.solid_rect = pygame.Rect(wx, 0, wall_w, SCREEN_HEIGHT)
            wall.one_way    = False
            group.add(wall)

        return group
