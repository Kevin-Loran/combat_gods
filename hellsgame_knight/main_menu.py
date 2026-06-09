"""
main_menu.py — Main menu and battle selection screens.
"""
import pygame
import random
import os
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, ASSETS_DIR

_PARALLAX_FILES = [
    ("parallax-demon-woods-bg.png",          0.05),
    ("parallax-demon-woods-far-trees.png",   0.10),
    ("parallax-demon-woods-mid-trees.png",   0.20),
    ("parallax-demon-woods-close-trees.png", 0.35),
]


# ── Ember particle ─────────────────────────────────────────────────────────────

class _Ember:
    _COLORS = [
        (255, 100, 20), (255, 60, 0), (220, 140, 30),
        (255, 180, 50), (200, 40,  0),
    ]

    def __init__(self):
        self._reset(initial=True)

    def _reset(self, initial=False):
        self.x        = random.uniform(0, SCREEN_WIDTH)
        self.y        = random.uniform(SCREEN_HEIGHT * 0.4, SCREEN_HEIGHT + 10) \
                        if not initial else random.uniform(0, SCREEN_HEIGHT)
        self.vx       = random.uniform(-18, 18)
        self.vy       = random.uniform(-55, -25)
        self.max_life = random.uniform(1.8, 4.0)
        self.life     = self.max_life if not initial else random.uniform(0.0, self.max_life)
        self.radius   = random.uniform(1.5, 3.5)
        self.color    = random.choice(self._COLORS)

    def update(self, dt):
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        self.vx   += random.uniform(-8, 8) * dt
        self.life -= dt
        if self.life <= 0 or self.y < -10:
            self._reset()

    def draw(self, screen):
        t     = max(0.0, self.life / self.max_life)
        r     = max(1, int(self.radius * t))
        alpha = int(200 * t)
        surf  = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (r + 1, r + 1), r)
        screen.blit(surf, (int(self.x) - r - 1, int(self.y) - r - 1))


# ── Slow-drift parallax ────────────────────────────────────────────────────────

class _MenuParallax:
    def __init__(self):
        self._layers = []
        self._offset = 0.0

    def load(self):
        for fname, factor in _PARALLAX_FILES:
            path = os.path.join(ASSETS_DIR, fname)
            if not os.path.exists(path):
                continue
            try:
                img = pygame.image.load(path).convert_alpha()
                ow, oh = img.get_size()
                nw     = int(ow * SCREEN_HEIGHT / oh)
                img    = pygame.transform.scale(img, (nw, SCREEN_HEIGHT))
                self._layers.append((img, factor, nw))
            except pygame.error:
                pass

    def update(self, dt):
        self._offset += 12.0 * dt

    def draw(self, screen):
        if not self._layers:
            screen.fill((8, 3, 3))
            return
        for img, factor, img_w in self._layers:
            off = (self._offset * factor) % img_w
            x   = -int(off)
            while x < SCREEN_WIDTH:
                screen.blit(img, (x, 0))
                x += img_w


# ── Gold button (larger than menu.py version) ──────────────────────────────────

_MBTN_W   = 260
_MBTN_H   = 46
_MBTN_GAP = 14


