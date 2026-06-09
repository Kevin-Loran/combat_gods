"""
particles.py — Partículas de poeira procedurais para o boss Minotauro.

DustParticle  — círculo procedural (sem sprites externos)
ParticleSystem — gerencia emit, update e draw das partículas de poeira

Pedras (FallingRock / RockHazardSystem) estão em rock_hazard.py.
"""

import pygame
import random
import math


class DustParticle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'radius', 'max_radius', 'life', 'max_life', 'color')

    def __init__(self, x, y, vx, vy, radius, life, color):
        self.x          = float(x)
        self.y          = float(y)
        self.vx         = float(vx)
        self.vy         = float(vy)
        self.radius     = float(radius)
        self.max_radius = float(radius)
        self.life       = float(life)
        self.max_life   = float(life)
        self.color      = color

    def update(self, dt: float):
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        self.vy += 80.0 * dt
        self.vx *= max(0.0, 1.0 - 3.5 * dt)
        self.life   -= dt
        self.radius  = self.max_radius * max(0.0, self.life / self.max_life)

    @property
    def alive(self) -> bool:
        return self.life > 0.0

    def draw(self, screen: pygame.Surface):
        r = max(1, int(self.radius))
        size = r * 2 + 2
        alpha = int(210 * max(0.0, self.life / self.max_life))
        surf = pygame.Surface((size, size))
        surf.set_colorkey((0, 0, 0))
        pygame.draw.circle(surf, self.color, (r + 1, r + 1), r)
        surf.set_alpha(alpha)
        screen.blit(surf, (int(self.x) - r - 1, int(self.y) - r - 1))


class ParticleSystem:
    _COLORS = [
        (196, 163,  90),
        (180, 140,  70),
        (210, 185, 130),
        (125,  90,  47),
        (232, 210, 155),
    ]

    def __init__(self):
        self.particles: list[DustParticle] = []

    def _rand_color(self) -> tuple:
        return random.choice(self._COLORS)

    # ── Emissores ─────────────────────────────────────────────────────────────

    def emit_stomp(self, x: float, y: float, count: int = 4):
        """Poeira ao iniciar o ataque (pisada pesada)."""
        for _ in range(count):
            angle = random.uniform(math.pi * 1.1, math.pi * 1.9)
            speed = random.uniform(28, 72)
            self.particles.append(DustParticle(
                x + random.uniform(-18, 18), y,
                math.cos(angle) * speed,
                math.sin(angle) * speed - 38,
                random.uniform(3.5, 7.5),
                random.uniform(0.38, 0.62),
                self._rand_color(),
            ))

    def emit_impact(self, x: float, y: float, facing: int, count: int = 7):
        """Burst de poeira no frame de impacto do golpe."""
        for _ in range(count):
            base  = 0.0 if facing == 1 else math.pi
            angle = base + random.uniform(-math.pi * 0.65, math.pi * 0.65)
            speed = random.uniform(55, 125)
            self.particles.append(DustParticle(
                x + random.uniform(-14, 14), y,
                math.cos(angle) * speed,
                math.sin(angle) * speed - 58,
                random.uniform(4.5, 11.0),
                random.uniform(0.28, 0.54),
                self._rand_color(),
            ))

    def emit_recovery(self, x: float, y: float, count: int = 3):
        """Poeira leve ao entrar em recovery."""
        for _ in range(count):
            angle = random.uniform(math.pi * 1.2, math.pi * 1.8)
            speed = random.uniform(14, 42)
            self.particles.append(DustParticle(
                x + random.uniform(-14, 14), y,
                math.cos(angle) * speed,
                math.sin(angle) * speed - 20,
                random.uniform(2.0, 5.5),
                random.uniform(0.22, 0.44),
                self._rand_color(),
            ))

    def emit_footstep(self, x: float, y: float, facing: int, count: int = 2):
        """Puff pequeno a cada passo."""
        for _ in range(count):
            vx = random.uniform(-22, 22) - facing * 10
            vy = random.uniform(-38, -14)
            self.particles.append(DustParticle(
                x + random.uniform(-10, 10), y,
                vx, vy,
                random.uniform(1.5, 4.0),
                random.uniform(0.18, 0.32),
                self._rand_color(),
            ))

    # ── Update / Draw / Clear ─────────────────────────────────────────────────

    def update(self, dt: float):
        self.particles = [p for p in self.particles if p.alive]
        for p in self.particles:
            p.update(dt)

    def draw(self, screen: pygame.Surface):
        for p in self.particles:
            p.draw(screen)

    def clear(self):
        self.particles.clear()
