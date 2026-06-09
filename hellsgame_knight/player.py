"""
player.py — Knight Warrior (FreeKnight v1).

Controls
--------
  ← →        move
  SPACE / ↑  jump
  Z          attack
  X          roll (rolamento com i-frames)

SPRITES (FreeKnight 120x80 sheets — Colour1/NoOutline)
------------------------------------------------------
  _Idle.png            — 10 frames (1200x80)
  _Run.png             — 10 frames (1200x80)
  _Jump.png            —  3 frames  (360x80)
  _Fall.png            —  3 frames  (360x80)
  _AttackCombo.png     — 10 frames (1200x80)
  _Roll.png            — 12 frames (1440x80)  ← rolamento completo
  _Hit.png             —  1 frame   (120x80)
  _Death.png           — 10 frames (1200x80)

Hitbox: centralizado no knight, ajustado para tamanho visual real.
Escala: knight exibido em ~2.4x (120→~192px wide, 80→~128px tall)
para ficar proporcional ao cenário de 960x540.
"""

import pygame
import os
import math
from settings import *
from analytics import tracker as combat_tracker
from magic_projectile import load_projectile_icon, PROJ_COOLDOWN

# ── Caminhos dos sprites ──────────────────────────────────────────────────────
KNIGHT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "knight")

def knight_sheet(name: str) -> str:
    return os.path.join(KNIGHT_DIR, name)

# ── Tamanho do frame original do knight ──────────────────────────────────────
KNIGHT_FRAME_W = 120
KNIGHT_FRAME_H = 80

# ── Escala de exibição ────────────────────────────────────────────────────────
KNIGHT_SCALE   = 2.4
DISPLAY_W = int(KNIGHT_FRAME_W * KNIGHT_SCALE)   # 288
DISPLAY_H = int(KNIGHT_FRAME_H * KNIGHT_SCALE)   # 192

# ── Hitbox ────────────────────────────────────────────────────────────────────
HB_W = 44
HB_H = 88

# Durante o roll a hitbox encolhe verticalmente (personagem agachado)
ROLL_HB_H = 48   # hitbox reduzida no roll — permite passar sob projéteis

SPRITE_FOOT_PAD = 0

# ── Duração das ações ─────────────────────────────────────────────────────────
ATTACK_DURATION    = 0.42
JUMP_ANIM_DURATION = 0.30
ROLL_DURATION      = 0.45    # duração total do rolamento (12 frames)
ROLL_SPEED         = 420     # velocidade horizontal durante o roll (px/s)
ROLL_COOLDOWN_TIME = 0.9     # cooldown entre rolls

POTION_HEAL          = 1     # HP por poção
POTION_COOLDOWN_TIME = 0.5   # cooldown entre usos (s)
_HUD_HEART_SIZE      = 36    # tamanho dos corações no HUD (px)

# ── Pasta de assets de HUD ────────────────────────────────────────────────────
_HODS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "hods", "hods")


def _load_knight_sheet(filename: str, num_frames: int) -> list[pygame.Surface]:
    """Carrega um spritesheet do knight, retorna lista de frames escalados."""
    path = knight_sheet(filename)
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except Exception as e:
        print(f"[knight] ERRO ao carregar {path}: {e}", flush=True)
        surf = pygame.Surface((DISPLAY_W, DISPLAY_H), pygame.SRCALPHA)
        pygame.draw.rect(surf, (180, 30, 200), (10, 10, DISPLAY_W-20, DISPLAY_H-20), 3)
        return [surf] * num_frames

    sw, sh = sheet.get_size()
    fw = sw // num_frames

    frames = []
    for i in range(num_frames):
        frame = sheet.subsurface(pygame.Rect(i * fw, 0, fw, sh))
        scaled = pygame.transform.scale(frame, (DISPLAY_W, DISPLAY_H))
        frames.append(scaled)

    print(f"[knight] {filename}: {num_frames} frames ({sw}x{sh} -> {DISPLAY_W}x{DISPLAY_H})", flush=True)
    return frames


