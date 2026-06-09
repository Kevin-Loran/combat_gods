"""
night_boss.py — Night Guardian

Estrutura de assets (assets/noite_boss/):
    idle/  idle_1.png  …  idle_15.png   (15 frames, loop)
    fly/   fly_1.png   …  fly_6.png     ( 6 frames, loop)
    walk/  walk_1.png  …  walk_12.png   (12 frames, loop)
    atk_1/ 1atk_1.png …  1atk_7.png    ( 7 frames, 1 dano)
    atk_2/ 2atk_1.png …  2atk_9.png    ( 9 frames, 2 danos)
    hurt/  hurt_1.png  …  hurt_5.png    ( 5 frames, one-shot)
    death/ death_1.png …  death_11.png  (11 frames + fade-out)

Interface compatível com game.py (idêntica a MinotaurBoss):
    .hitbox             pygame.Rect
    .hp / .max_hp       int
    .is_dead            bool
    .should_be_removed  bool (property)
    .state              str
    .particles          ParticleSystem
    .update(dt, platforms, player)
    .take_damage(amount)
    .draw(screen)
    .draw_hud(screen)

State machine:
    idle  ──► fly    player entra em AGGRO_RANGE
    fly   ──► walk   player entra em STALK_RANGE
    walk  ──► atk    player entra em ATTACK_RANGE + cooldown livre
    atk   ──► walk   animação completa + recovery
    hurt  ──► walk   após HURT_DUR
    *     ──► death  hp == 0
"""

import pygame
import os
import math
import random
from particles import ParticleSystem

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────

_NB_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "assets", "noite_boss"
)


def _nb_path(subdir: str, filename: str) -> str:
    """Retorna o caminho completo: assets/noite_boss/{subdir}/{filename}"""
    return os.path.join(_NB_DIR, subdir, filename)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÕES — DISPLAY
# ─────────────────────────────────────────────────────────────────────────────

NB_SCALE = 2.2   # multiplicador de escala aplicado às dimensões brutas do sprite

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÕES — HITBOX
# ─────────────────────────────────────────────────────────────────────────────

NB_HB_W = 72
NB_HB_H = 100

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÕES — HP
# ─────────────────────────────────────────────────────────────────────────────

NB_MAX_HP = 25

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÕES — IA
# ─────────────────────────────────────────────────────────────────────────────

AGGRO_RANGE   = 620    # px — detecta o player e inicia perseguição
STALK_RANGE   = 220    # px — troca fly (rápido) por walk (cerco)
ATTACK_RANGE  = 125    # px — inicia ataque

# ── Movimento horizontal ───────────────────────────────────────────────────────
MOVE_H_SPEED  = 95.0   # px/s — lento e pesado, sem pressa
MOVE_H_ACCEL  = 2.8    # aceleração suave (ramp lenta = sensação de peso)
H_SNAP_THRESH = 36     # px — zona de repouso horizontal

# ── Movimento vertical ─────────────────────────────────────────────────────────
MOVE_V_LERP   = 1.1    # suavização vertical — deslizamento lento e deliberado
V_SNAP_THRESH = 20     # px — zona de repouso vertical

# ── Hover / bob ────────────────────────────────────────────────────────────────
BOB_IDLE_AMP = 2       # px — flutuação quase imperceptível quando parado
BOB_MOVE_AMP = 0       # px — sem balanço durante movimento
BOB_FREQ     = 0.45    # Hz — oscilação muito lenta (cinematográfica)

# ── Posicionamento ─────────────────────────────────────────────────────────────
PREFERRED_DIST       = 90    # px — distância horizontal mantida do player
HOVER_OFFSET         = -22   # px — boss flutua levemente acima do centro do player
GROUND_VISUAL_OFFSET = 35    # px — compensa 16px transparentes na base × escala 2.2 = 35px

# ── Pausa estratégica ──────────────────────────────────────────────────────────
REPOSITION_MIN = 1.4   # s — pausa mínima antes de novo reposicionamento
REPOSITION_MAX = 2.8   # s — pausa máxima (cria tensão e presença)

# ── Ciclo aéreo / terrestre ────────────────────────────────────────────────────
GROUND_SPEED      = 75.0   # px/s — velocidade de caminhada no chão
GROUND_ACCEL      = 5.0    # lerp de aceleração/desaceleração no chão
HOVER_HEIGHT      = -150   # px acima do chão — altitude padrão de voo (não perseguição)
LAND_THRESHOLD    = 15     # px — margem para confirmar pouso
PLATFORM_THRESHOLD = 80   # px — diferença Y mínima para considerar player elevado
PHASE_SWITCH_CD   = 2.0    # s — cooldown mínimo entre mudanças de fase

ATK2_CHANCE = 0.35   # probabilidade de escolher atk2 quando ambos disponíveis

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÕES — ANIMAÇÕES
# ─────────────────────────────────────────────────────────────────────────────

IDLE_SPF  = 0.10   # s/frame idle loop
FLY_SPF   = 0.09   # s/frame fly loop
WALK_SPF  = 0.09   # s/frame walk loop

ATK1_TOTAL = 0.80  # duração total atk1 (7 frames)
ATK1_HIT_F = 4     # frame de impacto, 1-indexed
ATK1_DMG   = 1     # dano em corações

