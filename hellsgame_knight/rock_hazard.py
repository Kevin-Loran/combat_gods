"""
rock_hazard.py — Pedras ambientais da arena (falling hazard).

FallingRock      — entidade independente: nasce acima da tela, cai com
                   gravidade, causa dano ao player ou impacto no chão.
RockHazardSystem — gerencia spawn aleatório por timer, sem nenhuma
                   dependência da AI ou attack state do boss.
"""

import pygame
import random
import os
from settings import SCREEN_WIDTH

# ── Paths ─────────────────────────────────────────────────────────────────────
_BOSS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "boss")

def _rock_asset(*parts):
    return os.path.join(_BOSS_DIR, "rock", *parts)


def _frame_has_content(surf: pygame.Surface, min_pixels: int = 80) -> bool:
    """Retorna True se o frame tem pelo menos min_pixels visíveis (alpha > 10)."""
    w, h = surf.get_size()
    count = 0
    for py in range(h):
        for px in range(w):
            if surf.get_at((px, py))[3] > 10:
                count += 1
                if count >= min_pixels:
                    return True
    return False


def _find_intact_frame(frames: list) -> pygame.Surface:
    """Retorna o frame mais escuro entre os mais sólidos — aglomerado de pedra intacto.
    Critério: entre todos os frames com >= 80% dos pixels do frame mais denso,
    escolhe o de menor brightness (mais escuro = pedras marrons sólidas)."""
    def _stats(surf):
        w, h = surf.get_size()
        n = tr = tg = tb = 0
        for py in range(h):
            for px in range(w):
                col = surf.get_at((px, py))
                if col[3] > 10:
                    tr += col[0]; tg += col[1]; tb += col[2]; n += 1
        brightness = (tr + tg + tb) // (3 * n) if n > 0 else 999
        return n, brightness

    stats     = [_stats(f) for f in frames]
    max_px    = max(s[0] for s in stats)
    threshold = max_px * 0.80   # candidatos com ao menos 80% do frame mais denso

    # Entre os candidatos sólidos, escolhe o mais escuro (menor brightness)
    candidates = [(brightness, i)
                  for i, (px, brightness) in enumerate(stats)
                  if px >= threshold]
    best_idx = min(candidates)[1]   # menor brightness = mais escuro
    return frames[best_idx]

# ── Constantes ────────────────────────────────────────────────────────────────
ROCK_SPAWN_MIN  = 2.5     # s mínimo entre spawns
ROCK_SPAWN_MAX  = 5.0     # s máximo entre spawns
ROCK_FALL_SPEED = 130.0   # vy inicial (px/s, positivo = para baixo)
ROCK_GRAVITY    = 340.0   # aceleração gravitacional (px/s²)
ROCK_VX_MIN     = 70.0    # diagonal mínima garantida — sem queda vertical
ROCK_VX_MAX     = 200.0   # diagonal máxima
ROCK_DAMAGE     = 1       # corações removidos ao atingir player
ROCK_IMPACT_SPF = 0.055   # s/frame da animação de impacto
ROCK_FW         = 48      # largura do frame — rock spritesheet
ROCK_FH         = 48      # altura do frame — rock spritesheet
IMPACT_FW       = 48      # largura do frame — impact spritesheet
IMPACT_FH       = 48      # altura do frame — impact spritesheet
ARENA_MARGIN    = 80      # margem horizontal (evita spawnar grudado na parede)


# ── Entidade ──────────────────────────────────────────────────────────────────