def _flip_frames(frames: list[pygame.Surface]) -> list[pygame.Surface]:
    return [pygame.transform.flip(f, True, False) for f in frames]


def _build_heart(size: int, full: bool) -> pygame.Surface:
    """Coração pixel-art para o HUD de HP."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    if full:
        base = (210, 38, 38)
        hi   = (255, 108, 108)
        sh   = (130, 15, 15)
    else:
        base = (52, 18, 18)
        hi   = (70, 28, 28)
        sh   = (25,  8,  8)

    r  = max(2, size // 4)
    cx = size // 2
    ty = size // 3

    pygame.draw.circle(surf, base, (cx - r + 1, ty), r)
    pygame.draw.circle(surf, base, (cx + r - 1, ty), r)
    pygame.draw.polygon(surf, base, [(1, ty), (size - 1, ty), (cx, size - 2)])

    if full:
        pygame.draw.circle(surf, hi, (cx - r + 2, ty - r // 2 - 1), max(1, r // 2))
        pygame.draw.line(surf, sh, (cx - 2, size - 5), (cx + 2, size - 5))

    return surf


def _build_potion(w: int, h: int) -> pygame.Surface:
    """Frasco de poção pixel-art."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    cork_c  = (155, 105, 50)
    neck_c  = (135, 185, 205)
    body_c  = (75,  40, 150)
    liq_c   = (55, 120, 240)
    shine_c = (120, 78, 195)
    ref_c   = (195, 225, 240)

    # Rolha
    pygame.draw.rect(surf, cork_c, (w // 2 - 2, 0, 5, 4))
    # Pescoço
    nx, nw = w // 2 - w // 7, w // 3 + 1
    nh = max(4, h // 4)
    pygame.draw.rect(surf, neck_c, (nx, 3, nw, nh))
    # Corpo
    by = 3 + nh - 2
    pygame.draw.ellipse(surf, body_c, (0, by, w, h - by))
    # Líquido
    ly = by + (h - by) // 3
    lh = (h - by) * 2 // 3
    pygame.draw.ellipse(surf, liq_c, (2, ly, w - 4, lh - 2))
    # Brilho pescoço
    pygame.draw.rect(surf, ref_c, (nx + 1, 4, max(1, nw // 2 - 1), max(1, nh - 2)))
    # Brilho corpo
    pygame.draw.ellipse(surf, shine_c, (3, by + 3, w // 3, (h - by) // 4))

    return surf


def _build_key_icon(ch: str, sz: int) -> pygame.Surface:
    """Ícone de tecla pixel-art (ex: [C])."""
    surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
    pygame.draw.rect(surf, (155, 150, 160), (0, 0, sz, sz), border_radius=3)
    pygame.draw.rect(surf, (50,  47,  55),  (1, 1, sz - 2, sz - 2), border_radius=2)
    font = pygame.font.SysFont("monospace", max(8, sz - 6), bold=True)
    lbl  = font.render(ch, True, (205, 200, 212))
    surf.blit(lbl, lbl.get_rect(center=(sz // 2, sz // 2)))
    return surf


def _load_lightning_icon_sprite() -> pygame.Surface:
    """Carrega o ícone do Raio Divino de assets/raio/."""
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "assets", "raio", "Thunder Effect 02", "Thunder Strike", "icone_raio.png"
    )
    try:
        surf = pygame.image.load(path).convert_alpha()
        surf = pygame.transform.scale(surf, (26, 26))
        print(f"[knight] ícone raio carregado: {path}", flush=True)
        return surf
    except Exception as e:
        print(f"[knight] ERRO ícone raio: {e}", flush=True)
        fb = pygame.Surface((26, 26), pygame.SRCALPHA)
        pts = [(13,0),(4,13),(11,13),(7,26),(22,10),(15,10)]
        pygame.draw.polygon(fb, (255, 220, 0), pts)
        return fb


def _load_hud_sprite(filename: str, size=None, crop=None) -> pygame.Surface:
    """Carrega PNG de HUD com crop e escala opcionais.
    crop = (x, y, w, h) em coordenadas do PNG original.
    """
    path = os.path.join(_HODS_DIR, filename)
    try:
        surf = pygame.image.load(path).convert_alpha()
        if crop is not None:
            surf = surf.subsurface(pygame.Rect(*crop))
        if size is not None:
            surf = pygame.transform.scale(surf, size)
        return surf
    except Exception as e:
        print(f"[hud] ERRO ao carregar {path}: {e}", flush=True)
        w, h = size if size else (32, 32)
        fallback = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(fallback, (255, 0, 255), (0, 0, w, h), 2)
        return fallback


def _build_stamina_icon(size: int) -> pygame.Surface:
    """Relâmpago pixel-art para o ícone de estamina."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    s    = size
    pts  = [
        (int(s * 0.55), 0),
        (int(s * 0.18), int(s * 0.52)),
        (int(s * 0.44), int(s * 0.52)),
        (int(s * 0.44), s - 1),
        (int(s * 0.82), int(s * 0.44)),
        (int(s * 0.56), int(s * 0.44)),
    ]
    pygame.draw.polygon(surf, (55, 90, 130), pts)
    inner = [(int(x * 0.80 + s * 0.10), int(y * 0.80 + s * 0.10)) for x, y in pts]
    pygame.draw.polygon(surf, (165, 225, 255), inner)
    return surf


class Player(pygame.sprite.Sprite):

    def __init__(self, x: int, y: int):
        super().__init__()

        # ── Carregar todos os spritesheets do knight ──────────────────────
        idle_frames   = _load_knight_sheet("_Idle.png",        10)
        run_frames    = _load_knight_sheet("_Run.png",         10)
        jump_frames   = _load_knight_sheet("_Jump.png",         3)
        fall_frames   = _load_knight_sheet("_Fall.png",         3)
        attack_frames = _load_knight_sheet("_AttackCombo.png", 10)
        roll_frames   = _load_knight_sheet("_Roll.png",        12)
        hurt_frames   = _load_knight_sheet("_Hit.png",          1)
        death_frames  = _load_knight_sheet("_Death.png",       10)

        self.animations = {
            "idle":   idle_frames,
            "run":    run_frames,
            "jump":   jump_frames,
            "fall":   fall_frames,
            "attack": attack_frames,
            "roll":   roll_frames,
            "hurt":   hurt_frames,
            "death":  death_frames,
        }
        self.animations_left = {k: _flip_frames(v) for k, v in self.animations.items()}

        # ── Estado ────────────────────────────────────────────────────────
        self.state       = "idle"
        self._anim_state = "idle"
        self.facing      = 1
        self.frame_index = 0
        self.anim_timer  = 0.0
        self.anim_speed  = 0.08

        # ── Ataque ────────────────────────────────────────────────────────
        self.is_attacking         = False
        self.attack_finished      = False
        self.attack_timer         = 0.0
        self.attack_hit_enemies: set = set()
        self._attack_key_was_down = False

        # ── Roll ──────────────────────────────────────────────────────────
        self.is_rolling      = False
        self.roll_timer      = 0.0
        self.roll_cooldown   = 0.0
        self._roll_key_was_down = False

        # ── Poção ─────────────────────────────────────────────────────────
        self.potions          = 3
        self.max_potions      = 3
        self.potion_cooldown  = 0.0
        self._potion_key_down = False

        # ── HUD sprites (carregados de assets/hods/hods/) ─────────────────
        # Corações: rows de 6 corações (1224×182 visível dentro de 1536×1024)
        _HR_H = 36
        _HR_W = int(1224 * _HR_H / 182)   # ≈ 242px
        self._hud_hearts_full  = _load_hud_sprite(
            "coraçao_cheio.png",  size=(_HR_W, _HR_H), crop=(156, 382, 1224, 182))
        self._hud_hearts_empty = _load_hud_sprite(
            "coraçao_vazio.png",  size=(_HR_W, _HR_H), crop=(163, 380, 1212, 177))
        # Barra de estamina (870×114 visível → mesma largura da row de corações)
        self._hud_stam_bar = _load_hud_sprite(
            "barra_stamina.png",  size=(_HR_W, 22),    crop=(336, 437, 870, 114))
        # Poções: 4 sprites (x0=vazio → x3=3 doses) — o sprite já mostra a quantidade
        _POT_SZ = (64, 54)
        self._hud_potions = [
            _load_hud_sprite("poçoes_cura_x0.png", size=_POT_SZ, crop=(403, 184, 731, 627)),
            _load_hud_sprite("poçoes_cura_x1.png", size=_POT_SZ, crop=(368, 176, 800, 663)),
            _load_hud_sprite("poçoes_cura_x2.png", size=_POT_SZ, crop=(408, 211, 724, 617)),
            _load_hud_sprite("poçoes_cura_x3.png", size=_POT_SZ, crop=(376, 186, 784, 657)),
        ]

        # ── Raio Divino ───────────────────────────────────────────────────
        self.lightning_charges       = 2      # cargas por batalha
        self.lightning_pending       = False  # consumido por game.py no mesmo frame
        self._lightning_key_was_down = False
        self._hud_lightning_icon     = self._load_lightning_icon()
        self._hud_font_small         = pygame.font.SysFont("monospace", 13, bold=True)

        # ── Projetil Magico ───────────────────────────────────────────────
        self.projectile_cooldown  = 0.0    # countdown em segundos (0 = disponivel)
        self.projectile_pending   = False  # consumido por game.py no mesmo frame
        self._proj_key_was_down   = False
        self._proj_attack_pending = False  # True: ataque F em andamento, projetil dispara ao fim
        self._hud_proj_icon       = load_projectile_icon((28, 28))

        # ── Hurt / Hitstun ────────────────────────────────────────────────
        self.is_hurt          = False
        self.hurt_timer       = 0.0
        self.invincible_timer = 0.0
        self.hitstun_timer    = 0.0   # trava input por 0.65s após tomar dano

        # ── Física ────────────────────────────────────────────────────────
        self.vel_x     = 0.0
        self.vel_y     = 0.0
        self.on_ground = False

        # ── HP ────────────────────────────────────────────────────────────
        self.hp     = 6
        self.max_hp = 6

        # ── Hitbox e rect ─────────────────────────────────────────────────
        self.hitbox = pygame.Rect(0, 0, HB_W, HB_H)
        self.hitbox.midbottom = (x, y)

        self.image = self._current_frame()
        self.rect  = self.image.get_rect()
        self._align_rect()

        print("[knight] Player inicializado com sucesso! (roll ativo)", flush=True)

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE
    # ─────────────────────────────────────────────────────────────────────────

    def update(self, keys, dt: float, platforms):
        self.attack_timer        = max(0.0, self.attack_timer        - dt)
        self.invincible_timer    = max(0.0, self.invincible_timer    - dt)
        self.hitstun_timer       = max(0.0, self.hitstun_timer       - dt)
        self.roll_cooldown       = max(0.0, self.roll_cooldown       - dt)
        self.roll_timer          = max(0.0, self.roll_timer          - dt)
        self.potion_cooldown     = max(0.0, self.potion_cooldown     - dt)
        self.projectile_cooldown = max(0.0, self.projectile_cooldown - dt)

        if self.is_hurt:
            self.hurt_timer = max(0.0, self.hurt_timer - dt)
            if self.hurt_timer <= 0.0:
                self.is_hurt = False

        # Liberar ataque quando animação completou
        if self.is_attacking and self.attack_finished:
            self.is_attacking    = False
            self.attack_finished = False
            self.attack_hit_enemies.clear()

        # Liberar roll quando o timer acabou
        if self.is_rolling and self.roll_timer <= 0.0:
            self.is_rolling = False
            # Restaurar hitbox normal
            bottom = self.hitbox.bottom
            self.hitbox.height = HB_H
            self.hitbox.bottom = bottom

        self._handle_input(keys, dt)
        self._physics(dt, platforms)
        self._animate(dt)

    # ─────────────────────────────────────────────────────────────────────────
    # INPUT
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_input(self, keys, dt: float):
        # Hitstun: trava todo input por 0.65s após tomar dano
        if self.hitstun_timer > 0:
            self.vel_x = 0.0
            self._roll_key_was_down      = bool(keys[pygame.K_x])
            self._attack_key_was_down    = bool(keys[pygame.K_z])
            self._potion_key_down        = bool(keys[pygame.K_c])
            self._lightning_key_was_down = bool(keys[pygame.K_v])
            self._proj_key_was_down      = bool(keys[pygame.K_f])
            return

        # POÇÃO (C) — bloqueada durante hitstun
        c_down = bool(keys[pygame.K_c])
        if c_down and not self._potion_key_down and self.potion_cooldown <= 0:
            self._use_potion()
        self._potion_key_down = c_down

        x_down = bool(keys[pygame.K_x])

        # ROLL — só no chão, não durante ataque, com cooldown
        if (x_down and not self._roll_key_was_down
                and self.on_ground
                and self.roll_cooldown <= 0.0
                and not self.is_rolling
                and not self.is_attacking):
            self._start_roll()

        self._roll_key_was_down = x_down

        # Durante o roll: movimento forçado, i-frames ativos — bloqueia todo resto
        if self.is_rolling:
            self.vel_x = ROLL_SPEED * self.facing
            return

        # MOVIMENTO normal
        if not self.is_attacking:
            if keys[pygame.K_LEFT]:
                self.vel_x  = -PLAYER_SPEED
                self.facing = -1
            elif keys[pygame.K_RIGHT]:
                self.vel_x  =  PLAYER_SPEED
                self.facing =  1
            else:
                self.vel_x = 0.0

        # PULO
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP]) and self.on_ground:
            self.vel_y     = JUMP_SPEED
            self.on_ground = False
            combat_tracker.log_event("jumps")

        # RAIO DIVINO (V) — ativa se houver cargas disponíveis
        v_down = bool(keys[pygame.K_v])
        if v_down and not self._lightning_key_was_down and self.lightning_charges > 0:
            self.lightning_charges      -= 1
            self.lightning_pending       = True
            print(f"[knight] Raio Divino! Cargas restantes: {self.lightning_charges}", flush=True)
        self._lightning_key_was_down = v_down

        # PROJETIL MAGICO (F) — dispara imediatamente e inicia animacao de ataque
        f_down = bool(keys[pygame.K_f])
        if (f_down and not self._proj_key_was_down
                and self.projectile_cooldown <= 0
                and not self.is_attacking
                and not self.is_rolling):
            self.projectile_cooldown = PROJ_COOLDOWN
            self.projectile_pending  = True          # disparo imediato
            self.is_attacking    = True
            self.attack_finished = False
            self.attack_timer    = ATTACK_DURATION
            self.frame_index     = 0
            self.anim_timer      = 0.0
            self.attack_hit_enemies.clear()
        self._proj_key_was_down = f_down

        # ATAQUE (Z) — bloqueado durante roll
        z_down = bool(keys[pygame.K_z])
        if z_down and not self._attack_key_was_down and not self.is_attacking:
            self.is_attacking    = True
            self.attack_finished = False
            self.attack_timer    = ATTACK_DURATION
            self.frame_index     = 0
            self.anim_timer      = 0.0
            self.attack_hit_enemies.clear()
        self._attack_key_was_down = z_down

    def _load_lightning_icon(self) -> pygame.Surface:
        return _load_lightning_icon_sprite()

    def _start_roll(self):
        self.is_rolling   = True
        self.roll_timer   = ROLL_DURATION
        self.roll_cooldown = ROLL_COOLDOWN_TIME
        # I-frames durante todo o roll
        self.invincible_timer = ROLL_DURATION
        # Hitbox reduzida (personagem agachado durante o roll)
        bottom = self.hitbox.bottom
        self.hitbox.height = ROLL_HB_H
        self.hitbox.bottom = bottom
        # Reset frame da animação
        self.frame_index = 0
        self.anim_timer  = 0.0
        combat_tracker.log_event("rolls")
        print("[knight] roll!", flush=True)

    # ─────────────────────────────────────────────────────────────────────────
    # FÍSICA
    # ─────────────────────────────────────────────────────────────────────────

    def _physics(self, dt: float, platforms):
        was_on_ground = self.on_ground

        if not was_on_ground and not self.is_rolling:
            self.vel_y += GRAVITY * dt
            self.vel_y  = min(self.vel_y, 900)

        self.hitbox.x += round(self.vel_x * dt)
        self._resolve_x(platforms)

        self.on_ground = False
        dy = round(self.vel_y * dt)
        if was_on_ground and dy == 0:
            dy = 1
        self.hitbox.y += dy
        self._resolve_y(platforms)

        self._align_rect()

    def _resolve_x(self, platforms):
        for plat in platforms:
            if getattr(plat, 'one_way', False):
                continue
            pr = plat.solid_rect
            if not self.hitbox.colliderect(pr):
                continue
            if self.vel_x > 0:
                self.hitbox.right = pr.left
            elif self.vel_x < 0:
                self.hitbox.left  = pr.right
            self.vel_x = 0.0

    def _resolve_y(self, platforms):
        for plat in platforms:
            pr = plat.solid_rect
            if not self.hitbox.colliderect(pr):
                continue
            if self.vel_y >= 0:
                self.hitbox.bottom = pr.top
                self.vel_y         = 0.0
                self.on_ground     = True
            elif not getattr(plat, 'one_way', False):
                self.hitbox.top = pr.bottom
                self.vel_y      = 0.0

    def _align_rect(self):
        self.rect.midbottom = (
            self.hitbox.centerx,
            self.hitbox.bottom + SPRITE_FOOT_PAD
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ANIMAÇÃO
    # ─────────────────────────────────────────────────────────────────────────

    def _animate(self, dt: float):
        # Determinar estado visual (prioridade decrescente)
        if self.is_rolling:
            new_state = "roll"
        elif self.is_attacking:
            new_state = "attack"
        elif self.is_hurt:
            new_state = "hurt"
        elif not self.on_ground:
            new_state = "fall" if self.vel_y > 50 else "jump"
        elif abs(self.vel_x) > 10:
            new_state = "run"
        else:
            new_state = "idle"

        # Reset de frame quando estado muda
        if new_state != self._anim_state:
            self._anim_state = new_state
            self.frame_index = 0
            self.anim_timer  = 0.0

        self.state = self._anim_state

        frames = self._get_anim()
        if not frames:
            return

        # SPF por estado
        if self.state == "attack":
            spf = ATTACK_DURATION / max(len(frames), 1)
        elif self.state == "roll":
            spf = ROLL_DURATION / max(len(frames), 1)
        elif self.state in ("jump", "fall"):
            spf = JUMP_ANIM_DURATION / max(len(frames), 1)
        elif self.state == "hurt":
            spf = 0.08
        else:
            spf = self.anim_speed   # idle/run: loop a 0.08s/frame

        self.anim_timer += dt
        if self.anim_timer >= spf:
            self.anim_timer -= spf

            if self.state in ("attack", "roll"):
                # One-shot: avança até o último e trava
                if self.frame_index < len(frames) - 1:
                    self.frame_index += 1
                    if self.frame_index == len(frames) - 1 and self.state == "attack":
                        self.attack_finished = True
            elif self.state in ("jump", "fall", "hurt"):
                if self.frame_index < len(frames) - 1:
                    self.frame_index += 1
            else:
                # idle/run: loop
                self.frame_index = (self.frame_index + 1) % len(frames)

        self.image = frames[self.frame_index]

    def _get_anim(self) -> list:
        bank = self.animations if self.facing == 1 else self.animations_left
        return bank.get(self.state, bank["idle"])

    def _current_frame(self) -> pygame.Surface:
        frames = self._get_anim()
        return frames[self.frame_index % len(frames)]

    # ─────────────────────────────────────────────────────────────────────────
    # COMBAT
    # ─────────────────────────────────────────────────────────────────────────

    def get_attack_rect(self) -> pygame.Rect | None:
        if not self.is_attacking:
            return None
        reach = 80
        if self.facing == 1:
            ax = self.hitbox.right
        else:
            ax = self.hitbox.left - reach
        return pygame.Rect(ax, self.hitbox.centery - 30, reach, 55)

    def take_damage(self, amount: int = 1):
        # is_rolling: proteção explícita independente do timer
        if self.invincible_timer > 0 or self.is_rolling:
            return
        self.hp -= amount
        self.invincible_timer = 0.9
        self.hitstun_timer    = 0.65   # bloqueia input por 0.65s (< i-frames 0.9s)
        self.is_hurt          = True
        self.hurt_timer       = 0.25
        # Cancela ações em andamento
        self.is_attacking    = False
        self.attack_finished = False
        self.is_rolling      = False
        self.roll_timer      = 0.0
        self.vel_x           = 0.0
        combat_tracker.log_event("damage_taken", amount)

    def _use_potion(self):
        if self.potions <= 0 or self.hp >= self.max_hp:
            return
        self.potions        -= 1
        self.hp              = min(self.hp + POTION_HEAL, self.max_hp)
        self.potion_cooldown = POTION_COOLDOWN_TIME
        combat_tracker.log_event("potions")
        print(f"[player] poção! HP={self.hp}/{self.max_hp} poções={self.potions}", flush=True)

    @property
    def alive(self) -> bool:
        return self.hp > 0

    # ─────────────────────────────────────────────────────────────────────────
    # DRAW
    # ─────────────────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface):
        # Trail fantasma durante o roll (antes do sprite para ficar atrás)
        if self.is_rolling:
            offset = -38 * self.facing
            ghost = self.image.copy()
            # BLEND_RGBA_MULT multiplica alpha pixel a pixel — sem retângulo
            ghost.fill((255, 255, 255, 55), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(ghost, (self.rect.x + offset, self.rect.y))
            ghost2 = self.image.copy()
            ghost2.fill((255, 255, 255, 25), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(ghost2, (self.rect.x + offset * 2, self.rect.y))

        if self.invincible_timer > 0:
            if int(self.invincible_timer * 8) % 2:
                flash = self.image.copy()
                # BLEND_RGB_ADD afeta só RGB, preserva alpha original — sem retângulo
                flash.fill((120, 120, 120), special_flags=pygame.BLEND_RGB_ADD)
                screen.blit(flash, self.rect)
            else:
                screen.blit(self.image, self.rect)
        else:
            screen.blit(self.image, self.rect)

    def draw_hud(self, screen: pygame.Surface):
        hx, hy = 12, 10

        # ── Corações de vida (topo esquerdo) ──────────────────────────────
        hw = self._hud_hearts_full.get_width()
        hh = self._hud_hearts_full.get_height()
        # Base: todos os slots vazios
        screen.blit(self._hud_hearts_empty, (hx, hy))
        # Overlay: corações cheios clipados ao HP atual
        if self.hp > 0:
            fill_w = int(hw * min(self.hp, self.max_hp) / self.max_hp)
            screen.blit(self._hud_hearts_full, (hx, hy), area=pygame.Rect(0, 0, fill_w, hh))

        # ── Barra de estamina (abaixo dos corações) ───────────────────────
        sb_w, sb_h = self._hud_stam_bar.get_size()
        stam_y = hy + hh + 8

        # Trilho escuro (fundo quando vazio)
        track = pygame.Surface((sb_w, sb_h), pygame.SRCALPHA)
        track.fill((10, 12, 20, 210))
        screen.blit(track, (hx, stam_y))

        # Sprite de preenchimento clipado ao ratio de cooldown
        ready  = max(0.0, 1.0 - self.roll_cooldown / ROLL_COOLDOWN_TIME)
        fill_w = int(sb_w * ready)
        if fill_w > 0:
            screen.blit(self._hud_stam_bar, (hx, stam_y), area=pygame.Rect(0, 0, fill_w, sb_h))

        # Borda sutil ao redor da barra
        pygame.draw.rect(screen, (55, 65, 90), (hx - 1, stam_y - 1, sb_w + 2, sb_h + 2), 1)

        # ── Raio Divino (abaixo da barra de estamina) ────────────────────────
        lightning_y = stam_y + sb_h + 10
        icon        = self._hud_lightning_icon
        iw, ih      = icon.get_size()

        if self.lightning_charges == 0:
            # Ícone apagado quando sem cargas
            dim = icon.copy()
            dim.fill((255, 255, 255, 65), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(dim, (hx, lightning_y))
        else:
            screen.blit(icon, (hx, lightning_y))

        charge_color = (255, 220, 0) if self.lightning_charges > 0 else (70, 70, 70)
        lbl = self._hud_font_small.render(f"x{self.lightning_charges}", True, charge_color)
        screen.blit(lbl, (hx + iw + 4, lightning_y + (ih - lbl.get_height()) // 2))

        # ── Tecla de dica ─────────────────────────────────────────────────
        if self.lightning_charges > 0:
            hint_font = self._hud_font_small
            hint = hint_font.render("[V]", True, (160, 140, 80))
            screen.blit(hint, (hx + iw + 4 + lbl.get_width() + 4,
                                lightning_y + (ih - hint.get_height()) // 2))

        # ── Poção (canto inferior direito) ────────────────────────────────
        pot_idx  = max(0, min(self.potions, len(self._hud_potions) - 1))
        pot_surf = self._hud_potions[pot_idx]
        pot_w, pot_h = pot_surf.get_size()
        margin = 16
        pot_x = SCREEN_WIDTH - pot_w - margin
        pot_y = SCREEN_HEIGHT - pot_h - margin
        screen.blit(pot_surf, (pot_x, pot_y))

        # ── Projetil Magico (à esquerda da poção) ─────────────────────────
        proj_surf        = self._hud_proj_icon
        proj_w, proj_h   = proj_surf.get_size()
        proj_x = pot_x - proj_w - 12
        proj_y = pot_y + (pot_h - proj_h) // 2

        if self.projectile_cooldown > 0:
            # Ícone escurecido durante o cooldown
            dim = proj_surf.copy()
            dim.fill((255, 255, 255, 60), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(dim, (proj_x, proj_y))
            # Contador regressivo acima do ícone
            secs    = math.ceil(self.projectile_cooldown)
            cd_lbl  = self._hud_font_small.render(str(secs), True, (180, 180, 180))
            screen.blit(cd_lbl, (
                proj_x + (proj_w - cd_lbl.get_width()) // 2,
                proj_y - cd_lbl.get_height() - 2,
            ))
        else:
            screen.blit(proj_surf, (proj_x, proj_y))

        # Tecla de dica [F]
        hint = self._hud_font_small.render("[F]", True, (140, 130, 90))
        screen.blit(hint, (
            proj_x + (proj_w - hint.get_width()) // 2,
            proj_y + proj_h + 2,
        ))
