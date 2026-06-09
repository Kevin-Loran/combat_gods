"""
sombrio_arena.py — Sombrio Arena (Bringer of Death / Morthak)  v7

Estrutura mínima e limpa:
    Chão:   chao_sombrio.png  (960px peça única, sem tiling)
    Paredes: invisíveis (contém player/boss na arena)

Alinhamento de sprite vs colisão (mesmo padrão da NightArena):
    FLOOR_SOLID_Y = 440     → linha de colisão real
    _FLOOR_RAISE  = 8       → sprite sobe 8px acima → 8px de pedra visível
                              acima dos pés do player → aparência natural
    rect.top      = 432     → onde o sprite é desenhado
    solid_rect.top= 440     → onde a colisão acontece

Parallax (back → front):
    [0] gradient teal    factor=0.000  — estático, garante fundo sem buracos
    [1] sky.png          factor=0.100  — 10% da velocidade da câmera (mais distante)
    [2] composed-bg.png  factor=0.300  — 30% da velocidade da câmera (intermediário)
    [3] back-towers.png  factor=0.500  — 50% da velocidade da câmera (mais próximo)
    [4] top vignette     factor=0.000  — estático, overlay cinematográfico
"""

import pygame
import os
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE

# ── Asset directory ────────────────────────────────────────────────────────────
_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "assets", "arena_sombrio")

def _ap(*parts: str) -> str:
    return os.path.join(_DIR, *parts)


# ═══════════════════════════════════════════════════════════════════════════════
# LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════

FLOOR_SOLID_Y = 440          # y da colisão do chão (imutável — gameplay)

PLAYER_SPAWN  = (220, FLOOR_SOLID_Y)
BOSS_SPAWN    = (720, FLOOR_SOLID_Y)


# ═══════════════════════════════════════════════════════════════════════════════
# GEOMETRIA DO CHÃO
# ═══════════════════════════════════════════════════════════════════════════════

# chao_sombrio.png: conteúdo visível medido em (4,291) size=1523×349
# Proporcional a 960px wide: height = 349*960/1523 ≈ 220px
_CHAO_CROP     = pygame.Rect(1, 116, 608, 139)   # chao_sombrio 612x408 — ratio 4.37:1
_FLOOR_VIS_H   = 220    # ≈ altura proporcional (sem esticar)
_FLOOR_RAISE   = 45     # px de pedra visíveis ACIMA da colisão — sprite sobe 45px acima de FLOOR_SOLID_Y


# ═══════════════════════════════════════════════════════════════════════════════
# SPRITE CACHE
# ═══════════════════════════════════════════════════════════════════════════════

_cache: dict[str, pygame.Surface] = {}
_tried: set[str]                  = set()


def _load(name: str) -> pygame.Surface | None:
    if name in _tried:
        return _cache.get(name)
    _tried.add(name)
    path = _ap(name)
    if not os.path.exists(path):
        print(f"[sombrio_arena] não encontrado: {name}", flush=True)
        return None
    try:
        surf = pygame.image.load(path).convert_alpha()
        _cache[name] = surf
        print(f"[sombrio_arena] carregado: {name} {surf.get_size()}", flush=True)
        return surf
    except pygame.error as exc:
        print(f"[sombrio_arena] ERRO {name}: {exc}", flush=True)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# PALETA TEAL
# ═══════════════════════════════════════════════════════════════════════════════

_SKY_A  = (  4,  16,  26)
_SKY_B  = (  7,  30,  44)
_SKY_C  = ( 12,  50,  64)
_FOG    = ( 14,  52,  68)
_ST_HI  = ( 55,  92,  90)
_ST_MID = ( 30,  58,  58)
_ST_LO  = ( 12,  32,  34)
_GLOW   = ( 40,  96, 100)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _mult(surf: pygame.Surface, rgb: tuple) -> None:
    """BLEND_MULT in-place — escurece e desloca cromaticamente."""
    ov = pygame.Surface(surf.get_size())
    ov.fill(rgb)
    surf.blit(ov, (0, 0), special_flags=pygame.BLEND_MULT)


