from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Type

import pygame


@dataclass
class PoolStats:
    created: int = 0
    reused: int = 0
    released: int = 0


class EnemyPool:
    """
    Pool simples de sprites (principalmente inimigos).
    Objetivo: evitar picos de CPU por create/destroy repetido.

    Regras:
    - Sprites no pool devem implementar reset(x, y) (opcional) para reuso.
    - Ao liberar: sprite.kill() já remove dos Groups; o pool só guarda referência.
    """

    def __init__(self):
        self._inactive: dict[Type[pygame.sprite.Sprite], list[pygame.sprite.Sprite]] = {}
        self.stats: dict[Type[pygame.sprite.Sprite], PoolStats] = {}

    def _s(self, cls: Type[pygame.sprite.Sprite]) -> PoolStats:
        if cls not in self.stats:
            self.stats[cls] = PoolStats()
        return self.stats[cls]

    def acquire(self, cls: Type[pygame.sprite.Sprite], x: int, y: int, *args, **kwargs) -> pygame.sprite.Sprite:
        bucket = self._inactive.get(cls)
        if bucket:
            obj = bucket.pop()
            st = self._s(cls)
            st.reused += 1
            if hasattr(obj, "reset"):
                obj.reset(x, y, *args, **kwargs)  # type: ignore[attr-defined]
            else:
                # Fallback: reposiciona se não tiver reset
                if hasattr(obj, "rect"):
                    obj.rect.midbottom = (x, y)
            print(f"[pool] reuse {cls.__name__} (inactive_left={len(bucket)})", flush=True)
            return obj

        obj = cls(x, y, *args, **kwargs)
        st = self._s(cls)
        st.created += 1
        print(f"[pool] create {cls.__name__}", flush=True)
        return obj

    def release(self, obj: pygame.sprite.Sprite) -> None:
        cls = type(obj)
        self._inactive.setdefault(cls, []).append(obj)
        st = self._s(cls)
        st.released += 1
        print(f"[pool] release {cls.__name__} (inactive={len(self._inactive[cls])})", flush=True)

