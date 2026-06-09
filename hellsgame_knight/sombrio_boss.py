"""
sombrio_boss.py — Bringer of Death / Morthak  v1

Assets usados (todos os sprites de cada pasta):
    idle/   Bringer-of-Death_Idle_{1..8}.png      8 frames  loop
    walk/   Bringer-of-Death_Walk_{1..8}.png      8 frames  loop
    atk_1/  Bringer-of-Death_Attack_{1..10}.png  10 frames  one-shot  2 corações
    cast/   Bringer-of-Death_Cast_{1..9}.png       9 frames  one-shot  boss PARADO
    spell/  Bringer-of-Death_Spell_{1..16}.png   16 frames  projetil acima do player
    hurt/   Bringer-of-Death_Hurt_{1..3}.png       3 frames  one-shot
    death/  Bringer-of-Death_Death_{1..10}.png   10 frames  one-shot + fade-out

State machine:
    idle  ──► walk   player entra em AGGRO_RANGE
    walk  ──► atk_1  player entra em ATTACK_RANGE + atk1_cd livre
    walk  ──► cast   player fora de ATTACK_RANGE + cast_cd livre
    atk_1 ──► idle   animação completa + recovery
    cast  ──► idle   animação completa + magia spawned + recovery
    hurt  ──► idle   após HURT_DUR  (não cancela ataque nem cast)
    *     ──► death  hp == 0

Interface compatível com game.py (idêntica a MinotaurBoss / NightBoss):
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
"""

import pygame
import os
import random
from particles import ParticleSystem
from analytics import tracker as combat_tracker

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sombrio_boss")


def _p(subdir: str, fname: str) -> str:
    return os.path.join(_DIR, subdir, fname)


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES — DISPLAY
# ─────────────────────────────────────────────────────────────────────────────

SB_SCALE    = 2.0    # escala aplicada a cada frame do boss
SPELL_SCALE = 2.3    # escala dos frames da magia

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES — HITBOX
# ─────────────────────────────────────────────────────────────────────────────

SB_HB_W       = 68   # largura hitbox do boss
SB_HB_H       = 108  # altura  hitbox do boss
SB_FOOT_PAD   = 3    # px abaixo do hitbox.bottom até o bottom do canvas (medido: feet_from_bottom=3)
SPRITE_X_OFF  = 71   # px — centro do corpo no canvas (facing-left): 211px, canvas_half=140 → offset=71

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES — HP
# ─────────────────────────────────────────────────────────────────────────────

SB_MAX_HP = 24

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES — IA
# ─────────────────────────────────────────────────────────────────────────────

AGGRO_RANGE  = 520    # px — detecta o player
ATTACK_RANGE = 130    # px — distância de corpo a corpo (atk_1)
WALK_SPEED   = 65     # px/s — pesado e deliberado

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES — ANIMAÇÕES
# ─────────────────────────────────────────────────────────────────────────────

IDLE_SPF    = 0.12   # s/frame idle loop
WALK_SPF    = 0.10   # s/frame walk loop
ATK1_TOTAL  = 1.10   # s — duração total do atk_1 (10 frames)
ATK1_HIT_F  = 7      # frame de impacto atk_1 (1-indexed)
ATK1_DMG    = 2      # 2 corações por acerto
CAST_TOTAL  = 1.05   # s — duração total do cast (9 frames) — boss imóvel
HURT_DUR    = 0.30   # s — duração hurt (3 frames one-shot)
DEATH_TOTAL = 2.20   # s — duração animação de morte (10 frames)
FADE_DUR    = 1.00   # s — fade-out após animação de morte

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES — COOLDOWNS
# ─────────────────────────────────────────────────────────────────────────────

ATK1_CD       = 1.50   # pausa mínima entre atk_1
CAST_CD       = 4.00   # pausa mínima entre casts
RECOVERY_ATK1 = 0.60   # janela de punição após atk_1 (boss parado)
RECOVERY_CAST = 0.40   # janela de punição após cast
IFRAMES_DUR   = 0.40   # invencibilidade após cada hit recebido
CONTACT_CD    = 1.20   # cooldown dano por contato corporal

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES — MAGIA
# ─────────────────────────────────────────────────────────────────────────────

SPELL_SPF          = 0.10   # s/frame — animação one-shot (16 frames × 0.10 = 1.6 s)
SPELL_DMG          = 1      # 1 coração por magia
SPELL_HB_W         = 72     # largura  da hitbox — precisa, levemente menor que o sprite
SPELL_HB_H         = 72     # altura   da hitbox
SPELL_ABOVE        = 85     # px: centro do sprite fica SPELL_ABOVE px acima do topo da hitbox do player
SPELL_H_STRETCH    = 1.60   # multiplicador de altura do sprite (sem alterar a largura)
SPELL_ACTIVE_START = 4      # primeiro frame ativo (0-indexed) — 0.4 s de startup/telegraph
SPELL_ACTIVE_END   = 13     # último  frame ativo — frames 14-15 são recovery (sem dano)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS — CARREGAMENTO DE FRAMES
# ─────────────────────────────────────────────────────────────────────────────