def _glow_line(surf: pygame.Surface) -> None:
    """Linha de brilho teal na borda superior do sprite."""
    w = surf.get_width()
    pygame.draw.line(surf, _GLOW, (0, 0), (w - 1, 0), 2)
    pygame.draw.line(surf, _ST_HI, (0, 2), (w - 1, 2), 1)


# ═══════════════════════════════════════════════════════════════════════════════
# BACKGROUND BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def _build_gradient() -> pygame.Surface:
    """
    Layer 0 — Gradiente escuro, ESTÁTICO.
    Base de cor por trás de todas as outras layers.
    Garante que nunca haja pixels vazios visíveis na tela.
    """
    surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    for y in range(SCREEN_HEIGHT):
        t = y / SCREEN_HEIGHT
        if t < 0.55:
            t2 = t / 0.55
            c = tuple(int(_SKY_A[i] + t2 * (_SKY_B[i] - _SKY_A[i])) for i in range(3))
        else:
            t2 = (t - 0.55) / 0.45
            c = tuple(int(_SKY_B[i] + t2 * (_SKY_C[i] - _SKY_B[i])) for i in range(3))
        pygame.draw.line(surf, c, (0, y), (SCREEN_WIDTH, y))
    return surf


def _build_bg_layer(name: str, tint: tuple | None = None) -> pygame.Surface:
    """
    Carrega um PNG de background, escala para cobrir SCREEN_HEIGHT
    e aplica tint escuro opcional. A largura resultante (~786px para
    256×176) é tileável horizontalmente pelo _BgLayer.
    """
    raw = _load(name)
    if raw is None:
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        s.fill(_SKY_B)
        return s
    rw, rh = raw.get_size()
    # Escala para cobrir a altura da tela; largura proporcional
    new_h = SCREEN_HEIGHT
    new_w = max(SCREEN_WIDTH, int(rw * new_h / rh)) + 2
    surf  = pygame.transform.scale(raw, (new_w, new_h))
    if tint is not None:
        _mult(surf, tint)
    return surf


def _build_mist() -> pygame.Surface:
    """Névoa teal rente ao chão."""
    h    = 90
    surf = pygame.Surface((SCREEN_WIDTH, h), pygame.SRCALPHA)
    for y in range(h):
        t = 1.0 - y / h
        a = int(85 * t ** 1.5)
        pygame.draw.line(surf, (*_FOG, a), (0, y), (SCREEN_WIDTH - 1, y))
    return surf


def _build_vignette() -> pygame.Surface:
    """Vinheta cinematográfica no topo."""
    h    = 80
    surf = pygame.Surface((SCREEN_WIDTH, h), pygame.SRCALPHA)
    for y in range(h):
        a = int(115 * (1.0 - y / h) ** 1.5)
        pygame.draw.line(surf, (1, 6, 10, a), (0, y), (SCREEN_WIDTH - 1, y))
    return surf


# ═══════════════════════════════════════════════════════════════════════════════
# PARALLAX LAYER
# ═══════════════════════════════════════════════════════════════════════════════

class _BgLayer:
    __slots__ = ("factor", "offset_x", "_surf", "_w", "_y")

    def __init__(self, surf: pygame.Surface, factor: float, y: int = 0):
        self.factor = factor; self.offset_x = 0.0
        self._surf  = surf;   self._w = surf.get_width(); self._y = y

    def update(self, vel_x: float, dt: float) -> None:
        self.offset_x = (self.offset_x + vel_x * self.factor * dt) % self._w

    def draw(self, screen: pygame.Surface) -> None:
        x = -int(self.offset_x)
        while x < SCREEN_WIDTH:
            screen.blit(self._surf, (x, self._y)); x += self._w


# ═══════════════════════════════════════════════════════════════════════════════
# FLOOR SPRITE
# ═══════════════════════════════════════════════════════════════════════════════