ATK2_TOTAL = 1.25  # duração total atk2 (9 frames)
ATK2_HIT_F = 5     # frame de impacto
ATK2_DMG   = 2     # dano em corações

HURT_DUR    = 0.28  # duração total estado hurt
DEATH_TOTAL = 2.20  # duração animação de morte (11 frames)
FADE_DUR    = 1.00  # fade-out após animação completa

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÕES — COOLDOWNS / COMBATE
# ─────────────────────────────────────────────────────────────────────────────

ATK1_CD       = 1.4   # s — cooldown do ataque leve
ATK2_CD       = 3.0   # s — cooldown do ataque pesado
RECOVERY_ATK1 = 0.50  # s — janela de punição após atk1
RECOVERY_ATK2 = 0.80  # s — janela de punição após atk2
IFRAMES_DUR   = 0.38  # s — invencibilidade após cada hit
CONTACT_CD    = 1.20  # s — cooldown de dano por contato corporal


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS — CARREGAMENTO DE SPRITES
# ─────────────────────────────────────────────────────────────────────────────

def _load_anim(subdir: str, prefix: str, count: int) -> list[pygame.Surface]:
    """
    Carrega `count` frames de  assets/noite_boss/{subdir}/{prefix}_{i}.png
    e escala cada um por NB_SCALE.  Gera placeholder transparente se falhar.
    """
    frames: list[pygame.Surface] = []

    subdir_path = os.path.join(_NB_DIR, subdir)
    if not os.path.isdir(subdir_path):
        print(f"[night_boss] PASTA NAO ENCONTRADA: {subdir_path}", flush=True)

    for i in range(1, count + 1):
        fname = f"{prefix}_{i}.png"
        path  = os.path.join(subdir_path, fname)
        try:
            img = pygame.image.load(path).convert_alpha()
            raw_w, raw_h = img.get_size()
            disp_w = max(1, int(raw_w * NB_SCALE))
            disp_h = max(1, int(raw_h * NB_SCALE))
            frames.append(pygame.transform.scale(img, (disp_w, disp_h)))
        except Exception as e:
            print(f"[night_boss] ERRO ao carregar {subdir}/{fname}: {e}", flush=True)
            # Placeholder visível (magenta) para depuração visual
            ph = pygame.Surface((int(80 * NB_SCALE), int(80 * NB_SCALE)), pygame.SRCALPHA)
            ph.fill((200, 0, 200, 180))
            frames.append(ph)

    if frames:
        w, h = frames[0].get_size()
        print(
            f"[night_boss] '{subdir}/{prefix}': {len(frames)} frames  "
            f"{w}×{h}px  (scale={NB_SCALE}x)",
            flush=True,
        )
    return frames


def _flip_frames(frames: list[pygame.Surface]) -> list[pygame.Surface]:
    return [pygame.transform.flip(f, True, False) for f in frames]


