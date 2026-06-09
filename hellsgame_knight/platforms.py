"""
platform.py — Plataforma contínua usando plataforma_principal_960.png.

A imagem plataforma_principal_960.png (960x111, fundo preto) cobre exatamente
a largura da tela. Fundo preto removido via colorkey.

TOP_INSET: pixels do topo da imagem que são decorativos (não colidem).
           Ajuste se o personagem afundar (+) ou flutuar (-).
"""

import pygame
import os
from settings import *

PLATFORM_IMAGE = asset_path("plataforma_principal_960.png")
TOP_INSET = 10   # topo decorativo (pedras arredondadas do novo asset)

_tile_cache: pygame.Surface | None = None


def _load_tile() -> pygame.Surface:
    global _tile_cache
    if _tile_cache is not None:
        return _tile_cache

    if os.path.exists(PLATFORM_IMAGE):
        raw = pygame.image.load(PLATFORM_IMAGE).convert()
        # Remove fundo preto via colorkey
        raw.set_colorkey((0, 0, 0))
        # Converte para SRCALPHA para preservar a transparência
        surf = pygame.Surface(raw.get_size(), pygame.SRCALPHA)
        surf.blit(raw, (0, 0))
        _tile_cache = surf
        return surf

    # Fallback colorido se imagem não encontrada
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    surf.fill(PLATFORM_C)
    _tile_cache = surf
    return surf


class Platform(pygame.sprite.Sprite):
    """
    self.rect       — bounding box completo (renderização)
    self.solid_rect — superfície de colisão (sem o TOP_INSET decorativo)
    """

    def __init__(self, x: int, y: int, tile_count: int = 1, tile_height: int = 1):
        super().__init__()

        tile = _load_tile()
        tw, th = tile.get_size()

        # tile_count automático: cobre toda a tela + 1 tile extra para scroll
        # Se o tile já tem ~960px, tile_count=2 cobre tela + margem de segurança
        if tile_count <= 1:
            tile_count = max(2, (SCREEN_WIDTH // tw) + 2)

        total_w = tw * tile_count
        total_h = th

        self.image = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
        for col in range(tile_count):
            self.image.blit(tile, (col * tw, 0))

        self.rect = self.image.get_rect(topleft=(x, y))

        # solid_rect: começa onde o visual sólido começa (após TOP_INSET)
        self.solid_rect = pygame.Rect(x, y + TOP_INSET, total_w, total_h - TOP_INSET)