def _load_anim(subdir: str, prefix: str, count: int, scale: float = SB_SCALE) -> list[pygame.Surface]:
    """
    Carrega todos os frames de assets/sombrio_boss/{subdir}/{prefix}_{i}.png
    e escala proporcionalmente.
    """
    frames: list[pygame.Surface] = []
    subdir_path = os.path.join(_DIR, subdir)

    for i in range(1, count + 1):
        fname = f"{prefix}_{i}.png"
        path  = os.path.join(subdir_path, fname)
        try:
            img = pygame.image.load(path).convert_alpha()
            rw, rh = img.get_size()
            frames.append(pygame.transform.scale(img, (max(1, int(rw * scale)),
                                                        max(1, int(rh * scale)))))
        except Exception as e:
            print(f"[sombrio_boss] ERRO {subdir}/{fname}: {e}", flush=True)
            ph = pygame.Surface((int(80 * scale), int(80 * scale)), pygame.SRCALPHA)
            ph.fill((220, 0, 220, 160))
            frames.append(ph)

    if frames:
        w, h = frames[0].get_size()
        print(f"[sombrio_boss] '{subdir}': {len(frames)} frames  {w}×{h}  (scale={scale}x)", flush=True)
    return frames


def _flip(frames: list[pygame.Surface]) -> list[pygame.Surface]:
    return [pygame.transform.flip(f, True, False) for f in frames]


def _tint_red(frame: pygame.Surface) -> pygame.Surface:
    """Tint vermelho preservando canal alpha (BLEND_RGB_ADD não toca alpha)."""
    result  = frame.copy()
    overlay = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
    overlay.fill((130, 0, 0, 0))
    result.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# BRINGER SPELL — projetil da magia do cast
# ─────────────────────────────────────────────────────────────────────────────

class BringerSpell:
    """
    Magia estática do Bringer of Death.

    Ciclo de vida:
        1. Aparece centrada no X do player, com o centro do sprite
           SPELL_ABOVE px acima do topo da hitbox do player.
        2. Executa os 16 frames em one-shot (sem loop, sem queda).
        3. A cada frame, verifica colisão real com o player.
           Ao primeiro contato → tira SPELL_DMG coração → para de causar dano.
        4. Após o último frame → desaparece.
    """

    def __init__(self, cx: int, player_hitbox_top: int,
                 spell_frames: list[pygame.Surface]):
        # Esticar apenas a altura de cada frame (sem alterar a largura)
        if spell_frames:
            fw = spell_frames[0].get_width()
            fh = spell_frames[0].get_height()
            new_h = int(fh * SPELL_H_STRETCH)
            self._frames = [pygame.transform.scale(f, (fw, new_h)) for f in spell_frames]
        else:
            self._frames = spell_frames

        self.frame_index = 0
        self.anim_timer  = 0.0
        self.done        = False
        self.hit_done    = False

        # Rect visual: centralizado no X do player, centro acima da cabeça
        w = self._frames[0].get_width()  if self._frames else SPELL_HB_W
        h = self._frames[0].get_height() if self._frames else SPELL_HB_H
        self.rect         = pygame.Rect(0, 0, w, h)
        self.rect.centerx = cx
        self.rect.centery = player_hitbox_top - SPELL_ABOVE

        # Hitbox — mesma âncora do rect, atinge o player se ele não se mover
        self.hitbox           = pygame.Rect(0, 0, SPELL_HB_W, SPELL_HB_H)
        self.hitbox.midbottom = self.rect.midbottom

    def update(self, dt: float, player) -> None:
        if self.done:
            return

        # Animação one-shot: avança 1 frame a cada SPELL_SPF segundos
        self.anim_timer += dt
        if self.anim_timer >= SPELL_SPF:
            self.anim_timer -= SPELL_SPF
            if self.frame_index < len(self._frames) - 1:
                self.frame_index += 1
            else:
                self.done = True   # último frame concluído → desaparece
                return

        # Hitbox ativa apenas durante os frames "activos" (padrão profissional)
        # Frames 0-3: startup/telegraph — player tem 0.4 s para reagir
        # Frames 4-13: zona de dano real
        # Frames 14-15: recovery — efeito ainda visível, mas sem dano
        hitbox_active = SPELL_ACTIVE_START <= self.frame_index <= SPELL_ACTIVE_END
        if hitbox_active and not self.hit_done and self.hitbox.colliderect(player.hitbox):
            player.take_damage(SPELL_DMG)
            self.hit_done = True

    def draw(self, screen: pygame.Surface) -> None:
        if self.done or not self._frames:
            return
        screen.blit(self._frames[self.frame_index], self.rect)