def _tint_red(frame: pygame.Surface) -> pygame.Surface:
    """Tint vermelho preservando alpha (BLEND_RGB_ADD não toca canal alpha)."""
    result  = frame.copy()
    overlay = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
    overlay.fill((130, 0, 0, 0))
    result.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# CLASSE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class NightBoss(pygame.sprite.Sprite):
    """
    Night Guardian — boss voador da Night Town Arena.
    Usa TODOS os sprites de assets/noite_boss/ distribuídos em 7 animações.
    """

    def __init__(self, x: int, y: int):
        super().__init__()

        # ── Carregar TODOS os frames ──────────────────────────────────────
        #   subdir   prefix   count
        idle_r  = _load_anim("idle",  "idle",   15)
        fly_r   = _load_anim("fly",   "fly",     6)
        walk_r  = _load_anim("walk",  "walk",   12)
        atk1_r  = _load_anim("atk_1", "1atk",   7)
        atk2_r  = _load_anim("atk_2", "2atk",   9)
        hurt_r  = _load_anim("hurt",  "hurt",    5)
        death_r = _load_anim("death", "death",  11)

        # Orientação: originais → facing right (+1); flip → facing left (-1)
        self._anims_r: dict[str, list] = {
            "idle":  idle_r,
            "fly":   fly_r,
            "walk":  walk_r,
            "atk1":  atk1_r,
            "atk2":  atk2_r,
            "hurt":  hurt_r,
            "death": death_r,
        }
        self._anims_l: dict[str, list] = {
            k: _flip_frames(v) for k, v in self._anims_r.items()
        }

        # Frames pré-tintados para efeito de i-frames
        self._tint_r: dict[str, list] = {
            k: [_tint_red(f) for f in v] for k, v in self._anims_r.items()
        }
        self._tint_l: dict[str, list] = {
            k: _flip_frames(v) for k, v in self._tint_r.items()
        }

        # ── Partículas ────────────────────────────────────────────────────
        self.particles = ParticleSystem()

        # ── Estado ────────────────────────────────────────────────────────
        self.state       = "idle"
        self._anim_state = "idle"
        self.facing      = -1       # boss spawna à direita, olha para o player (esq.)
        self.frame_index = 0
        self.anim_timer  = 0.0
        self._bob_time   = 0.0

        # ── Ataque ────────────────────────────────────────────────────────
        self.is_attacking  = False
        self._atk_type     = 1       # 1 = light / 2 = heavy
        self._atk_finished = False
        self._atk_hit_done = False
        self._atk_vfx_done = False

        # ── Recovery (janela de punição após ataque) ──────────────────────
        self.is_recovering   = False
        self._recovery_timer = 0.0

        # ── Cooldowns ─────────────────────────────────────────────────────
        self._cd_atk1    = 0.0
        self._cd_atk2    = 0.0
        self._cd_contact = 0.0

        # ── Stun (Raio Divino) ────────────────────────────────────────────
        self.is_stunned = False
        self.stun_timer = 0.0

        # ── Hurt ──────────────────────────────────────────────────────────
        self.is_hurt          = False
        self._hurt_timer      = 0.0
        self.invincible_timer = 0.0

        # ── HP ────────────────────────────────────────────────────────────
        self.hp     = NB_MAX_HP
        self.max_hp = NB_MAX_HP

        # ── HUD ───────────────────────────────────────────────────────────
        self._hud_cache = None           # lazy-loaded na 1ª chamada de draw_hud
        self._hud_hp    = float(NB_MAX_HP)  # HP animado (drena suavemente)

        # ── Morte ─────────────────────────────────────────────────────────
        self.is_dead      = False
        self._death_timer = 0.0
        self.death_alpha  = 255

        # ── Física de voo — sistema de eixo único ─────────────────────────
        self.vel_x        = 0.0
        self._smooth_velx = 0.0   # velocidade horizontal suavizada (aceleração)
        self._base_y      = 0.0   # âncora Y estável (bob é somado sobre ela)
        self._target_x    = 0.0   # X desejado pela IA
        self._target_y    = 0.0   # Y desejado pela IA
        self._move_axis      = "none"  # "h" | "v" | "none" — eixo ativo no frame
        self._reposition_cd  = 0.0    # s — cooldown antes de escolher nova posição

        # ── Ciclo de fase (aerial ↔ grounded) ────────────────────────────
        self._phase          = "grounded"  # começa no chão
        self._phase_timer    = PHASE_SWITCH_CD  # cooldown antes da 1ª mudança
        self._is_grounded    = False     # True quando boss está no chão
        self._ground_y       = 0.0      # centery do boss quando pousado
        self._ground_y_ready = False    # calculado na 1ª chamada de _physics

        # ── Hitbox e rect ─────────────────────────────────────────────────
        self.hitbox = pygame.Rect(0, 0, NB_HB_W, NB_HB_H)
        self.hitbox.midbottom = (x, y)
        self._base_y   = float(self.hitbox.centery)
        self._target_x = float(self.hitbox.centerx)
        self._target_y = float(self.hitbox.centery)

        # Inicializa image/rect com o primeiro frame idle
        self.image = self._current_frame()
        self.rect  = self.image.get_rect()
        self._align_rect()

        print(
            f"[night_boss] NightBoss criado em ({x},{y}) | "
            f"hitbox={self.hitbox} | "
            f"rect={self.rect} | "
            f"HP={NB_MAX_HP} | scale={NB_SCALE}x",
            flush=True,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE PRINCIPAL
    # ─────────────────────────────────────────────────────────────────────────

    def update(self, dt: float, platforms, player, projectiles=None):
        # Ticks de cooldown
        self.invincible_timer = max(0.0, self.invincible_timer - dt)
        self._cd_atk1         = max(0.0, self._cd_atk1         - dt)
        self._cd_atk2         = max(0.0, self._cd_atk2         - dt)
        self._cd_contact      = max(0.0, self._cd_contact       - dt)
        self._reposition_cd   = max(0.0, self._reposition_cd    - dt)
        self._phase_timer     = max(0.0, self._phase_timer      - dt)
        self.stun_timer       = max(0.0, self.stun_timer         - dt)
        if self.stun_timer <= 0.0:
            self.is_stunned = False
        self._bob_time       += dt
        self.particles.update(dt)

        # Animação suave da barra de vida (drena a ~15% do max HP/s)
        if self._hud_hp > self.hp:
            self._hud_hp = max(float(self.hp), self._hud_hp - dt * self.max_hp * 0.15)
        else:
            self._hud_hp = float(self.hp)

        # Morte: apenas animação + fade
        if self.is_dead:
            self._update_death(dt)
            return

        # Hurt
        if self.is_hurt:
            self._hurt_timer -= dt
            if self._hurt_timer <= 0.0:
                self.is_hurt = False

        # Fim de ataque → recovery
        if self.is_attacking and self._atk_finished:
            rec = RECOVERY_ATK1 if self._atk_type == 1 else RECOVERY_ATK2
            self.is_attacking    = False
            self._atk_finished   = False
            self._atk_hit_done   = False
            self.is_recovering   = True
            self._recovery_timer = rec
            self.vel_x           = 0.0
            self.state           = "idle"
            self.particles.emit_recovery(self.hitbox.centerx, self.hitbox.bottom)

        # Recovery: boss parado (janela de punição para o player)
        if self.is_recovering:
            self._recovery_timer -= dt
            self.vel_x = 0.0
            if self._recovery_timer <= 0.0:
                self.is_recovering = False

        # Stun (Raio Divino): imobiliza o boss completamente
        if self.is_stunned:
            self.vel_x        = 0.0
            self._smooth_velx = 0.0

        # IA — bloqueada durante hurt, ataque, recovery e stun
        if not self.is_hurt and not self.is_attacking and not self.is_recovering and not self.is_stunned:
            self._run_ai(player)

        # Física de voo
        self._physics(dt, platforms, player)

        # Dano sincronizado com frame de impacto
        if self.is_attacking and not self._atk_hit_done:
            hit_f = ATK1_HIT_F if self._atk_type == 1 else ATK2_HIT_F
            if self.frame_index >= hit_f - 1:
                dmg      = ATK1_DMG if self._atk_type == 1 else ATK2_DMG
                atk_rect = self._get_attack_rect()
                if atk_rect and player.alive and atk_rect.colliderect(player.hitbox):
                    player.take_damage(dmg)
                self._atk_hit_done = True

        # VFX no frame de impacto
        if self.is_attacking and not self._atk_vfx_done:
            hit_f = ATK1_HIT_F if self._atk_type == 1 else ATK2_HIT_F
            if self.frame_index >= hit_f - 1:
                atk_rect = self._get_attack_rect()
                ex = atk_rect.centerx if atk_rect else self.hitbox.centerx
                ey = atk_rect.centery if atk_rect else self.hitbox.centery
                self.particles.emit_impact(ex, ey, self.facing)
                self._atk_vfx_done = True

        # Dano por contato corporal
        if player.alive and self._cd_contact <= 0:
            if self.hitbox.colliderect(player.hitbox) and not player.is_rolling:
                player.take_damage(1)
                self._cd_contact = CONTACT_CD

        self._animate(dt)

    # ─────────────────────────────────────────────────────────────────────────
    # IA
    # ─────────────────────────────────────────────────────────────────────────

    def _run_ai(self, player):
        """
        IA de dois modos: grounded (padrão) e aerial (só quando player sobe).
        Voo é estritamente reativo à altura do player — não acontece por timer.
        Define targets — movimento fica exclusivamente em _physics().
        """
        if not player.alive:
            self.state = "idle"
            return

        dx   = player.hitbox.centerx - self.hitbox.centerx
        dist = abs(dx)

        if dx != 0:
            self.facing = 1 if dx > 0 else -1

        if dist > AGGRO_RANGE:
            self.state = "idle"
            return

        # Detectar se player está em plataforma elevada
        player_elevated = (
            self._ground_y_ready and
            (self._ground_y - player.hitbox.centery) > PLATFORM_THRESHOLD
        )

        # ── FASE TERRESTRE ────────────────────────────────────────────────
        if self._phase == "grounded":
            # Player subiu em plataforma → decola para seguir (com cooldown)
            if player_elevated and self._phase_timer <= 0:
                self._start_aerial_phase(player)
                return

            # Ataque quando próximo
            if dist <= ATTACK_RANGE:
                can1 = self._cd_atk1 <= 0
                can2 = self._cd_atk2 <= 0
                if can1 or can2:
                    chosen = 2 if (can2 and (not can1 or random.random() < ATK2_CHANCE)) else 1
                    self._start_attack(chosen)
                    return
                self.state = "idle"
                return

            # Perseguição terrestre
            self._target_x = float(player.hitbox.centerx - self.facing * PREFERRED_DIST)
            self.state = "walk" if abs(dx) > H_SNAP_THRESH else "idle"
            return

        # ── FASE AÉREA ────────────────────────────────────────────────────
        # Player voltou ao chão → pousa também (com cooldown)
        if not player_elevated and self._phase_timer <= 0 and self._ground_y_ready:
            self._start_grounded_phase()
            return

        # Ataque aéreo quando próximo
        if dist <= ATTACK_RANGE:
            can1 = self._cd_atk1 <= 0
            can2 = self._cd_atk2 <= 0
            if can1 or can2:
                chosen = 2 if (can2 and (not can1 or random.random() < ATK2_CHANCE)) else 1
                self._start_attack(chosen)
                return
            self.state = "idle"
            return

        # Reposicionamento aéreo: persegue a altura do player
        if self._move_axis == "none" and self._reposition_cd <= 0:
            self._target_x = float(player.hitbox.centerx - self.facing * PREFERRED_DIST)
            self._target_y = float(player.hitbox.centery + HOVER_OFFSET)
            self._reposition_cd = random.uniform(REPOSITION_MIN, REPOSITION_MAX)

        self.state = "fly"

    def _start_attack(self, atk_type: int):
        self._atk_type     = atk_type
        self.is_attacking  = True
        self._atk_finished = False
        self._atk_hit_done = False
        self._atk_vfx_done = False
        self.frame_index   = 0
        self.anim_timer    = 0.0
        self.vel_x         = 0.0
        self.state         = f"atk{atk_type}"
        if atk_type == 1:
            self._cd_atk1 = ATK1_CD
        else:
            self._cd_atk2 = ATK2_CD
        self.particles.emit_stomp(self.hitbox.centerx, self.hitbox.bottom)

    def _start_aerial_phase(self, player=None):
        self._phase         = "aerial"
        self._is_grounded   = False
        self._phase_timer   = PHASE_SWITCH_CD + random.uniform(0.5, 2.0)
        self._reposition_cd = 0.0   # reposiciona imediatamente ao decolar
        # Alvo Y: altura do player ou hover padrão, o que for mais alto
        if player is not None:
            self._target_y = float(player.hitbox.centery + HOVER_OFFSET)
        elif self._ground_y_ready:
            self._target_y = self._ground_y + HOVER_HEIGHT
        print(f"[night_boss] DECOLA — segue player em plataforma", flush=True)

    def _start_grounded_phase(self):
        self._phase       = "grounded"
        self._phase_timer = PHASE_SWITCH_CD + random.uniform(0.5, 2.0)
        self._target_y    = self._ground_y
        print(f"[night_boss] POUSA — player voltou ao chão", flush=True)

    def _compute_ground_y(self, platforms) -> float:
        """Retorna o centery do boss quando pousado no chão principal."""
        best = -1.0
        for plat in platforms:
            if getattr(plat, "one_way", False):
                continue
            pr = plat.solid_rect
            # Ignora paredes laterais (solid_rect começa no topo da tela)
            if pr.top < NB_HB_H:
                continue
            candidate = float(pr.top - NB_HB_H // 2)
            if candidate > best:
                best = candidate
        if best < 0:
            from settings import SCREEN_HEIGHT
            best = float(SCREEN_HEIGHT - NB_HB_H // 2 - 10)
        return best

    # ─────────────────────────────────────────────────────────────────────────
    # FÍSICA DE VOO
    # ─────────────────────────────────────────────────────────────────────────

    def _physics(self, dt: float, platforms, player=None):
        from settings import SCREEN_WIDTH, SCREEN_HEIGHT

        # ── Inicializar ground_y na 1ª frame (precisa de platforms) ──────
        if not self._ground_y_ready and platforms:
            self._ground_y = self._compute_ground_y(platforms)
            if self._ground_y > 0:
                self._ground_y_ready = True
                if self._phase == "grounded":
                    # Snap imediato ao chão — boss nasce no solo
                    self._base_y   = self._ground_y
                    self._target_y = self._ground_y
                else:
                    self._target_y = self._ground_y + HOVER_HEIGHT
                    self._base_y   = self._target_y

        dx = self._target_x - self.hitbox.centerx
        dy = self._target_y - self._base_y

        # ── Detectar grounded: boss na fase terrestre E já desceu até o chão
        if self._ground_y_ready and self._phase == "grounded":
            self._is_grounded = abs(self._base_y - self._ground_y) < LAND_THRESHOLD
        else:
            self._is_grounded = False

        # ──────────────────────────────────────────────────────────────────
        if self._is_grounded:
            # MODO TERRESTRE: Y travado no chão, move apenas X
            self._base_y   = self._ground_y
            self._target_y = self._ground_y

            if abs(dx) > H_SNAP_THRESH:
                self._move_axis = "h"
                target_vel = GROUND_SPEED * (1.0 if dx > 0 else -1.0)
                self._smooth_velx += (target_vel - self._smooth_velx) * min(1.0, dt * GROUND_ACCEL)
                step = self._smooth_velx * dt
                if abs(step) > abs(dx):
                    step = dx
                self.hitbox.x += round(step)
                self.vel_x     = self._smooth_velx
                self._resolve_x(platforms)
            else:
                self._move_axis   = "none"
                self._smooth_velx = self._smooth_velx * max(0.0, 1.0 - dt * 8.0)
                self.vel_x        = 0.0
            bob_amp = 0.0   # sem bob no chão — estabilidade visual

        elif self._phase == "grounded":
            # MODO ATERRISSAGEM: descida vertical pura até tocar o chão
            # Ignorar eixo horizontal enquanto não pousou — evita boss voar lateral
            self._move_axis   = "v"
            self._smooth_velx = self._smooth_velx * max(0.0, 1.0 - dt * 12.0)
            self.vel_x        = 0.0
            self._base_y     += (self._ground_y - self._base_y) * min(1.0, dt * MOVE_V_LERP * 2.0)
            bob_amp = BOB_IDLE_AMP

        else:
            # MODO AÉREO: sistema de eixo único (H ou V, nunca diagonal)
            if abs(dx) > H_SNAP_THRESH:
                self._move_axis = "h"
                target_vel = MOVE_H_SPEED * (1.0 if dx > 0 else -1.0)
                self._smooth_velx += (target_vel - self._smooth_velx) * min(1.0, dt * MOVE_H_ACCEL)
                step = self._smooth_velx * dt
                if abs(step) > abs(dx):
                    step = dx
                self.hitbox.x += round(step)
                self.vel_x     = self._smooth_velx
                self._resolve_x(platforms)
                bob_amp = BOB_MOVE_AMP

            elif abs(dy) > V_SNAP_THRESH:
                self._move_axis   = "v"
                self._smooth_velx = self._smooth_velx * max(0.0, 1.0 - dt * 12.0)
                self.vel_x        = 0.0
                self._base_y     += (self._target_y - self._base_y) * min(1.0, dt * MOVE_V_LERP)
                bob_amp = BOB_IDLE_AMP

            else:
                self._move_axis   = "none"
                self._smooth_velx = self._smooth_velx * max(0.0, 1.0 - dt * 8.0)
                self.vel_x        = 0.0
                self._base_y     += (self._target_y - self._base_y) * min(1.0, dt * 0.3)
                bob_amp = BOB_IDLE_AMP

        # ── Clamp _base_y: teto de tela + chão derivado das plataformas ──
        lo_f = float(NB_HB_H // 2 + 10)
        hi_f = float(SCREEN_HEIGHT - NB_HB_H // 2 - 10)
        for plat in platforms:
            if getattr(plat, "one_way", False):
                continue
            pr = plat.solid_rect
            # Ignora paredes laterais (top=0) — elas só limitam X, não Y
            if pr.top < NB_HB_H:
                continue
            candidate = float(pr.top - NB_HB_H // 2)
            if candidate < hi_f:
                hi_f = candidate
        self._base_y   = max(lo_f, min(hi_f, self._base_y))
        self._target_y = min(self._target_y, hi_f)

        # ── Clamp X ───────────────────────────────────────────────────────
        self.hitbox.left  = max(0, self.hitbox.left)
        self.hitbox.right = min(SCREEN_WIDTH, self.hitbox.right)

        # ── Hitbox física (sem bob) ───────────────────────────────────────
        self.hitbox.centery = int(self._base_y)

        # ── Colisão direta com o chão — garantia absoluta ─────────────────
        # Independente do lerp/clamp, o hitbox nunca pode ultrapassar o piso.
        for plat in platforms:
            if getattr(plat, "one_way", False):
                continue
            pr = plat.solid_rect
            if pr.top < NB_HB_H:          # ignora paredes laterais
                continue
            if self.hitbox.bottom > pr.top and self.hitbox.top < pr.bottom:
                self.hitbox.bottom = pr.top
                self._base_y       = float(self.hitbox.centery)
                self._target_y     = min(self._target_y, self._base_y)

        # ── Rect visual (com bob) ─────────────────────────────────────────
        bob           = math.sin(self._bob_time * BOB_FREQ * math.tau) * bob_amp
        ground_push   = GROUND_VISUAL_OFFSET if self._is_grounded else 0
        self.rect.centerx = self.hitbox.centerx
        self.rect.bottom  = self.hitbox.bottom - int(bob) + ground_push

    def _resolve_x(self, platforms):
        for plat in platforms:
            if getattr(plat, "one_way", False):
                continue
            pr = plat.solid_rect
            if not self.hitbox.colliderect(pr):
                continue
            if self.vel_x > 0:
                self.hitbox.right = pr.left
            else:
                self.hitbox.left  = pr.right
            self.vel_x = 0.0

    def _align_rect(self):
        self.rect.center = self.hitbox.center

    # ─────────────────────────────────────────────────────────────────────────
    # ANIMAÇÃO
    # ─────────────────────────────────────────────────────────────────────────

    def _animate(self, dt: float):
        # Hierarquia: death > ataque > hurt > [grounded: idle/walk] > [aéreo: fly]
        # Ataque NÃO é interrompido por hurt — boss commita o swing inteiro.
        if self.is_dead:
            new_state = "death"
        elif self.is_attacking:
            new_state = f"atk{self._atk_type}"
        elif self.is_hurt:
            new_state = "hurt"
        elif self._is_grounded:
            new_state = "walk" if abs(self._smooth_velx) > 10 else "idle"
        else:
            new_state = "fly"

        # Reset ao mudar de estado
        if new_state != self._anim_state:
            self._anim_state = new_state
            self.frame_index = 0
            self.anim_timer  = 0.0

        frames = self._get_frames(new_state)
        if not frames:
            return

        n = max(len(frames), 1)
        if new_state == "atk1":
            spf = ATK1_TOTAL / n
        elif new_state == "atk2":
            spf = ATK2_TOTAL / n
        elif new_state == "hurt":
            spf = HURT_DUR / n
        elif new_state == "death":
            spf = DEATH_TOTAL / n
        elif new_state == "fly":
            spf = FLY_SPF
        elif new_state == "walk":
            spf = WALK_SPF
        else:
            spf = IDLE_SPF

        self.anim_timer += dt
        if self.anim_timer >= spf:
            self.anim_timer -= spf
            if new_state in ("atk1", "atk2", "hurt", "death"):
                if self.frame_index < len(frames) - 1:
                    self.frame_index += 1
                elif new_state in ("atk1", "atk2"):
                    self._atk_finished = True
            else:
                self.frame_index = (self.frame_index + 1) % len(frames)

        new_image = frames[self.frame_index]
        if new_image is not self.image:
            old_bottom  = self.rect.bottom
            old_centerx = self.rect.centerx
            self.image      = new_image
            self.rect       = self.image.get_rect()
            self.rect.bottom  = old_bottom
            self.rect.centerx = old_centerx
        else:
            self.image = new_image

    def _get_frames(self, state: str) -> list:
        bank = self._anims_r if self.facing == 1 else self._anims_l
        return bank.get(state, bank["idle"])

    def _current_frame(self) -> pygame.Surface:
        frames = self._get_frames(self._anim_state)
        return frames[self.frame_index % max(len(frames), 1)]

    def _get_tinted_frame(self) -> pygame.Surface:
        bank   = self._tint_r if self.facing == 1 else self._tint_l
        frames = bank.get(self._anim_state, bank["idle"])
        return frames[min(self.frame_index, len(frames) - 1)]

    # ─────────────────────────────────────────────────────────────────────────
    # MORTE
    # ─────────────────────────────────────────────────────────────────────────

    def _update_death(self, dt: float):
        self._death_timer += dt
        self._animate(dt)
        if self._death_timer >= DEATH_TOTAL:
            progress         = (self._death_timer - DEATH_TOTAL) / FADE_DUR
            self.death_alpha = max(0, int(255 * (1.0 - progress)))
        else:
            self.death_alpha = 255

    @property
    def should_be_removed(self) -> bool:
        return self.is_dead and self.death_alpha <= 0

    # ─────────────────────────────────────────────────────────────────────────
    # COMBATE
    # ─────────────────────────────────────────────────────────────────────────

    def take_damage(self, amount: int = 1):
        if self.invincible_timer > 0 or self.is_dead:
            return
        self.hp               -= amount
        self.invincible_timer  = IFRAMES_DUR
        if self.hp <= 0:
            self.hp = 0
            self._start_death()
        else:
            self.is_hurt     = True
            self._hurt_timer = HURT_DUR
        print(f"[night_boss] hit! HP={self.hp}/{self.max_hp}", flush=True)

    def stun(self, duration: float) -> None:
        """Paralisa o boss pelo tempo dado (Raio Divino). Cancela ação em andamento."""
        if self.is_dead:
            return
        self.is_stunned      = True
        self.stun_timer      = duration
        self.is_attacking    = False
        self._atk_finished   = False
        self.is_recovering   = False
        self.is_hurt         = False
        self.vel_x           = 0.0
        self._smooth_velx    = 0.0
        self._target_x       = float(self.hitbox.centerx)
        self._target_y       = float(self._base_y)
        self.state           = "idle"
        print(f"[night_boss] Stun! {duration:.1f}s", flush=True)

    def _start_death(self):
        self.is_dead      = True
        self.is_attacking = False
        self.is_hurt      = False
        self.state        = "death"
        self._anim_state  = "death"
        self.frame_index  = 0
        self.anim_timer   = 0.0
        self._death_timer = 0.0
        self.death_alpha  = 255
        self.vel_x        = 0.0
        self.particles.clear()
        print(
            f"[night_boss] DERROTADO! Animação de morte ({DEATH_TOTAL:.1f}s).",
            flush=True,
        )

    def _get_attack_rect(self) -> pygame.Rect | None:
        if not self.is_attacking:
            return None
        if self._atk_type == 1:
            reach, vy, vh = 95,  38, 70
        else:
            reach, vy, vh = 135, 52, 105
        ax = self.hitbox.right if self.facing == 1 else self.hitbox.left - reach
        return pygame.Rect(ax, self.hitbox.centery - vy, reach, vh)

    # ─────────────────────────────────────────────────────────────────────────
    # DRAW
    # ─────────────────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface):
        if self.is_dead:
            img = self.image.copy()
            if self.death_alpha < 255:
                img.set_alpha(self.death_alpha)
            screen.blit(img, self.rect)
            return

        # Stun (Raio Divino): pulso amarelo lento a ~2Hz
        if self.is_stunned:
            img = self.image.copy()
            if int(self.stun_timer * 4) % 2:
                overlay = pygame.Surface(img.get_size(), pygame.SRCALPHA)
                overlay.fill((90, 90, 0, 0))
                img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            screen.blit(img, self.rect)
            return

        # I-frames: alterna frame normal / frame tintado de vermelho
        if self.invincible_timer > 0:
            if int(self.invincible_timer * 12) % 2 == 1:
                screen.blit(self._get_tinted_frame(), self.rect)
                return

        screen.blit(self.image, self.rect)

    # ─────────────────────────────────────────────────────────────────────────
    # HUD — Umbrazoth: nome integrado dentro do frame da barra
    # ─────────────────────────────────────────────────────────────────────────

    def draw_hud(self, screen: pygame.Surface):
        if self.is_dead:
            return
        if self._hud_cache is None:
            self._hud_cache = self._build_hud_cache()
        if not self._hud_cache:
            self._draw_hud_fallback(screen)
            return

        c        = self._hud_cache
        hp_ratio = max(0.0, min(1.0, self._hud_hp / self.max_hp))

        # 1. Moldura base (under)
        screen.blit(c['under'], (c['bar_x'], c['bar_y']))

        # 2. Preenchimento de HP — recortado horizontalmente conforme razão de vida
        if c['prog']:
            fill_w = int(c['prog'].get_width() * hp_ratio)
            if fill_w > 0:
                screen.blit(
                    c['prog'],
                    (c['bar_x'] + c['prog_ox'], c['bar_y']),
                    area=pygame.Rect(0, 0, fill_w, c['prog'].get_height()),
                )

        # 3. Glow sutil atrás do nome (desenhado antes do nome)
        if c['glow']:
            screen.blit(c['glow'], (c['glow_x'], c['glow_y']))

        # 4. Nome DENTRO do frame — centralizado sobre o preenchimento
        if c['name']:
            screen.blit(c['name'], (c['name_x'], c['name_y']))

    def _build_hud_cache(self) -> dict:
        from settings import SCREEN_WIDTH

        LIFE_DIR  = os.path.join(_NB_DIR, "life")
        BAR_SCALE = 3   # → under: 480×192 | prog: 432×192

        def _try_load(fname):
            path = os.path.join(LIFE_DIR, fname)
            try:
                surf = pygame.image.load(path).convert_alpha()
                print(f"[night_boss HUD] '{fname}': {surf.get_size()}", flush=True)
                return surf
            except Exception as e:
                print(f"[night_boss HUD] falha '{fname}': {e}", flush=True)
                return None

        under_raw = _try_load("umbrazoth_health_under.png")
        prog_raw  = _try_load("umbrazoth_health_progress.png")
        name_raw  = _try_load("nome_boss-removebg-preview.png")

        if under_raw is None:
            return {}

        # ── Escalar barra ──────────────────────────────────────────────────────
        bw    = under_raw.get_width()  * BAR_SCALE  # 480
        bh    = under_raw.get_height() * BAR_SCALE  # 192
        under = pygame.transform.scale(under_raw, (bw, bh))

        prog    = pygame.transform.scale(
            prog_raw,
            (prog_raw.get_width() * BAR_SCALE, prog_raw.get_height() * BAR_SCALE),
        ) if prog_raw else None
        prog_ox = (bw - prog.get_width()) // 2 if prog else 0

        # Barra posicionada perto do topo
        bar_x = SCREEN_WIDTH // 2 - bw // 2  # 240
        bar_y = 10

        # ── Bounds do frame visível (medidos em pixels nativos) ───────────────
        # under visível: left=6, top=6, right=153, bot=37  →  148×32 px native
        FRAME_L   = 6  * BAR_SCALE   # 18 px — offset esquerdo do frame no under
        FRAME_T   = 6  * BAR_SCALE   # 18 px — offset superior do frame no under
        FRAME_W   = (153 - 6) * BAR_SCALE  # 441 px — largura visível
        FRAME_H   = (37  - 6) * BAR_SCALE  # 93 px  — altura visível

        # Posição absoluta do frame na tela
        frame_screen_x = bar_x + FRAME_L   # 258
        frame_screen_y = bar_y + FRAME_T   # 28

        # ── Recortar nome ao bounding-box medido: 555×97 em (47, 150) ────────
        NAME_CROP = pygame.Rect(47, 150, 555, 97)
        if name_raw:
            cropped = name_raw.subsurface(NAME_CROP)

            # Escalar para 75% da largura do frame; altura proporcional
            name_w = int(FRAME_W * 0.75)                   # ≈ 331 px
            name_h = int(NAME_CROP.height * name_w / NAME_CROP.width)  # ≈ 58 px

            name   = pygame.transform.scale(cropped, (name_w, name_h))

            # Centralizar DENTRO do frame (horizontal + vertical)
            name_x = frame_screen_x + (FRAME_W - name_w) // 2   # = frame_screen_x
            name_y = frame_screen_y + (FRAME_H - name_h) // 2 + 36

            # Glow: versão alargada (+6/+4 px) com alpha reduzido a ≈27%
            glow_w = name_w + 6
            glow_h = name_h + 4
            glow   = pygame.transform.scale(cropped, (glow_w, glow_h))
            # BLEND_RGBA_MULT: RGB×1.0, Alpha×(70/255)≈0.27 → halo translúcido
            glow.fill((255, 255, 255, 70), special_flags=pygame.BLEND_RGBA_MULT)
            glow_x = name_x - 3
            glow_y = name_y - 2
        else:
            name = glow = None
            name_x = name_y = glow_x = glow_y = 0

        return {
            'under':   under,
            'prog':    prog,
            'name':    name,
            'glow':    glow,
            'bar_x':   bar_x,
            'bar_y':   bar_y,
            'name_x':  name_x,
            'name_y':  name_y,
            'glow_x':  glow_x,
            'glow_y':  glow_y,
            'prog_ox': prog_ox,
        }

    def _draw_hud_fallback(self, screen: pygame.Surface):
        from settings import SCREEN_WIDTH
        BAR_W, BAR_H = 360, 28
        bx = SCREEN_WIDTH // 2 - BAR_W // 2
        by = 10
        # Painel escuro
        pygame.draw.rect(screen, (6, 3, 16),    (bx-4, by-4, BAR_W+8, BAR_H+8))
        pygame.draw.rect(screen, (18, 10, 38),  (bx, by, BAR_W, BAR_H))
        # Preenchimento
        fill = max(0, int(BAR_W * self._hud_hp / self.max_hp))
        if fill > 0:
            pygame.draw.rect(screen, (90, 40, 170), (bx, by, fill, BAR_H))
            pygame.draw.rect(screen, (150, 90, 255), (bx, by, fill, 5))
        # Borda
        pygame.draw.rect(screen, (140, 80, 220), (bx, by, BAR_W, BAR_H), 2)
        # Nome centralizado
        font = pygame.font.SysFont("monospace", 14, bold=True)
        lbl  = font.render("UMBRAZOTH — ASAS DA RUÍNA", True, (210, 170, 255))
        screen.blit(lbl, (bx + BAR_W // 2 - lbl.get_width() // 2, by + (BAR_H - lbl.get_height()) // 2))