def _build_floor() -> pygame.Surface:
    """
    Chão 960 × _FLOOR_VIS_H px — SOMENTE chao_sombrio.png.

    Técnica (sem tiling, sem seams):
        1. subsurface do crop medido (4, 291, 1523, 349).
        2. scale para (960, _FLOOR_VIS_H) — proporção natural ~220px.
        3. linha de brilho teal no topo (assinatura visual do solo).

    Alinhamento:
        sprite.rect.top   = FLOOR_SOLID_Y - _FLOOR_RAISE  (= 432)
        solid_rect.top    = FLOOR_SOLID_Y                  (= 440)
        → 8px de pedra visíveis acima da linha de colisão
        → player parece apoiado naturalmente na superfície
    """
    # Superfície com alpha — pixels transparentes do PNG mostram o background
    surf = pygame.Surface((SCREEN_WIDTH, _FLOOR_VIS_H), pygame.SRCALPHA)

    raw = _load("chao_sombrio.png")
    if raw is None:
        print("[sombrio_arena] AVISO: chao_sombrio.png não encontrado!", flush=True)
        surf.fill((*_ST_MID, 255))
        return surf

    rw, rh = raw.get_size()
    print(f"[sombrio_arena] chao_sombrio: {rw}x{rh}  crop_definido={_CHAO_CROP}", flush=True)

    # Crop seguro — clamp ao tamanho real da imagem
    cx = max(0, min(_CHAO_CROP.x, rw - 1))
    cy = max(0, min(_CHAO_CROP.y, rh - 1))
    cw = max(1, min(_CHAO_CROP.w, rw - cx))
    ch = max(1, min(_CHAO_CROP.h, rh - cy))

    if cx + cw > rw or cy + ch > rh:
        # Fallback: imagem inteira
        print(f"[sombrio_arena] crop fora dos limites — usando imagem inteira", flush=True)
        cx, cy, cw, ch = 0, 0, rw, rh

    safe_rect = pygame.Rect(cx, cy, cw, ch)
    print(f"[sombrio_arena] crop_final={safe_rect}", flush=True)

    crop    = raw.subsurface(safe_rect)
    prop_h  = int(ch * SCREEN_WIDTH / cw)
    scale_h = max(_FLOOR_VIS_H, prop_h)
    scaled  = pygame.transform.scale(crop, (SCREEN_WIDTH, scale_h))
    surf.blit(scaled, (0, 0))
    return surf


# ═══════════════════════════════════════════════════════════════════════════════
# GAME SPRITES
# ═══════════════════════════════════════════════════════════════════════════════

_FLOOR_CACHE: pygame.Surface | None = None