# ─────────────────────────────────────────────────────────────────────────────
# CLASSE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class SombrioBoss(pygame.sprite.Sprite):
    """
    Bringer of Death — Morthak.
    Boss terrestre da Sombrio Arena com combate corpo a corpo e magia à distância.
    Usa TODOS os sprites de assets/sombrio_boss/.
    """

    def __init__(self, x: int, y: int):
        super().__init__()

        # ── Carregar TODOS os frames de cada animação ─────────────────────
        idle_r  = _load_anim("idle",  "Bringer-of-Death_Idle",    8)
        walk_r  = _load_anim("walk",  "Bringer-of-Death_Walk",    8)
        atk1_r  = _load_anim("atk_1", "Bringer-of-Death_Attack", 10)
        cast_r  = _load_anim("cast",  "Bringer-of-Death_Cast",    9)
        hurt_r  = _load_anim("hurt",  "Bringer-of-Death_Hurt",    3)
        death_r = _load_anim("death", "Bringer-of-Death_Death",  10)
        spell_r = _load_anim("spell", "Bringer-of-Death_Spell",  16, SPELL_SCALE)

        self._spell_frames = spell_r

        # Orientação: sprites originais olham para a ESQUERDA
        self._anims_l: dict[str, list] = {
            "idle":  idle_r,
            "walk":  walk_r,
            "atk_1": atk1_r,
            "cast":  cast_r,
            "hurt":  hurt_r,
            "death": death_r,
        }
        self._anims_r: dict[str, list] = {k: _flip(v) for k, v in self._anims_l.items()}

        # Frames pré-tintados para efeito de i-frames (vermelho suave)
        self._tint_l: dict[str, list] = {
            k: [_tint_red(f) for f in v] for k, v in self._anims_l.items()
        }
        self._tint_r: dict[str, list] = {k: _flip(v) for k, v in self._tint_l.items()}

        # ── HUD (lazy-loaded na 1ª chamada de draw_hud) ───────────────────
        self._hud_cache = None
        self._hud_hp    = float(SB_MAX_HP)   # HP animado para drain suave

        # ── Partículas ────────────────────────────────────────────────────
        self.particles = ParticleSystem()

        # ── Estado ────────────────────────────────────────────────────────
        self.state       = "idle"
        self._anim_state = "idle"
        self.facing      = -1       # spawna à direita olhando para o player (esq.)
        self.frame_index = 0
        self.anim_timer  = 0.0

        # ── Ataque 1 ──────────────────────────────────────────────────────
        self.is_attacking  = False
        self._atk_finished = False
        self._atk_hit_done = False
        self._atk_vfx_done = False

        # ── Cast + Magia ──────────────────────────────────────────────────
        self.is_casting        = False
        self._cast_finished    = False
        self._cast_spell_done  = False   # garantia de 1 magia por cast
        self.spells: list[BringerSpell] = []

        # ── Recovery (janela de punição após ação) ────────────────────────
        self.is_recovering   = False
        self._recovery_timer = 0.0

        # ── Cooldowns ─────────────────────────────────────────────────────
        self._cd_atk1    = 0.0
        self._cd_cast    = 0.0
        self._cd_contact = 0.0

        # ── Stun (Raio Divino) ────────────────────────────────────────────
        self.is_stunned = False
        self.stun_timer = 0.0

        # ── Hurt ──────────────────────────────────────────────────────────
        self.is_hurt          = False
        self._hurt_timer      = 0.0
        self.invincible_timer = 0.0

        # ── HP ────────────────────────────────────────────────────────────
        self.hp     = SB_MAX_HP
        self.max_hp = SB_MAX_HP

        # ── Morte ─────────────────────────────────────────────────────────
        self.is_dead      = False
        self._death_timer = 0.0
        self.death_alpha  = 255

        # ── Física ────────────────────────────────────────────────────────
        self.vel_x = 0.0

        # ── Adaptive AI Parameters ────────────────────────────────────────
        self.habits = combat_tracker.global_data.get('habit_scores', {})
        self.profile = combat_tracker.global_data.get('style_profile', "Unknown")
        
        # Twitchy Counter: Delay the attack hit frame if player rolls after hits
        self.atk_hit_frame = ATK1_HIT_F
        if self.profile == "Twitchy" or self.habits.get("twitchy", 0) > 0.5:
            self.atk_hit_frame = 9  # Delayed swing to catch the end of a roll
            print(f"[sombrio_boss] Adaptive: Delayed swing active (frame {self.atk_hit_frame})")

        # Berserker Counter: Lower burst cooldown
        self._cd_burst = 0.0
        self.burst_cd_max = 6.0
        if self.profile == "Berserker" or self.habits.get("berserker", 0) > 0.6:
            self.burst_cd_max = 3.5  # More frequent AoE pushbacks
            print(f"[sombrio_boss] Adaptive: Berserker counter active (Lower burst CD)")

        # Aviator Counter: Faster spells
        self.spell_delay_mult = 1.0
        if self.profile == "Aviator" or self.habits.get("aviator", 0) > 0.6:
            self.spell_delay_mult = 0.6  # Spells happen faster after cast starts
            print(f"[sombrio_boss] Adaptive: Anti-Air focus active (Faster spell startup)")

        # ── Runtime adaptive tracking (aprendizado DURANTE o combate) ─────
        self._rt = {
            'projeteis':  0,    # projéteis mágicos disparados pelo player
            'raios':      0,    # raios divinos utilizados
            'pocoes':     0,    # poções usadas
            'rolls_esq':  0,    # esquivas para a esquerda
            'rolls_dir':  0,    # esquivas para a direita
            't_perto':    0.0,  # segundos em combate corpo a corpo
            't_longe':    0.0,  # segundos à distância
        }

        # Fase de combate (1, 2, 3) determinada pelo HP atual
        self._phase         = 1
        self._stun_count    = 0      # quantos raios já recebeu (resistência)

        # Adaptação anti-ranged
        self._anti_ranged   = False  # True após 8+ projéteis

        # Previsão de movimento do spell
        self._pred_time     = 0.25   # segundos de antecipação (cresce com erros)
        self._spell_escapes = 0      # magias que não acertaram

        # Viés de direção baseado no padrão de esquivas
        self._bias_dir      = 0      # -1 (esq), 0 (neutro), +1 (dir)

        # Mensagem adaptativa na HUD
        self._msg           = ""
        self._msg_timer     = 0.0
        self._msg_font      = pygame.font.SysFont("monospace", 16, bold=True)

        # ── Hitbox / rect ─────────────────────────────────────────────────
        self.hitbox = pygame.Rect(0, 0, SB_HB_W, SB_HB_H)
        self.hitbox.midbottom = (x, y)
        self.image = self._current_frame()
        self.rect  = self.image.get_rect()
        self._align_rect()

        print(
            f"[sombrio_boss] SombrioBoss criado em ({x},{y})  "
            f"HP={SB_MAX_HP}  scale={SB_SCALE}x  hitbox={self.hitbox}",
            flush=True,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE PRINCIPAL
    # ─────────────────────────────────────────────────────────────────────────

    def update(self, dt: float, platforms, player, projectiles=None) -> None:
        # Cooldowns
        self.invincible_timer = max(0.0, self.invincible_timer - dt)
        self._cd_atk1         = max(0.0, self._cd_atk1         - dt)
        self._cd_cast         = max(0.0, self._cd_cast          - dt)
        self._cd_burst        = max(0.0, self._cd_burst         - dt)
        self._cd_contact      = max(0.0, self._cd_contact       - dt)
        self.stun_timer       = max(0.0, self.stun_timer         - dt)
        if self.stun_timer <= 0.0:
            self.is_stunned = False
        self.particles.update(dt)

        # ── Adaptações de runtime ──────────────────────────────────────────
        self._update_phase()
        self._update_runtime(dt, player)

        # Barra de vida: drain animado suave (~15% max/s)
        if self._hud_hp > self.hp:
            self._hud_hp = max(float(self.hp), self._hud_hp - dt * self.max_hp * 0.15)
        else:
            self._hud_hp = float(self.hp)

        # Morte — ignora toda a lógica restante
        if self.is_dead:
            self._update_death(dt)
            self._update_spells(dt, player)
            return

        # ── Hurt ──────────────────────────────────────────────────────────
        if self.is_hurt:
            self._hurt_timer -= dt
            if self._hurt_timer <= 0.0:
                self.is_hurt = False

        # ── Fim de atk_1 → recovery ───────────────────────────────────────
        if self.is_attacking and self._atk_finished:
            self.is_attacking    = False
            self._atk_finished   = False
            self._atk_hit_done   = False
            self._atk_vfx_done   = False
            self.is_recovering   = True
            self._recovery_timer = RECOVERY_ATK1
            self.vel_x           = 0.0
            self.state           = "idle"
            self.particles.emit_recovery(self.hitbox.centerx, self.hitbox.bottom)

        # ── Fim de cast/burst → spawn magia + recovery ──────────────────────────
        if self.is_casting and self._cast_finished:
            self.is_casting     = False
            self._cast_finished = False
            if not self._cast_spell_done:
                if self.state == "burst":
                    self._spawn_burst(player)
                else:
                    self._spawn_spell(player)
                self._cast_spell_done = True
            self.is_recovering   = True
            self._recovery_timer = RECOVERY_CAST
            self.vel_x           = 0.0
            self.state           = "idle"

        # ── Recovery (janela de punição — boss parado) ────────────────────
        if self.is_recovering:
            self._recovery_timer -= dt
            self.vel_x = 0.0
            if self._recovery_timer <= 0.0:
                self.is_recovering = False

        # Stun (Raio Divino): imobiliza o boss completamente
        if self.is_stunned:
            self.vel_x = 0.0

        # ── IA — bloqueada durante ação ativa e stun ──────────────────────
        if not (self.is_hurt or self.is_attacking or self.is_casting or self.is_recovering or self.is_stunned):
            self._run_ai(player)

        # ── Física ────────────────────────────────────────────────────────
        self._physics(dt, platforms)

        # ── Dano atk_1 (1 hit por swing garantido) ────────────────────────
        if self.is_attacking and not self._atk_hit_done:
            if self.frame_index >= self.atk_hit_frame - 1:
                atk_rect = self._get_attack_rect()
                if atk_rect and player.alive and atk_rect.colliderect(player.hitbox):
                    if not player.is_rolling:
                        player.take_damage(ATK1_DMG)
                self._atk_hit_done = True

        # ── VFX partículas no frame de impacto ────────────────────────────
        if self.is_attacking and not self._atk_vfx_done and self.frame_index >= self.atk_hit_frame - 1:
            atk_rect = self._get_attack_rect()
            ex = atk_rect.centerx if atk_rect else self.hitbox.centerx
            ey = atk_rect.centery if atk_rect else self.hitbox.centery
            self.particles.emit_impact(ex, ey, self.facing)
            self._atk_vfx_done = True

        # ── Dano por contato corporal ──────────────────────────────────────
        if player.alive and self._cd_contact <= 0:
            if self.hitbox.colliderect(player.hitbox) and not player.is_rolling:
                player.take_damage(1)
                self._cd_contact = CONTACT_CD

        # ── Magia ─────────────────────────────────────────────────────────
        self._update_spells(dt, player)

        # ── Animação ──────────────────────────────────────────────────────
        self._animate(dt)

    # ─────────────────────────────────────────────────────────────────────────
    # MAGIA
    # ─────────────────────────────────────────────────────────────────────────

    def _update_spells(self, dt: float, player) -> None:
        for spell in self.spells:
            spell.update(dt, player)
        for spell in self.spells:
            if spell.done and not spell.hit_done:
                self._on_spell_miss()
        self.spells = [s for s in self.spells if not s.done]

    def _spawn_spell(self, player) -> None:
        vel_x  = getattr(player, 'vel_x', 0)
        pred_x = int(player.hitbox.centerx + vel_x * self._pred_time)
        bias_x = self._bias_dir * 60
        cx     = pred_x + bias_x
        top_y  = player.hitbox.top
        self.spells.append(BringerSpell(cx, top_y, list(self._spell_frames)))
        print(f"[sombrio_boss] Magia: pred_x={pred_x} bias={bias_x} cx={cx}", flush=True)

    def _spawn_burst(self, player) -> None:
        cx    = self.hitbox.centerx
        top_y = self.hitbox.top
        shift = self._bias_dir * 60   # desloca conjunto na direção preferida do player
        self.spells.append(BringerSpell(cx - 100 + shift, top_y, list(self._spell_frames)))
        self.spells.append(BringerSpell(cx        + shift, top_y, list(self._spell_frames)))
        self.spells.append(BringerSpell(cx + 100  + shift, top_y, list(self._spell_frames)))
        print(f"[sombrio_boss] BURST invocada (bias_dir={self._bias_dir} shift={shift})", flush=True)

    # ─────────────────────────────────────────────────────────────────────────
    # IA
    # ─────────────────────────────────────────────────────────────────────────

    def _run_ai(self, player) -> None:
        if not player.alive:
            self.state = "idle"
            self.vel_x = 0.0
            return

        dx   = player.hitbox.centerx - self.hitbox.centerx
        dist = abs(dx)

        # Atualiza orientação
        if dx != 0:
            self.facing = 1 if dx > 0 else -1

        # Fora de aggro — relaxado
        if dist > AGGRO_RANGE:
            self.state = "idle"
            self.vel_x = 0.0
            return

        # ADAPTIVE: Berserker Counter (AoE Burst)
        if dist <= 100 and self._cd_burst <= 0:
            self._start_burst()
            return

        # PERTO — corpo a corpo (prioridade)
        if dist <= ATTACK_RANGE and self._cd_atk1 <= 0:
            self._start_atk1()
            return

        # DISTANTE — cast (magia à distância)
        if dist > ATTACK_RANGE and self._cd_cast <= 0:
            cast_prob = 0.6 if self._anti_ranged else 0.3
            if not player.on_ground or random.random() < cast_prob:
                self._start_cast()
                return

        # Aguardando cooldowns — perseguir
        self.state = "walk"
        self.vel_x = self._effective_walk_speed() * self.facing

    def _start_burst(self) -> None:
        self.is_casting       = True
        self._cast_finished   = False
        self._cast_spell_done = False
        self.frame_index      = 0
        self.anim_timer       = 0.0
        self.vel_x            = 0.0
        self.state            = "burst"
        self._cd_burst         = self._effective_burst_cd()
        print("[sombrio_boss] BURST iniciado (Anti-Berserker)", flush=True)

    def _start_atk1(self) -> None:
        self.is_attacking  = True
        self._atk_finished = False
        self._atk_hit_done = False
        self._atk_vfx_done = False
        self.frame_index   = 0
        self.anim_timer    = 0.0
        self.vel_x         = 0.0
        self.state         = "atk_1"
        self._cd_atk1      = ATK1_CD
        self.particles.emit_stomp(self.hitbox.centerx, self.hitbox.bottom)

    def _start_cast(self) -> None:
        self.is_casting       = True
        self._cast_finished   = False
        self._cast_spell_done = False
        self.frame_index      = 0
        self.anim_timer       = 0.0
        self.vel_x            = 0.0
        self.state            = "cast"
        self._cd_cast         = self._effective_cast_cd()
        print("[sombrio_boss] CAST iniciado — boss imóvel", flush=True)

    # ─────────────────────────────────────────────────────────────────────────
    # FÍSICA
    # ─────────────────────────────────────────────────────────────────────────

    def _physics(self, dt: float, platforms) -> None:
        from settings import SCREEN_WIDTH
        if self.vel_x != 0.0:
            self.hitbox.x += round(self.vel_x * dt)
            self._resolve_x(platforms)
        # Clamp lateral
        self.hitbox.left  = max(0, self.hitbox.left)
        self.hitbox.right = min(SCREEN_WIDTH, self.hitbox.right)
        self._align_rect()

    def _resolve_x(self, platforms) -> None:
        for plat in platforms:
            pr = plat.solid_rect
            if not self.hitbox.colliderect(pr):
                continue
            if self.vel_x > 0:
                self.hitbox.right = pr.left
            else:
                self.hitbox.left  = pr.right
            self.vel_x = 0.0

    def _align_rect(self) -> None:
        # Sprites facing-left têm o corpo 71px à direita do centro do canvas.
        # Quando espelhado (facing=+1) o corpo fica 71px à ESQUERDA do centro.
        # Deslocamos o rect para que o centro visual do corpo coincida com o hitbox.
        h_off = -SPRITE_X_OFF if self.facing == -1 else SPRITE_X_OFF
        self.rect.centerx = self.hitbox.centerx + h_off
        self.rect.bottom  = self.hitbox.bottom  + SB_FOOT_PAD

    # ─────────────────────────────────────────────────────────────────────────
    # ANIMAÇÃO
    # ─────────────────────────────────────────────────────────────────────────

    def _animate(self, dt: float) -> None:
        # Hierarquia de prioridade: death > cast/burst > atk_1 > hurt > walk > idle
        # Ações de combate ativas NÃO são interrompidas por hurt — boss commita a ação inteira.
        if self.is_dead:
            new_state = "death"
        elif self.is_casting:
            # burst usa os mesmos frames de cast
            new_state = "cast"
        elif self.is_attacking:
            new_state = "atk_1"
        elif self.is_hurt:
            new_state = "hurt"
        elif self.state == "walk" and abs(self.vel_x) > 1:
            new_state = "walk"
        else:
            new_state = "idle"

        # Reset de frame ao mudar de estado
        if new_state != self._anim_state:
            self._anim_state = new_state
            self.frame_index = 0
            self.anim_timer  = 0.0

        frames = self._get_frames(new_state)
        if not frames:
            return

        n = max(len(frames), 1)
        if new_state == "atk_1":
            spf = ATK1_TOTAL / n
        elif new_state == "cast":
            # ADAPTIVE: Faster spells for Aviators
            spf = (CAST_TOTAL / n) * self.spell_delay_mult
        elif new_state == "hurt":
            spf = HURT_DUR / n
        elif new_state == "death":
            spf = DEATH_TOTAL / n
        elif new_state == "walk":
            spf = WALK_SPF
        else:
            spf = IDLE_SPF

        self.anim_timer += dt
        if self.anim_timer >= spf:
            self.anim_timer -= spf
            one_shot = new_state in ("atk_1", "cast", "hurt", "death")
            if one_shot:
                if self.frame_index < len(frames) - 1:
                    self.frame_index += 1
                elif new_state == "atk_1":
                    self._atk_finished = True
                elif new_state == "cast":
                    self._cast_finished = True
                # hurt e death travam no último frame até saírem por lógica externa
            else:
                self.frame_index = (self.frame_index + 1) % len(frames)

        # Atualiza image mantendo posição do rect
        new_img = frames[self.frame_index]
        if new_img is not self.image:
            old_bottom  = self.rect.bottom
            old_centerx = self.rect.centerx
            self.image      = new_img
            self.rect       = self.image.get_rect()
            self.rect.bottom  = old_bottom
            self.rect.centerx = old_centerx
        else:
            self.image = new_img

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

    def _update_death(self, dt: float) -> None:
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

    def take_damage(self, amount: int = 1) -> None:
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
        print(f"[sombrio_boss] hit! HP={self.hp}/{self.max_hp}", flush=True)

    def stun(self, duration: float) -> None:
        """Paralisa o boss pelo tempo dado (Raio Divino). Cancela ação em andamento."""
        if self.is_dead:
            return
        _STUN_TABLE = [3.0, 2.0, 1.0, 0.5]
        idx       = min(self._stun_count, len(_STUN_TABLE) - 1)
        effective = _STUN_TABLE[idx]
        self._stun_count += 1
        if self._stun_count > 1:
            self._show_msg("RESISTÊNCIA DESENVOLVIDA")
        self.is_stunned     = True
        self.stun_timer     = effective
        self.is_attacking   = False
        self._atk_finished  = False
        self.is_casting     = False
        self._cast_finished = False
        self.is_recovering  = False
        self.is_hurt        = False
        self.vel_x          = 0.0
        self.state          = "idle"
        print(f"[sombrio_boss] Stun! {effective:.1f}s (#{self._stun_count})", flush=True)

    def _start_death(self) -> None:
        self.is_dead      = True
        self.is_attacking = False
        self.is_casting   = False
        self.is_hurt      = False
        self.state        = "death"
        self._anim_state  = "death"
        self.frame_index  = 0
        self.anim_timer   = 0.0
        self._death_timer = 0.0
        self.death_alpha  = 255
        self.vel_x        = 0.0
        self.particles.clear()
        self.spells.clear()
        print(f"[sombrio_boss] DERROTADO! Morte ({DEATH_TOTAL:.1f}s) + fade ({FADE_DUR:.1f}s).", flush=True)

    def _get_attack_rect(self) -> pygame.Rect | None:
        if not self.is_attacking:
            return None
        reach = 115
        ax = self.hitbox.right if self.facing == 1 else self.hitbox.left - reach
        return pygame.Rect(ax, self.hitbox.centery - 46, reach, 92)

    # ─────────────────────────────────────────────────────────────────────────
    # DRAW
    # ─────────────────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface) -> None:
        # Magia renderizada antes do boss (atrás do sprite)
        for spell in self.spells:
            spell.draw(screen)

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

        # I-frames: piscar entre frame normal e frame tintado de vermelho
        if self.invincible_timer > 0:
            if int(self.invincible_timer * 12) % 2 == 1:
                screen.blit(self._get_tinted_frame(), self.rect)
                return

        screen.blit(self.image, self.rect)

    # ─────────────────────────────────────────────────────────────────────────
    # HUD — barra de vida com assets oficiais
    # ─────────────────────────────────────────────────────────────────────────

    def draw_hud(self, screen: pygame.Surface) -> None:
        if self.is_dead:
            return
        if self._hud_cache is None:
            self._hud_cache = self._build_hud_cache()
        if not self._hud_cache:
            self._draw_hud_fallback(screen)
            return

        c        = self._hud_cache
        hp_ratio = max(0.0, min(1.0, self._hud_hp / self.max_hp))

        # 1. Fundo/moldura da barra
        screen.blit(c['under'], (c['bar_x'], c['bar_y']))

        # 2. Preenchimento de HP recortado pela razão atual
        if c['prog']:
            fill_w = int(c['prog'].get_width() * hp_ratio)
            if fill_w > 0:
                screen.blit(
                    c['prog'],
                    (c['bar_x'] + c['prog_ox'], c['bar_y']),
                    area=pygame.Rect(0, 0, fill_w, c['prog'].get_height()),
                )

        # 3. Glow translúcido atrás do nome (desenhado antes do nome)
        if c.get('glow'):
            screen.blit(c['glow'], (c['glow_x'], c['glow_y']))

        # 4. Nome DENTRO do frame — sprite morthak_nome.png
        if c.get('name'):
            screen.blit(c['name'], (c['name_x'], c['name_y']))

        # 5. Mensagem adaptativa
        self._draw_adaptive_msg(screen)

    def _build_hud_cache(self) -> dict:
        from settings import SCREEN_WIDTH
        LIFE_DIR  = os.path.join(_DIR, "life")
        BAR_SCALE = 3

        def _load(fname: str) -> pygame.Surface | None:
            path = os.path.join(LIFE_DIR, fname)
            try:
                s = pygame.image.load(path).convert_alpha()
                print(f"[sombrio_boss HUD] '{fname}': {s.get_size()}", flush=True)
                return s
            except Exception as e:
                print(f"[sombrio_boss HUD] falha '{fname}': {e}", flush=True)
                return None

        under_raw = _load("morthak_health_under.png")
        prog_raw  = _load("morthak_health_progress.png")
        name_raw  = _load("morthak_nome.png")        # PNG 32-bit com alpha correto

        if under_raw is None:
            return {}

        # ── Escalar barra ──────────────────────────────────────────────────────
        bw    = under_raw.get_width()  * BAR_SCALE   # 480 px
        bh    = under_raw.get_height() * BAR_SCALE   # 192 px
        under = pygame.transform.scale(under_raw, (bw, bh))

        prog    = pygame.transform.scale(
            prog_raw,
            (prog_raw.get_width() * BAR_SCALE, prog_raw.get_height() * BAR_SCALE),
        ) if prog_raw else None
        prog_ox = (bw - prog.get_width()) // 2 if prog else 0

        bar_x = SCREEN_WIDTH // 2 - bw // 2
        bar_y = 10

        # ── Bounds do frame visível (medidos nos pixels nativos do under) ──────
        # morthak_health_under.png (160×64): frame em x=6..153, y=6..37
        FRAME_L = 6   * BAR_SCALE         # 18 px
        FRAME_T = 6   * BAR_SCALE         # 18 px
        FRAME_W = (153 - 6) * BAR_SCALE   # 441 px
        FRAME_H = (37  - 6) * BAR_SCALE   #  93 px

        frame_screen_x = bar_x + FRAME_L
        frame_screen_y = bar_y + FRAME_T

        # ── Sprite do nome: morthak_nome.png ──────────────────────────────────
        # PNG 32-bit com canal alpha — bounding-box medido: x=32..614, y=144..246
        # Mesmo pipeline do Umbrazoth: crop → scale → glow
        NAME_CROP = pygame.Rect(32, 144, 582, 102)

        name = glow = None
        name_x = name_y = glow_x = glow_y = 0

        if name_raw:
            iw, ih = name_raw.get_size()
            safe = pygame.Rect(
                min(NAME_CROP.x, iw - 1),
                min(NAME_CROP.y, ih - 1),
                min(NAME_CROP.w, iw - NAME_CROP.x),
                min(NAME_CROP.h, ih - NAME_CROP.y),
            )
            cropped = name_raw.subsurface(safe)

            # Escalar para 72% da largura do frame; altura proporcional
            name_w = int(FRAME_W * 0.72)                              # ≈ 317 px
            name_h = int(safe.height * name_w / max(safe.width, 1))  # ≈  55 px

            name = pygame.transform.scale(cropped, (max(1, name_w), max(1, name_h)))

            # Centralizar DENTRO do frame (horizontal + vertical)
            name_x = frame_screen_x + (FRAME_W - name_w) // 2
            name_y = frame_screen_y + (FRAME_H - name_h) // 2 + 38

            # Glow: cópia levemente maior com alpha ~27% — mesmo padrão do Umbrazoth
            glow_w = name_w + 6
            glow_h = name_h + 4
            glow   = pygame.transform.scale(cropped, (max(1, glow_w), max(1, glow_h)))
            glow.fill((255, 255, 255, 70), special_flags=pygame.BLEND_RGBA_MULT)
            glow_x = name_x - 3
            glow_y = name_y - 2

        print(
            f"[sombrio_boss HUD] name={name.get_size() if name else None} "
            f"pos=({name_x},{name_y})  "
            f"frame=({frame_screen_x},{frame_screen_y} {FRAME_W}x{FRAME_H})",
            flush=True,
        )

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

    def _draw_hud_fallback(self, screen: pygame.Surface) -> None:
        from settings import SCREEN_WIDTH, WHITE
        BAR_W, BAR_H = 340, 24
        bx = SCREEN_WIDTH // 2 - BAR_W // 2
        by = 12
        pygame.draw.rect(screen, (8, 4, 20),    (bx - 3, by - 3, BAR_W + 6, BAR_H + 6))
        pygame.draw.rect(screen, (20, 12, 40),  (bx, by, BAR_W, BAR_H))
        fill = max(0, int(BAR_W * self._hud_hp / self.max_hp))
        if fill > 0:
            pygame.draw.rect(screen, (100, 40, 180), (bx, by, fill, BAR_H))
            pygame.draw.rect(screen, (160, 90, 255), (bx, by, fill, 4))
        pygame.draw.rect(screen, (140, 80, 220), (bx, by, BAR_W, BAR_H), 2)
        font = pygame.font.SysFont("monospace", 13, bold=True)
        lbl  = font.render(f"MORTHAK  {self.hp}/{self.max_hp}", True, WHITE)
        screen.blit(lbl, (bx + BAR_W // 2 - lbl.get_width() // 2,
                          by + (BAR_H - lbl.get_height()) // 2))
        self._draw_adaptive_msg(screen)

    # ─────────────────────────────────────────────────────────────────────────
    # IA ADAPTATIVA — SEGUNDA CAMADA (APRENDIZADO EM COMBATE)
    # ─────────────────────────────────────────────────────────────────────────

    def on_projectile_fired(self) -> None:
        """Chamado por game.py a cada disparo do jogador."""
        self._rt['projeteis'] += 1
        if self._rt['projeteis'] >= 8 and not self._anti_ranged:
            self._anti_ranged = True
            self._show_msg("ADAPTAÇÃO CONCLUÍDA")
            print("[sombrio_boss] Adaptação: Anti-Ranged ativado", flush=True)

    def on_lightning_used(self) -> None:
        """Chamado por game.py a cada raio divino lançado."""
        self._rt['raios'] += 1

    def on_potion_used(self) -> None:
        """Chamado por game.py quando o jogador usa uma poção."""
        self._rt['pocoes'] += 1

    def on_player_rolled(self, direction: int) -> None:
        """Chamado por game.py no frame inicial de cada esquiva. direction = player.facing."""
        if direction < 0:
            self._rt['rolls_esq'] += 1
        else:
            self._rt['rolls_dir'] += 1
        self._update_roll_bias()

    def _show_msg(self, text: str, duration: float = 2.5) -> None:
        self._msg       = text
        self._msg_timer = duration

    def _update_phase(self) -> None:
        """Atualiza fase de HP (1→2→3) e dispara efeitos de escalada."""
        ratio = self.hp / max(self.max_hp, 1)
        if ratio > 0.66:
            new_phase = 1
        elif ratio > 0.33:
            new_phase = 2
        else:
            new_phase = 3
        if new_phase != self._phase:
            self._phase = new_phase
            msgs = {2: "ANALISANDO PADRÕES...", 3: "RESISTÊNCIA DESENVOLVIDA"}
            self._show_msg(msgs.get(new_phase, "ADAPTAÇÃO CONCLUÍDA"))
            print(f"[sombrio_boss] Fase {new_phase} (HP={self.hp})", flush=True)

    def _update_runtime(self, dt: float, player) -> None:
        """Acumula métricas de distância e conta regressiva da mensagem HUD."""
        if not player.alive:
            return
        dist = abs(player.hitbox.centerx - self.hitbox.centerx)
        if dist <= ATTACK_RANGE:
            self._rt['t_perto'] += dt
        else:
            self._rt['t_longe'] += dt
        if self._msg_timer > 0:
            self._msg_timer = max(0.0, self._msg_timer - dt)

    def _on_spell_miss(self) -> None:
        """Escalada da previsão de movimento a cada magia que erra o jogador."""
        self._spell_escapes += 1
        _PRED_TABLE = [0.25, 0.35, 0.45, 0.55]
        idx = min(self._spell_escapes - 1, len(_PRED_TABLE) - 1)
        old = self._pred_time
        self._pred_time = _PRED_TABLE[idx]
        if self._pred_time != old:
            self._show_msg("PREVISÃO APRIMORADA")
            print(f"[sombrio_boss] Previsão → {self._pred_time}s", flush=True)

    def _update_roll_bias(self) -> None:
        """Detecta padrão de esquiva (>70% numa direção) e configura viés de spell."""
        total = self._rt['rolls_esq'] + self._rt['rolls_dir']
        if total < 5:
            return
        old_bias = self._bias_dir
        if self._rt['rolls_esq'] / total > 0.70:
            self._bias_dir = -1
        elif self._rt['rolls_dir'] / total > 0.70:
            self._bias_dir = 1
        else:
            self._bias_dir = 0
        if self._bias_dir != old_bias and self._bias_dir != 0:
            self._show_msg("PADRÃO DETECTADO")
            print(f"[sombrio_boss] Roll bias → {self._bias_dir}", flush=True)

    def _effective_walk_speed(self) -> float:
        if self._phase == 3:
            return WALK_SPEED * 1.25
        if self._phase == 2:
            return WALK_SPEED * 1.15
        if self._anti_ranged:
            return WALK_SPEED * 1.20
        return WALK_SPEED

    def _effective_cast_cd(self) -> float:
        cd = CAST_CD
        if self._phase == 3:
            cd *= 0.75
        elif self._phase == 2:
            cd *= 0.85
        return cd

    def _effective_burst_cd(self) -> float:
        cd = self.burst_cd_max
        if self._phase == 3:
            cd *= 0.75
        return cd

    def _draw_adaptive_msg(self, screen: pygame.Surface) -> None:
        """Renderiza mensagem de adaptação na HUD (abaixo da barra de vida)."""
        if not self._msg or self._msg_timer <= 0:
            return
        from settings import SCREEN_WIDTH
        alpha = min(255, int(255 * min(1.0, self._msg_timer / 0.5)))
        surf  = self._msg_font.render(f"[ {self._msg} ]", True, (200, 100, 255))
        surf.set_alpha(alpha)
        x = SCREEN_WIDTH // 2 - surf.get_width() // 2
        screen.blit(surf, (x, 95))