class _MenuButton:
    def __init__(self, label):
        self.label = label
        self._font = pygame.font.SysFont("monospace", 18, bold=True)
        self._norm = self._bake(False)
        self._sel  = self._bake(True)
        self.rect  = pygame.Rect(0, 0, _MBTN_W, _MBTN_H)

    def _bake(self, selected):
        surf  = pygame.Surface((_MBTN_W, _MBTN_H), pygame.SRCALPHA)
        outer = (48, 32,  0) if selected else (22, 14,  0)
        inner = (245, 190, 38) if selected else (148, 105, 18)
        fill  = (115, 75,  5) if selected else (50,  33,  2)
        tc    = (255, 242, 148) if selected else (198, 173, 96)
        pygame.draw.rect(surf, outer, (0, 0, _MBTN_W, _MBTN_H),       border_radius=6)
        pygame.draw.rect(surf, inner, (1, 1, _MBTN_W-2, _MBTN_H-2),   border_radius=5)
        pygame.draw.rect(surf, fill,  (3, 3, _MBTN_W-6, _MBTN_H-6),   border_radius=4)
        shine = pygame.Surface((_MBTN_W - 12, 4), pygame.SRCALPHA)
        shine.fill((255, 252, 205, 68 if selected else 22))
        surf.blit(shine, (6, 6))
        lbl = self._font.render(self.label, True, tc)
        surf.blit(lbl, lbl.get_rect(center=(_MBTN_W // 2, _MBTN_H // 2)))
        return surf

    def draw(self, screen, cx, cy, selected):
        self.rect.center = (cx, cy)
        screen.blit(self._sel if selected else self._norm, self.rect)
        if selected:
            tx  = self.rect.left - 16
            pts = [(tx, cy), (tx - 10, cy - 7), (tx - 10, cy + 7)]
            pygame.draw.polygon(screen, (255, 215, 48), pts)

    def hit(self, pos):
        return self.rect.collidepoint(pos)


# ── Main Menu ─────────────────────────────────────────────────────────────────

class MainMenuState:
    """
    Tela inicial. Retorna acoes: 'play', 'select_battle', 'quit'.
    """
    _LABELS  = ("JOGAR", "SELECIONAR BATALHA", "SAIR")
    _ACTIONS = ("play", "select_battle", "quit")

    def __init__(self):
        self._parallax   = _MenuParallax()
        self._parallax.load()
        self._embers     = [_Ember() for _ in range(28)]
        self._buttons    = [_MenuButton(l) for l in self._LABELS]
        self._sel        = 0
        self._font_title = pygame.font.SysFont("monospace", 72, bold=True)
        self._font_sub   = pygame.font.SysFont("monospace", 22, bold=True)
        self._font_hint  = pygame.font.SysFont("monospace", 12)

    def reset(self):
        self._sel = 0

    def handle(self, event) -> str | None:
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k in (pygame.K_UP, pygame.K_w):
                self._sel = (self._sel - 1) % len(self._buttons)
            elif k in (pygame.K_DOWN, pygame.K_s):
                self._sel = (self._sel + 1) % len(self._buttons)
            elif k in (pygame.K_RETURN, pygame.K_SPACE):
                return self._ACTIONS[self._sel]
            elif k == pygame.K_ESCAPE:
                return "quit"
        elif event.type == pygame.MOUSEMOTION:
            for i, btn in enumerate(self._buttons):
                if btn.hit(event.pos):
                    self._sel = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, btn in enumerate(self._buttons):
                if btn.hit(event.pos):
                    return self._ACTIONS[i]
        return None

    def update(self, dt):
        self._parallax.update(dt)
        for e in self._embers:
            e.update(dt)

    def draw(self, screen):
        self._parallax.draw(screen)

        # Atmospheric overlay
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 110))
        screen.blit(ov, (0, 0))

        for e in self._embers:
            e.draw(screen)

        cx = SCREEN_WIDTH // 2

        # Title with drop shadow
        shadow = self._font_title.render("COMBAT GODS", True, (60, 5, 5))
        title  = self._font_title.render("COMBAT GODS", True, (210, 30, 15))
        tr     = title.get_rect(center=(cx, 165))
        screen.blit(shadow, (tr.x + 3, tr.y + 3))
        screen.blit(title,  tr)

        # Subtitle
        sub = self._font_sub.render("BOSS  BATTLES", True, (188, 148, 52))
        screen.blit(sub, sub.get_rect(center=(cx, 218)))

        # Decorative separator
        pygame.draw.line(screen, (130, 90, 20), (cx - 160, 241), (cx + 160, 241), 1)

        # Buttons
        btn_y0 = 305
        for i, btn in enumerate(self._buttons):
            btn.draw(screen, cx, btn_y0 + i * (_MBTN_H + _MBTN_GAP), i == self._sel)

        # Navigation hint
        hint = self._font_hint.render(
            "↑↓  Navegar     Enter  Confirmar", True, (90, 75, 40))
        screen.blit(hint, hint.get_rect(center=(cx, SCREEN_HEIGHT - 18)))


# ── Battle Select — boss data ─────────────────────────────────────────────────

_BOSSES = [
    {
        "name":         "MINOTAURO",
        "sub":          "Guardiao do Labirinto",
        "lore":         "Forca bruta implacavel",
        "unlocked":     True,
        "action":       "play",            # arena = minotaur
        "preview_dir":  "boss/idle",
        "preview_crop": (93, 26, 124, 128),
    },
    {
        "name":         "NIGHT GUARDIAN",
        "sub":          "Senhor das Sombras Eternas",
        "lore":         "A noite o pertence",
        "unlocked":     True,
        "action":       "play_night",
        "preview_dir":  "noite_boss/idle",
        "preview_crop": None,
    },
    {
        "name":         "MORTHAK",
        "sub":          "Bringer of Death",
        "lore":         "A morte caminhou pela terra",
        "unlocked":     True,
        "action":       "play_sombrio",
        "preview_dir":  "sombrio_boss/idle",
        "preview_crop": None,
    },
]


# ── Boss preview — animated idle sprite ───────────────────────────────────────

_PREVIEW_MAX = 230   # max dimension (px) for the scaled sprite in the preview panel
_PREVIEW_SPF = 0.085 # seconds per frame (~12 fps idle animation)


class _BossPreview:
    """
    Loads, caches and animates the boss idle sprite for the preview panel.
    Supports multiple bosses (keyed by index) for future expansion.
    Sprites are cropped to their content bounding box so transparency
    does not create dead-space, then uniformly scaled to _PREVIEW_MAX.
    """

    def __init__(self):
        self._cache: dict[int, list] = {}  # boss_idx -> list[Surface]
        self._timer  = 0.0
        self._fidx   = 0
        self._cur    = -1
        self._font_q = None   # lazy-init on first draw

    def preload(self, boss_idx: int, preview_dir,
                crop_hint=None) -> None:
        """
        Load and scale idle frames for one boss.
        crop_hint: optional (x, y, w, h) pre-measured content bounding box.
                   When provided, pixel-iteration is skipped (fast path).
                   When None, bounding box is computed dynamically (slow).
        """
        if boss_idx in self._cache:
            return
        if not preview_dir:
            self._cache[boss_idx] = []
            return

        dir_path = os.path.join(ASSETS_DIR, preview_dir)
        if not os.path.isdir(dir_path):
            self._cache[boss_idx] = []
            return

        # Load PNGs sorted numerically
        fnames = sorted(
            [f for f in os.listdir(dir_path) if f.lower().endswith(".png")],
            key=lambda s: int("".join(filter(str.isdigit, s)) or "0"),
        )
        raw = []
        for fname in fnames:
            try:
                raw.append(pygame.image.load(
                    os.path.join(dir_path, fname)).convert_alpha())
            except pygame.error:
                pass
        if not raw:
            self._cache[boss_idx] = []
            return

        # Determine crop rect
        fw, fh = raw[0].get_size()
        if crop_hint is not None:
            # Fast path: use pre-measured bbox
            cx0, cy0, cw, ch = crop_hint
        else:
            # Slow path: pixel-scan all frames for unified bbox (no jitter)
            mx0, my0, mx1, my1 = fw, fh, 0, 0
            for f in raw:
                for y in range(fh):
                    for x in range(fw):
                        if f.get_at((x, y))[3] > 10:
                            if x < mx0: mx0 = x
                            if y < my0: my0 = y
                            if x > mx1: mx1 = x
                            if y > my1: my1 = y
            pad = 10
            cx0 = max(0, mx0 - pad)
            cy0 = max(0, my0 - pad)
            cw  = min(fw, mx1 + pad) - cx0
            ch  = min(fh, my1 + pad) - cy0

        scl  = min(_PREVIEW_MAX / cw, _PREVIEW_MAX / ch)
        dw   = max(1, int(cw * scl))
        dh   = max(1, int(ch * scl))
        crop = pygame.Rect(cx0, cy0, cw, ch)

        scaled = []
        for f in raw:
            cropped = f.subsurface(crop).copy()
            scaled.append(pygame.transform.scale(cropped, (dw, dh)))
        self._cache[boss_idx] = scaled

    def update(self, dt: float, boss_idx: int) -> None:
        if boss_idx != self._cur:
            self._cur   = boss_idx
            self._timer = 0.0
            self._fidx  = 0
        frames = self._cache.get(boss_idx, [])
        if frames:
            self._timer += dt
            self._fidx   = int(self._timer / _PREVIEW_SPF) % len(frames)

    def draw(self, screen: pygame.Surface, cx: int, cy: int,
             boss_idx: int, unlocked: bool) -> None:
        frames = self._cache.get(boss_idx, [])
        if unlocked and frames:
            f = frames[self._fidx % len(frames)]
            # Soft ambient glow behind the sprite
            gw = int(f.get_width()  * 1.14)
            gh = int(f.get_height() * 1.14)
            glow = pygame.transform.scale(f, (gw, gh))
            glow.set_alpha(52)
            screen.blit(glow, glow.get_rect(center=(cx, cy)))
            screen.blit(f, f.get_rect(center=(cx, cy)))
        else:
            # Locked placeholder
            if self._font_q is None:
                self._font_q = pygame.font.SysFont("monospace", 64, bold=True)
            txt = self._font_q.render("?", True, (58, 48, 36))
            screen.blit(txt, txt.get_rect(center=(cx, cy)))


# ── Battle Select — state ─────────────────────────────────────────────────────

# Layout constants (all in screen pixels, screen = 960x540)
_BS_PANEL_Y  = 96    # top of both panels
_BS_PANEL_H  = 410   # height of both panels
_BS_LP_X     = 44    # left panel x
_BS_LP_W     = 292   # left panel width  (preview)
_BS_RP_X     = 356   # right panel x
_BS_RP_W     = 560   # right panel width (battle rows)

_ROW_H   = 88
_ROW_GAP = 12


class BattleSelectState:
    """
    Tela de selecao de batalha.
    Layout: preview animado a esquerda | lista de batalhas a direita.
    Retorna: 'play', 'back'.
    """

    def __init__(self):
        self._parallax = _MenuParallax()
        self._parallax.load()
        self._embers   = [_Ember() for _ in range(18)]
        self._sel      = 0

        # Pre-load preview frames for every boss (once, at construction)
        self._preview = _BossPreview()
        for i, boss in enumerate(_BOSSES):
            self._preview.preload(i, boss.get("preview_dir"),
                                  boss.get("preview_crop"))

        # Fonts
        self._ft = pygame.font.SysFont("monospace", 36, bold=True)  # screen title
        self._fn = pygame.font.SysFont("monospace", 18, bold=True)  # row boss name
        self._fs = pygame.font.SysFont("monospace", 11)             # row subtitle
        self._fp = pygame.font.SysFont("monospace", 15, bold=True)  # preview panel name
        self._fl = pygame.font.SysFont("monospace", 10)             # preview lore / badge
        self._fh = pygame.font.SysFont("monospace", 12)             # hint bar
        self._fnum = pygame.font.SysFont("monospace", 17, bold=True) # row number #1..#3

    def reset(self):
        self._sel = 0

    # ── Geometry helpers ──────────────────────────────────────────────────────

    def _row_rect(self, i: int) -> pygame.Rect:
        total_h = len(_BOSSES) * _ROW_H + (len(_BOSSES) - 1) * _ROW_GAP
        y0      = _BS_PANEL_Y + (_BS_PANEL_H - total_h) // 2
        return pygame.Rect(
            _BS_RP_X + 14,
            y0 + i * (_ROW_H + _ROW_GAP),
            _BS_RP_W - 28,
            _ROW_H,
        )

    # ── Input ─────────────────────────────────────────────────────────────────

    def handle(self, event) -> str | None:
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k in (pygame.K_UP, pygame.K_w):
                self._sel = (self._sel - 1) % len(_BOSSES)
            elif k in (pygame.K_DOWN, pygame.K_s):
                self._sel = (self._sel + 1) % len(_BOSSES)
            elif k in (pygame.K_RETURN, pygame.K_SPACE):
                boss = _BOSSES[self._sel]
                if boss["unlocked"]:
                    return boss["action"]
            elif k == pygame.K_ESCAPE:
                return "back"
        elif event.type == pygame.MOUSEMOTION:
            for i in range(len(_BOSSES)):
                if self._row_rect(i).collidepoint(event.pos):
                    self._sel = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, boss in enumerate(_BOSSES):
                if self._row_rect(i).collidepoint(event.pos) and boss["unlocked"]:
                    return boss["action"]
        return None

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        self._parallax.update(dt)
        for e in self._embers:
            e.update(dt)
        self._preview.update(dt, self._sel)

    # ── Draw helpers ──────────────────────────────────────────────────────────

    def _draw_left_panel(self, screen: pygame.Surface) -> None:
        boss     = _BOSSES[self._sel]
        unlocked = boss["unlocked"]
        px, py   = _BS_LP_X, _BS_PANEL_Y
        pw, ph   = _BS_LP_W, _BS_PANEL_H

        # Panel background
        bg  = (35, 20, 5, 222) if unlocked else (14, 9, 6, 210)
        brd = (188, 148, 52)   if unlocked else (52, 42, 30)
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, bg,  (0, 0, pw, ph), border_radius=10)
        pygame.draw.rect(panel, brd, (0, 0, pw, ph), 2, border_radius=10)
        if unlocked:
            shine = pygame.Surface((pw - 8, 3), pygame.SRCALPHA)
            shine.fill((245, 190, 38, 40))
            panel.blit(shine, (4, 4))
        screen.blit(panel, (px, py))

        # Animated sprite (upper ~58% of panel)
        spr_cx = px + pw // 2
        spr_cy = py + int(ph * 0.38)
        self._preview.draw(screen, spr_cx, spr_cy, self._sel, unlocked)

        # Separator
        sep_y = py + int(ph * 0.68)
        pygame.draw.line(screen, brd, (px + 18, sep_y), (px + pw - 18, sep_y), 1)

        # Boss name
        name_col = (255, 215, 80) if unlocked else (75, 62, 46)
        name     = self._fp.render(boss["name"], True, name_col)
        screen.blit(name, name.get_rect(centerx=spr_cx, top=sep_y + 10))

        # Subtitle
        sub_col = (155, 125, 65) if unlocked else (52, 44, 34)
        sub     = self._fl.render(boss["sub"], True, sub_col)
        screen.blit(sub, sub.get_rect(centerx=spr_cx, top=sep_y + 30))

        # Lore line
        if boss.get("lore"):
            lore = self._fl.render(boss["lore"], True,
                                   (115, 92, 52) if unlocked else (48, 40, 30))
            screen.blit(lore, lore.get_rect(centerx=spr_cx, top=sep_y + 48))

        # Status badge
        bdg_y = sep_y + 70
        if unlocked:
            bdg = pygame.Surface((122, 18), pygame.SRCALPHA)
            bdg.fill((40, 110, 40, 175))
            pygame.draw.rect(bdg, (70, 185, 70), (0, 0, 122, 18), 1, border_radius=3)
            bt  = self._fl.render("DESBLOQUEADO", True, (140, 240, 140))
            bdg.blit(bt, bt.get_rect(center=(61, 9)))
        else:
            bdg = pygame.Surface((88, 18), pygame.SRCALPHA)
            bdg.fill((52, 38, 26, 155))
            pygame.draw.rect(bdg, (82, 62, 40), (0, 0, 88, 18), 1, border_radius=3)
            bt  = self._fl.render("EM BREVE", True, (112, 92, 62))
            bdg.blit(bt, bt.get_rect(center=(44, 9)))
        screen.blit(bdg, bdg.get_rect(centerx=spr_cx, top=bdg_y))

    def _draw_right_panel(self, screen: pygame.Surface) -> None:
        px, py = _BS_RP_X, _BS_PANEL_Y
        pw, ph = _BS_RP_W, _BS_PANEL_H

        # Subtle panel tint
        bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        bg.fill((8, 5, 2, 135))
        pygame.draw.rect(bg, (42, 30, 8), (0, 0, pw, ph), 1, border_radius=8)
        screen.blit(bg, (px, py))

        for i, boss in enumerate(_BOSSES):
            self._draw_row(screen, i, boss, i == self._sel)

    def _draw_row(self, screen: pygame.Surface, i: int, boss: dict,
                  selected: bool) -> None:
        rect     = self._row_rect(i)
        unlocked = boss["unlocked"]

        if selected and unlocked:
            bg, brd = (52, 32, 5, 232), (245, 190, 38)
        elif selected:
            bg, brd = (30, 20, 12, 212), (115, 90, 50)
        elif unlocked:
            bg, brd = (28, 18, 4, 200),  (105, 78, 18)
        else:
            bg, brd = (16, 11, 7, 185),  (46, 36, 26)

        row = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(row, bg,  (0, 0, rect.w, rect.h), border_radius=7)
        pygame.draw.rect(row, brd, (0, 0, rect.w, rect.h), 2, border_radius=7)

        # Left accent stripe
        stripe = (200, 155, 35, 200) if (unlocked and selected) else \
                 (128,  98, 20, 155) if unlocked else (48, 38, 26, 110)
        pygame.draw.rect(row, stripe, (0, 6, 4, rect.h - 12), border_radius=2)

        screen.blit(row, rect)

        # Number badge  (#1, #2 …)
        num_col = (220, 175, 45) if (unlocked and selected) else \
                  (145, 115, 35) if unlocked else (58, 48, 36)
        num = self._fnum.render(f"#{i+1}", True, num_col)
        screen.blit(num, num.get_rect(center=(rect.x + 22, rect.centery)))

        # Boss name
        tx = rect.x + 50
        nc = (255, 215, 80) if (unlocked and selected) else \
             (195, 158, 62) if unlocked else (68, 56, 40)
        name_surf = self._fn.render(boss["name"], True, nc)
        screen.blit(name_surf, (tx, rect.y + 18))

        # Subtitle
        sc = (145, 118, 58) if unlocked else (50, 42, 32)
        sub_surf = self._fs.render(boss["sub"], True, sc)
        screen.blit(sub_surf, (tx, rect.y + 44))

        # Right indicator — arrow if selected, lock if locked
        if selected:
            ax  = rect.right - 18
            ay  = rect.centery
            pts = [(ax, ay), (ax - 9, ay - 6), (ax - 9, ay + 6)]
            pygame.draw.polygon(screen, brd, pts)
        elif not unlocked:
            lk = self._fs.render("[LOCK]", True, (55, 46, 34))
            screen.blit(lk, lk.get_rect(midright=(rect.right - 14, rect.centery)))

    # ── Main draw ─────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface) -> None:
        self._parallax.draw(screen)

        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 115))
        screen.blit(ov, (0, 0))

        for e in self._embers:
            e.draw(screen)

        cx    = SCREEN_WIDTH // 2
        title = self._ft.render("SELECIONAR BATALHA", True, (210, 165, 52))
        screen.blit(title, title.get_rect(center=(cx, 54)))
        pygame.draw.line(screen, (130, 90, 20), (cx - 215, 78), (cx + 215, 78), 1)

        self._draw_left_panel(screen)
        self._draw_right_panel(screen)

        hint = self._fh.render(
            "↑↓  Navegar     Enter  Selecionar     ESC  Voltar",
            True, (90, 75, 40))
        screen.blit(hint, hint.get_rect(center=(cx, SCREEN_HEIGHT - 16)))