class FallingRock:
    """
    Projétil ambiental independente.
    Não conhece o boss, não depende da state machine do boss.
    """

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 ground_y: float, falling_frame: pygame.Surface,
                 impact_frames: list, scale: float = 1.0):
        self.x        = float(x)
        self.y        = float(y)
        self.vx       = float(vx)
        self.vy       = float(vy)
        self.ground_y = float(ground_y)
        self.state    = "falling"   # "falling" | "impact" | "done"
        self.anim_timer = 0.0
        self.impact_idx = 0

        def _scale(surf):
            if abs(scale - 1.0) < 0.02:
                return surf
            return pygame.transform.scale(
                surf, (max(1, int(surf.get_width()  * scale)),
                       max(1, int(surf.get_height() * scale))))

        # Frame único da pedra intacta — NÃO aleatório, NÃO fragmentado
        self._rock_surf     = _scale(falling_frame)
        self._impact_frames = [_scale(f) for f in impact_frames]

        # Hitbox 3/4 do sprite — alinhada com o visual da pedra grande
        rw = self._rock_surf.get_width()
        rh = self._rock_surf.get_height()
        self.hitbox = pygame.Rect(0, 0, max(16, rw * 3 // 4), max(16, rh * 3 // 4))
        self._sync_hitbox()

    # ─────────────────────────────────────────────────────────────────────────

    def _sync_hitbox(self):
        self.hitbox.centerx = int(self.x)
        self.hitbox.centery = int(self.y)

    def _start_impact(self):
        self.state      = "impact"
        self.impact_idx = 0
        self.anim_timer = 0.0

    @property
    def alive(self) -> bool:
        return self.state != "done"

    # ─────────────────────────────────────────────────────────────────────────

    def update(self, dt: float, player) -> None:
        if self.state == "falling":
            self.x  += self.vx * dt
            self.y  += self.vy * dt
            self.vy += ROCK_GRAVITY * dt    # gravidade puxa para baixo
            self._sync_hitbox()

            # Colide com player — roll deixa o player intangível
            if player.alive and not player.is_rolling:
                if self.hitbox.colliderect(player.hitbox):
                    player.take_damage(ROCK_DAMAGE)
                    self._start_impact()
                    return

            # Atinge o chão
            if self.y >= self.ground_y:
                self.y = self.ground_y
                self._start_impact()

        elif self.state == "impact":
            self.anim_timer += dt
            if self.anim_timer >= ROCK_IMPACT_SPF:
                self.anim_timer -= ROCK_IMPACT_SPF
                self.impact_idx += 1
                if self.impact_idx >= len(self._impact_frames):
                    self.state = "done"

    def draw(self, screen: pygame.Surface) -> None:
        if self.state == "falling":
            w = self._rock_surf.get_width()
            h = self._rock_surf.get_height()
            screen.blit(self._rock_surf,
                        (int(self.x) - w // 2, int(self.y) - h // 2))

        elif self.state == "impact":
            if self.impact_idx < len(self._impact_frames):
                f = self._impact_frames[self.impact_idx]
                # Bottom do sprite ancorado no chão
                screen.blit(f, (int(self.x) - f.get_width()  // 2,
                                int(self.ground_y) - f.get_height()))


# ── Sistema de spawn ──────────────────────────────────────────────────────────

class RockHazardSystem:
    """
    Gerencia o spawn aleatório de pedras. Completamente independente do boss.
    Deve ser instanciado e atualizado pelo Game, não pelo MinotaurBoss.
    """

    def __init__(self):
        self._rocks:         list[FallingRock] = []
        self._rock_frames   = None   # todos os frames válidos (para diagnóstico)
        self._falling_frame = None   # frame único da pedra intacta (para FALLING)
        self._impact_frames = None
        # Timer inicia com valor aleatório para o primeiro spawn não ser imediato
        self._spawn_timer   = random.uniform(ROCK_SPAWN_MIN, ROCK_SPAWN_MAX)

    # ── Assets ───────────────────────────────────────────────────────────────

    def load_sprites(self, rock_path: str, impact_path: str) -> None:
        try:
            rs   = pygame.image.load(rock_path).convert_alpha()
            cols = rs.get_width()  // ROCK_FW
            rows = rs.get_height() // ROCK_FH
            all_frames = [
                rs.subsurface(pygame.Rect(c * ROCK_FW, r * ROCK_FH, ROCK_FW, ROCK_FH))
                for r in range(rows) for c in range(cols)
            ]
            # Filtra frames vazios/quase-vazios do spritesheet
            self._rock_frames = [f for f in all_frames if _frame_has_content(f)]
            # Identifica o frame mais sólido — pedra intacta para o estado FALLING
            self._falling_frame = _find_intact_frame(self._rock_frames)
            print(f"[rock_hazard] frames válidos: {len(self._rock_frames)}/{len(all_frames)}", flush=True)
            ims   = pygame.image.load(impact_path).convert_alpha()
            n_imp = ims.get_width() // IMPACT_FW
            self._impact_frames = [
                ims.subsurface(pygame.Rect(c * IMPACT_FW, 0, IMPACT_FW, IMPACT_FH))
                for c in range(n_imp)
            ]
            print(
                f"[rock_hazard] rock: {len(self._rock_frames)} frames | "
                f"impact: {len(self._impact_frames)} frames",
                flush=True,
            )
        except Exception as e:
            print(f"[rock_hazard] ERRO ao carregar sprites: {e}", flush=True)

    # ── Spawn ─────────────────────────────────────────────────────────────────

    def _spawn(self, ground_y: float) -> None:
        if not self._falling_frame or not self._impact_frames:
            return
        x     = random.uniform(ARENA_MARGIN, SCREEN_WIDTH - ARENA_MARGIN)
        y     = -120.0
        vx    = random.choice([-1, 1]) * random.uniform(ROCK_VX_MIN, ROCK_VX_MAX)
        vy    = ROCK_FALL_SPEED + random.uniform(0.0, 50.0)
        scale = random.uniform(1.9, 2.7)
        self._rocks.append(
            FallingRock(x, y, vx, vy, ground_y,
                        self._falling_frame, self._impact_frames, scale)
        )

    # ── Update / Draw / Clear ─────────────────────────────────────────────────

    def update(self, dt: float, player, ground_y: float) -> None:
        self._spawn_timer -= dt
        if self._spawn_timer <= 0.0:
            self._spawn_timer = random.uniform(ROCK_SPAWN_MIN, ROCK_SPAWN_MAX)
            self._spawn(ground_y)

        self._rocks = [r for r in self._rocks if r.alive]
        for r in self._rocks:
            r.update(dt, player)

    def draw(self, screen: pygame.Surface) -> None:
        for r in self._rocks:
            r.draw(screen)

    def clear(self) -> None:
        self._rocks.clear()