class SombrioFloor(pygame.sprite.Sprite):
    """
    Chão principal — colisão sólida em todas as direções.

    rect.top      = FLOOR_SOLID_Y - _FLOOR_RAISE   → onde o sprite é DESENHADO
    solid_rect.top = FLOOR_SOLID_Y                  → onde a COLISÃO ocorre
    """
    one_way = False

    def __init__(self):
        super().__init__()
        global _FLOOR_CACHE
        if _FLOOR_CACHE is None:
            _FLOOR_CACHE = _build_floor()
        self.image      = _FLOOR_CACHE
        self.rect       = pygame.Rect(
            0,
            FLOOR_SOLID_Y - _FLOOR_RAISE,
            SCREEN_WIDTH,
            _FLOOR_VIS_H,
        )
        self.solid_rect = pygame.Rect(
            0,
            FLOOR_SOLID_Y,
            SCREEN_WIDTH,
            SCREEN_HEIGHT - FLOOR_SOLID_Y,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# BACKGROUND CACHES
# ═══════════════════════════════════════════════════════════════════════════════

_GRAD_CACHE : pygame.Surface | None = None   # gradiente base estático
_SKY_CACHE  : pygame.Surface | None = None   # sky.png
_COMP_CACHE : pygame.Surface | None = None   # composed-bg.png
_TWR_CACHE  : pygame.Surface | None = None   # back-towers.png
_TOP_CACHE  : pygame.Surface | None = None   # vinheta


# ═══════════════════════════════════════════════════════════════════════════════
# ARENA
# ═══════════════════════════════════════════════════════════════════════════════

class SombrioArena:
    """
    Arena Sombria — Bringer of Death / Morthak  (v7, parallax profissional).

    Interface compatível com game.py:
        .parallax_layers  — list[_BgLayer]
        .fallback_bg      — None
        .platforms        — pygame.sprite.Group
        .player_spawn     — (x, y)
        .boss_spawn       — (x, y)
        .floor_y          — int
    """

    def __init__(self):
        global _GRAD_CACHE, _SKY_CACHE, _COMP_CACHE, _TWR_CACHE, _TOP_CACHE

        # Layer 0 — gradiente base (estático, garante fundo sem buracos)
        if _GRAD_CACHE is None: _GRAD_CACHE = _build_gradient()

        # Layer 1 — sky.png (mais distante, movimento mais lento)
        if _SKY_CACHE  is None: _SKY_CACHE  = _build_bg_layer("sky.png",         (55, 80, 90))

        # Layer 2 — composed-bg.png (intermediária, névoa/horizonte)
        if _COMP_CACHE is None: _COMP_CACHE = _build_bg_layer("composed-bg.png",  (45, 70, 82))

        # Layer 3 — back-towers.png (mais próxima, torres em frente)
        if _TWR_CACHE  is None: _TWR_CACHE  = _build_bg_layer("back-towers.png",  (38, 62, 76))

        # Layer 4 — vinheta cinematográfica (estática, sempre no topo)
        if _TOP_CACHE  is None: _TOP_CACHE  = _build_vignette()

        self.parallax_layers = [
            _BgLayer(_GRAD_CACHE, 0.000),   # gradiente base — estático
            _BgLayer(_SKY_CACHE,  0.100),   # sky.png       — 10% da velocidade da câmera
            _BgLayer(_COMP_CACHE, 0.300),   # composed-bg   — 30% da velocidade da câmera
            _BgLayer(_TWR_CACHE,  0.500),   # back-towers   — 50% da velocidade da câmera
            _BgLayer(_TOP_CACHE,  0.000),   # vinheta       — estática
        ]

        self.fallback_bg  = None
        self.platforms    = self._build_platforms()
        self.player_spawn = PLAYER_SPAWN
        self.boss_spawn   = BOSS_SPAWN
        self.floor_y      = FLOOR_SOLID_Y

        ok  = [k for k, v in _cache.items() if v is not None]
        bad = [k for k in _tried if _cache.get(k) is None]
        print(
            f"[sombrio_arena v7] FLOOR_SOLID_Y={FLOOR_SOLID_Y} "
            f"sprite_top={FLOOR_SOLID_Y - _FLOOR_RAISE}  "
            f"ok={ok}  miss={bad}",
            flush=True,
        )

    def _build_platforms(self) -> pygame.sprite.Group:
        """
        Arena mínima:
            • Chão sólido contínuo (chao_sombrio)
            • Paredes laterais invisíveis
        """
        g = pygame.sprite.Group()

        g.add(SombrioFloor())

        # Paredes laterais invisíveis (contêm player e boss)
        for wx in (-TILE_SIZE, SCREEN_WIDTH):
            wall            = pygame.sprite.Sprite()
            wall.image      = pygame.Surface((TILE_SIZE, SCREEN_HEIGHT), pygame.SRCALPHA)
            wall.image.fill((0, 0, 0, 0))
            wall.rect       = pygame.Rect(wx, 0, TILE_SIZE, SCREEN_HEIGHT)
            wall.solid_rect = pygame.Rect(wx, 0, TILE_SIZE, SCREEN_HEIGHT)
            wall.one_way    = False
            g.add(wall)

        return g
