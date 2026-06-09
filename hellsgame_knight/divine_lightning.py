"""
divine_lightning.py — Raio Divino: animacao em 3 fases.

  Fase 1 — Aviso (WARNING_DURATION s):
      Losango amarelo piscante acima do boss indica o alvo.

  Fase 2 — Animacao (DESCENT_DURATION s):
      Spritesheet lightining1-Sheet.png (384x64, 6 frames de 64x64)
      reproduzido quadro a quadro em posicao FIXA sobre o boss.
      A posicao nao muda — apenas o frame exibido avanca no tempo.

  Fase 3 — Impacto (IMPACT_DURATION s):
      Flash circular em expansao + should_hit + should_shake.
      O game.py aplica stun(3s) e screen shake ao receber os sinais.
"""

import pygame
import os

_RAIO_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "assets", "raio", "Thunder Effect 02", "Thunder Strike"
)

# ── Timing ────────────────────────────────────────────────────────────────────
WARNING_DURATION = 0.25   # s — indicador piscante acima do boss
DESCENT_DURATION = 0.35   # s — animacao de queda
HIT_TIME         = WARNING_DURATION + DESCENT_DURATION   # 0.60 s
IMPACT_DURATION  = 0.15   # s — flash de impacto
TOTAL_DURATION   = HIT_TIME + IMPACT_DURATION            # 0.75 s

# ── Spritesheet ───────────────────────────────────────────────────────────────
FRAME_W   = 64   # px — largura de cada frame no spritesheet
FRAME_H   = 64   # px — altura  de cada frame no spritesheet
DISPLAY_W = 128  # px — largura de exibicao na tela (altura calculada por boss)

# Cache global: frames fatiados, carregados uma vez por sessao pygame
_RAW_FRAMES: list | None = None


def _ensure_frames() -> list:
    """Fatia lightining1-Sheet.png em frames individuais (lazy, cached)."""
    global _RAW_FRAMES
    if _RAW_FRAMES is not None:
        return _RAW_FRAMES

    path = os.path.join(_RAIO_DIR, "lightining1-Sheet.png")
    try:
        sheet = pygame.image.load(path).convert_alpha()
        w, h  = sheet.get_size()
        n     = w // FRAME_W
        print(
            f"[divine_lightning] lightining1-Sheet.png  {w}x{h} px  "
            f"{n} frames de {FRAME_W}x{FRAME_H}",
            flush=True,
        )
        frames = [
            sheet.subsurface(pygame.Rect(i * FRAME_W, 0, FRAME_W, min(FRAME_H, h)))
            for i in range(n)
        ]
    except Exception as e:
        print(f"[divine_lightning] ERRO ao carregar spritesheet: {e}", flush=True)
        fb = pygame.Surface((FRAME_W, FRAME_H), pygame.SRCALPHA)
        fb.fill((255, 220, 0, 220))
        frames = [fb]

    _RAW_FRAMES = frames
    return _RAW_FRAMES


# ── Classe principal ──────────────────────────────────────────────────────────

class DivineThunder:
    """
    Efeito visual em 3 fases + sinais de hit/shake para o game.py.

    Uso em game.py:
        lt = DivineThunder(boss.hitbox.centerx, boss.hitbox.centery)
        lt.update(dt)
        if lt.should_hit:    boss.take_damage(1); boss.stun(3.0)
        if lt.should_shake:  self._shake_timer = 0.25
        if lt.done:          # descartar da lista
    """

    def __init__(self, boss_cx: int, boss_cy: int):
        self.boss_cx = boss_cx
        self.boss_cy = boss_cy
        self.timer   = 0.0
        self.done    = False

        # Sinais de um unico frame cada
        self.should_hit    = False
        self.should_shake  = False
        self._hit_signaled = False

        raw = _ensure_frames()
        self._n = len(raw)

        # Altura calculada para que rect.bottom == boss_cy e rect.top < 0 (acima da tela).
        # display_h = boss_cy + margem → top = boss_cy - display_h = -margem
        _ABOVE_SCREEN = 60   # px que o topo do raio fica acima da borda superior da tela
        self._display_h = boss_cy + _ABOVE_SCREEN
        self._frames = [
            pygame.transform.scale(f, (DISPLAY_W, self._display_h)) for f in raw
        ]

    # ── Logica ────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        self.should_hit   = False
        self.should_shake = False
        self.timer       += dt

        if not self._hit_signaled and self.timer >= HIT_TIME:
            self.should_hit    = True
            self.should_shake  = True
            self._hit_signaled = True

        if self.timer >= TOTAL_DURATION:
            self.done = True

    # ── Desenho ───────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface) -> None:
        if self.done:
            return

        if self.timer < WARNING_DURATION:
            self._draw_warning(screen)
        elif self.timer < HIT_TIME:
            self._draw_descent(screen)
        else:
            self._draw_impact(screen)

    def _draw_warning(self, screen: pygame.Surface) -> None:
        """Losango amarelo piscante acima do boss."""
        if int(self.timer * 10) % 2 == 0:
            cx  = self.boss_cx
            cy  = self.boss_cy - 75
            sz  = 14
            pts = [(cx, cy - sz), (cx + sz, cy), (cx, cy + sz), (cx - sz, cy)]
            pygame.draw.polygon(screen, (255, 230, 30), pts)
            pygame.draw.polygon(screen, (255, 255, 180), pts, 2)

    def _draw_descent(self, screen: pygame.Surface) -> None:
        """Frames da spritesheet em posicao fixa: base alinhada com boss, topo acima da tela."""
        if self._n == 0:
            return

        t = (self.timer - WARNING_DURATION) / DESCENT_DURATION
        t = max(0.0, min(1.0, t))

        # Apenas o frame muda — posicao permanece fixa durante toda a animacao
        frame_idx = min(int(t * self._n), self._n - 1)
        frame     = self._frames[frame_idx]

        rect         = frame.get_rect()
        rect.centerx = self.boss_cx   # centrado horizontalmente no boss
        rect.bottom  = self.boss_cy   # base alinhada ao boss → topo fica acima da tela
        screen.blit(frame, rect)

    def _draw_impact(self, screen: pygame.Surface) -> None:
        """Flash circular em expansao que some gradualmente."""
        t = min(1.0, (self.timer - HIT_TIME) / IMPACT_DURATION)

        alpha  = max(0, int(255 * (1.0 - t)))
        radius = int(DISPLAY_W // 2 + t * DISPLAY_W)

        if radius > 0 and alpha > 0:
            diam  = radius * 2
            flash = pygame.Surface((diam, diam), pygame.SRCALPHA)
            pygame.draw.circle(flash, (255, 255, 220, alpha), (radius, radius), radius)
            screen.blit(flash, (self.boss_cx - radius, self.boss_cy - radius))
