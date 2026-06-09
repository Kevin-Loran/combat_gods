"""
boss.py — Minotaur Boss (mino_v1.1_free).

Animações do pack (todas implementadas):
  idle   — 16 frames  (288×160 por frame, loop)
  walk   — 12 frames  (288×160 por frame, loop)
  atk_1  — 16 frames  (288×160 por frame, one-shot)

Animação de morte (sintética — pack free não inclui death dedicada):
  death  — atk_1 em reverse, distribuído por DEATH_ANIM_DURATION segundos.
            Após completar, fade-out suave de FADE_DURATION segundos.
            Boss só é removido quando death_alpha == 0.

Orientação dos sprites:
  Frames originais olham para a ESQUERDA.
  anims_left  = originais       (facing == -1)
  anims_right = espelhados      (facing == +1)

State Machine:
  idle  → walk  (player entra em AGGRO_RANGE)
  walk  → atk_1 (player entra em ATTACK_RANGE)
  walk  → idle  (player sai de AGGRO_RANGE)
  atk_1 → walk  (animação one-shot completa)
  hurt  → idle  (após HURT_FLASH segundos)
  death → removido após animação completa + fade

Dano:
  BUG 3 FIX: atk_hit_done garante exatamente 1 dano por swing.
  player.invincible_timer evita dano duplicado por frame.
  BOSS_DAMAGE = 1 coração por acerto.
"""

import pygame
import os
from particles import ParticleSystem

# ── Caminhos ──────────────────────────────────────────────────────────────────
_BOSS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "boss")

def _boss_path(*parts):
    return os.path.join(_BOSS_DIR, *parts)

# ── Escala e display ──────────────────────────────────────────────────────────
MINO_SCALE  = 1.8
MINO_RAW_W  = 288
MINO_RAW_H  = 160
MINO_DISP_W = int(MINO_RAW_W * MINO_SCALE)   # 518
MINO_DISP_H = int(MINO_RAW_H * MINO_SCALE)   # 288

# Foot offset: pés do personagem ficam 16px acima do bottom do canvas original
MINO_FOOT_PAD = int(16 * MINO_SCALE)   # ~28px

# ── Hitbox ────────────────────────────────────────────────────────────────────
MINO_HB_W = 80
MINO_HB_H = 120

# ── Parâmetros de IA ──────────────────────────────────────────────────────────
AGGRO_RANGE  = 480
ATTACK_RANGE = 110
WALK_SPEED   = 50    # px/s — pesado e ameaçador (era 62)

# ── HP ────────────────────────────────────────────────────────────────────────
MINO_MAX_HP = 20

# ── Duração das animações ─────────────────────────────────────────────────────
IDLE_SPF            = 0.14   # s/frame idle (era 0.13)
WALK_SPF            = 0.13   # s/frame walk (era 0.11)
ATK_DURATION        = 1.30   # duração total do ataque — wind-up legível (era 1.05)
HURT_FLASH          = 0.22   # duração do estado hurt
DEATH_ANIM_DURATION = 2.0    # duração dos 16 frames de morte
FADE_DURATION       = 0.9    # duração do fade-out após animação

# ── Cadência de ataque ────────────────────────────────────────────────────────
RECOVERY_DURATION = 0.65   # s — boss fica parado após cada swing (janela de punição)
ATTACK_COOLDOWN   = 1.05   # s — pausa mínima entre ataques (evita spam)

# ── Dano ──────────────────────────────────────────────────────────────────────
BOSS_DAMAGE            = 1    # 1 coração por acerto
ATK_HIT_FRAME          = 10   # frame de impacto (1-indexed)
CONTACT_DAMAGE_COOLDOWN = 1.2  # cooldown entre danos por contato corporal (s)


# ── Carregamento de frames ────────────────────────────────────────────────────

def _load_anim_frames(anim_name: str, num_frames: int) -> list[pygame.Surface]:
    """Carrega frames individuais e escala para MINO_DISP_W × MINO_DISP_H."""
    adir = _boss_path(anim_name)
    frames = []
    for i in range(1, num_frames + 1):
        path = os.path.join(adir, f"{anim_name}_{i}.png")
        try:
            img = pygame.image.load(path).convert_alpha()
            scaled = pygame.transform.scale(img, (MINO_DISP_W, MINO_DISP_H))
            frames.append(scaled)
        except Exception as e:
            print(f"[boss] ERRO ao carregar {path}: {e}", flush=True)
            # Fallback totalmente transparente (sem retângulo colorido)
            surf = pygame.Surface((MINO_DISP_W, MINO_DISP_H), pygame.SRCALPHA)
            frames.append(surf)
    print(f"[boss] {anim_name}: {len(frames)} frames ({MINO_DISP_W}×{MINO_DISP_H})", flush=True)
    return frames


def _flip_frames(frames: list[pygame.Surface]) -> list[pygame.Surface]:
    return [pygame.transform.flip(f, True, False) for f in frames]


def _tint_frame(frame: pygame.Surface, r: int, g: int, b: int, strength: int = 120) -> pygame.Surface:
    """
    Tinta um frame preservando o alpha original (sem numpy).
    Usa BLEND_ADD sobre uma cópia SRCALPHA: pixels transparentes continuam
    transparentes porque ADD(0, qualquer) = 0.
    """
    result = frame.copy()
    overlay = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
    # strength controla a intensidade; clamp para não estourar
    overlay.fill((min(r, strength), min(g, strength), min(b, strength), 0))
    result.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    return result


def _build_hurt_frame(base: pygame.Surface) -> pygame.Surface:
    """Frame de hurt: tint vermelho preservando alpha."""
    return _tint_frame(base, 255, 0, 0, 130)


def _load_healthbar_ui() -> dict:
    ui = {}
    for name in ("mino_health_under", "mino_health_progress", "mino_health_over"):
        path = _boss_path("ui", f"{name}.png")
        try:
            ui[name] = pygame.image.load(path).convert_alpha()
            print(f"[boss] UI '{name}': {ui[name].get_size()}", flush=True)
        except Exception as e:
            print(f"[boss] ERRO UI {path}: {e}", flush=True)
            ui[name] = None
    return ui


# ── Classe Principal ──────────────────────────────────────────────────────────

class MinotaurBoss(pygame.sprite.Sprite):

    def __init__(self, x: int, y: int):
        super().__init__()

        # ── Carregar animações do pack ────────────────────────────────────
        idle_r  = _load_anim_frames("idle",  16)
        walk_r  = _load_anim_frames("walk",  12)
        atk1_r  = _load_anim_frames("atk_1", 16)

        # Morte sintética: atk_1 em reverse (personagem "desfaz" o golpe)
        death_r = list(reversed(atk1_r))

        # Hurt: frame tintado de vermelho respeitando alpha
        hurt_r = [_build_hurt_frame(idle_r[0])]

        # Orientação: sprites originais olham para a ESQUERDA
        self.anims_left = {
            "idle":  idle_r,
            "walk":  walk_r,
            "atk_1": atk1_r,
            "hurt":  hurt_r,
            "death": death_r,
        }
        self.anims_right = {k: _flip_frames(v) for k, v in self.anims_left.items()}

        # Pré-calcular frames de i-frame tint para evitar cálculo por frame
        # Tint vermelho claro para piscar durante invencibilidade
        self._iframes_tint_left  = {k: [_tint_frame(f, 200, 0, 0, 80) for f in v]
                                     for k, v in self.anims_left.items()}
        self._iframes_tint_right = {k: _flip_frames(v)
                                    for k, v in self._iframes_tint_left.items()}

        # ── UI da healthbar ───────────────────────────────────────────────
        self.ui = _load_healthbar_ui()

        # ── Estado ────────────────────────────────────────────────────────
        self.state       = "idle"
        self._anim_state = "idle"
        self.facing      = -1      # começa olhando para a esquerda
        self.frame_index = 0
        self.anim_timer  = 0.0

        # ── Ataque ────────────────────────────────────────────────────────
        self.is_attacking    = False
        self.atk_finished    = False
        self.atk_hit_done    = False
        self._atk_spf        = ATK_DURATION / 16

        # ── Recovery (pausa após ataque) ──────────────────────────────────
        self.is_recovering   = False
        self.recovery_timer  = 0.0
        self.attack_cooldown = 0.0

        # ── Partículas ────────────────────────────────────────────────────
        self.particles       = ParticleSystem()
        self._atk_vfx_done   = False   # emite burst só uma vez por swing
        self._footstep_timer = 0.0

        # ── Stun (Raio Divino) ────────────────────────────────────────────
        self.is_stunned = False
        self.stun_timer = 0.0

        # ── Hurt ──────────────────────────────────────────────────────────
        self.is_hurt          = False
        self.hurt_timer       = 0.0
        self.invincible_timer = 0.0

        # ── Dano por contato ──────────────────────────────────────────────
        self.contact_cooldown = 0.0   # cooldown para evitar dano contínuo

        # ── Morte ─────────────────────────────────────────────────────────
        self.is_dead     = False
        self.death_timer = 0.0   # tempo desde início da morte
        self.death_alpha = 255   # 255 = totalmente visível, 0 = despawn

        # ── Física ────────────────────────────────────────────────────────
        self.vel_x = 0.0

        # ── HP ────────────────────────────────────────────────────────────
        self.hp     = MINO_MAX_HP
        self.max_hp = MINO_MAX_HP

        # ── Hitbox / rect ─────────────────────────────────────────────────
        self.hitbox = pygame.Rect(0, 0, MINO_HB_W, MINO_HB_H)
        self.hitbox.midbottom = (x, y)
        self.image = self._current_frame()
        self.rect  = self.image.get_rect()
        self._align_rect()

        print(
            f"[boss] MinotaurBoss criado em ({x},{y})  "
            f"hitbox={self.hitbox}  display={MINO_DISP_W}×{MINO_DISP_H}",
            flush=True
        )

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE
    # ─────────────────────────────────────────────────────────────────────────

    def update(self, dt: float, platforms, player, projectiles=None):
        self.invincible_timer = max(0.0, self.invincible_timer - dt)
        self.contact_cooldown = max(0.0, self.contact_cooldown - dt)
        self.attack_cooldown  = max(0.0, self.attack_cooldown  - dt)
        self._footstep_timer  = max(0.0, self._footstep_timer  - dt)
        self.stun_timer       = max(0.0, self.stun_timer        - dt)
        if self.stun_timer <= 0.0:
            self.is_stunned = False
        self.particles.update(dt)

        # Morte: avança animação + fade, ignora tudo mais
        if self.is_dead:
            self._update_death(dt)
            return

        # Hurt
        if self.is_hurt:
            self.hurt_timer = max(0.0, self.hurt_timer - dt)
            if self.hurt_timer <= 0.0:
                self.is_hurt = False
                self.state   = "idle"

        # Liberar ataque — entra em recovery ao invés de voltar direto ao walk
        if self.is_attacking and self.atk_finished:
            self.is_attacking    = False
            self.atk_finished    = False
            self.atk_hit_done    = False
            self.is_recovering   = True
            self.recovery_timer  = RECOVERY_DURATION
            self.attack_cooldown = ATTACK_COOLDOWN
            self.state           = "idle"
            self.vel_x           = 0.0
            self.particles.emit_recovery(self.hitbox.centerx, self.hitbox.bottom)

        # Recovery: boss parado, sem atacar — janela de punição para o jogador
        if self.is_recovering:
            self.recovery_timer -= dt
            self.vel_x = 0.0
            if self.recovery_timer <= 0.0:
                self.is_recovering = False
                self.state         = "walk"

        # Stun (Raio Divino): imobiliza o boss completamente
        if self.is_stunned:
            self.vel_x = 0.0

        # IA — só roda fora de hurt, ataque, recovery e stun
        if not self.is_hurt and not self.is_attacking and not self.is_recovering and not self.is_stunned:
            self._run_ai(dt, player)

        # Física
        self._physics(dt, platforms)

        # Footstep dust — emite a cada ~0.25s enquanto caminha
        if self.state == "walk" and abs(self.vel_x) > 1 and self._footstep_timer <= 0:
            self._footstep_timer = 0.25
            self.particles.emit_footstep(self.hitbox.centerx, self.hitbox.bottom, self.facing)

        # Dano por ataque (1 hit por swing via atk_hit_done)
        if self.is_attacking and not self.atk_hit_done:
            if self.frame_index >= ATK_HIT_FRAME - 1:
                atk_rect = self._get_attack_rect()
                if atk_rect and player.alive and atk_rect.colliderect(player.hitbox):
                    player.take_damage(BOSS_DAMAGE)
                    self.atk_hit_done = True

        # VFX burst no frame de impacto — independente de acertar o player
        if self.is_attacking and not self._atk_vfx_done and self.frame_index >= ATK_HIT_FRAME - 1:
            atk_rect = self._get_attack_rect()
            ex = atk_rect.centerx if atk_rect else self.hitbox.centerx
            ey = atk_rect.centery if atk_rect else self.hitbox.centery
            self.particles.emit_impact(ex, ey, self.facing)
            self._atk_vfx_done = True

        # Dano por contato corporal — sem dano durante roll (player intangível)
        if not self.is_dead and player.alive and self.contact_cooldown <= 0:
            if self.hitbox.colliderect(player.hitbox) and not player.is_rolling:
                player.take_damage(BOSS_DAMAGE)
                self.contact_cooldown = CONTACT_DAMAGE_COOLDOWN

        # Animação
        self._animate(dt)

    # ─────────────────────────────────────────────────────────────────────────
    # IA
    # ─────────────────────────────────────────────────────────────────────────

    def _run_ai(self, dt: float, player):
        if not player.alive:
            self.state = "idle"
            self.vel_x = 0.0
            return

        dx   = player.hitbox.centerx - self.hitbox.centerx
        dist = abs(dx)

        if dx != 0:
            self.facing = 1 if dx > 0 else -1

        if dist <= ATTACK_RANGE and not self.is_attacking and self.attack_cooldown <= 0:
            self.state           = "atk_1"
            self.is_attacking    = True
            self.atk_finished    = False
            self.atk_hit_done    = False
            self._atk_vfx_done   = False
            self.frame_index     = 0
            self.anim_timer      = 0.0
            self.vel_x           = 0.0
            self.particles.emit_stomp(self.hitbox.centerx, self.hitbox.bottom)
        elif dist <= AGGRO_RANGE:
            self.state = "walk"
            self.vel_x = WALK_SPEED * self.facing
        else:
            self.state = "idle"
            self.vel_x = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # FÍSICA
    # ─────────────────────────────────────────────────────────────────────────

    def _physics(self, dt: float, platforms):
        if self.vel_x != 0.0:
            self.hitbox.x += round(self.vel_x * dt)
            self._resolve_x(platforms)
        self._align_rect()

    def _resolve_x(self, platforms):
        for plat in platforms:
            pr = plat.solid_rect
            if not self.hitbox.colliderect(pr):
                continue
            if self.vel_x > 0:
                self.hitbox.right = pr.left
            elif self.vel_x < 0:
                self.hitbox.left  = pr.right
            self.vel_x = 0.0

    def _align_rect(self):
        self.rect.midbottom = (
            self.hitbox.centerx,
            self.hitbox.bottom + MINO_FOOT_PAD
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ANIMAÇÃO
    # ─────────────────────────────────────────────────────────────────────────

    def _animate(self, dt: float):
        # Prioridade de estado visual — ataque NÃO é interrompido por hurt
        if self.is_dead:
            new_state = "death"
        elif self.is_attacking:
            new_state = "atk_1"
        elif self.is_hurt:
            new_state = "hurt"
        elif self.state == "walk" and abs(self.vel_x) > 1:
            new_state = "walk"
        else:
            new_state = "idle"

        # Reset ao mudar de estado
        if new_state != self._anim_state:
            self._anim_state = new_state
            self.frame_index = 0
            self.anim_timer  = 0.0

        frames = self._get_anim(new_state)
        if not frames:
            return

        # SPF por estado
        if new_state == "atk_1":
            spf = self._atk_spf
        elif new_state == "walk":
            spf = WALK_SPF
        elif new_state == "hurt":
            spf = HURT_FLASH / max(len(frames), 1)
        elif new_state == "death":
            spf = DEATH_ANIM_DURATION / max(len(frames), 1)
        else:
            spf = IDLE_SPF

        self.anim_timer += dt
        if self.anim_timer >= spf:
            self.anim_timer -= spf
            if new_state in ("atk_1", "hurt", "death"):
                # One-shot: avança até o último e trava
                if self.frame_index < len(frames) - 1:
                    self.frame_index += 1
                elif new_state == "atk_1":
                    self.atk_finished = True
                # death trava no último frame e espera o fade
            else:
                # Loop: idle, walk
                self.frame_index = (self.frame_index + 1) % len(frames)

        self.image = frames[self.frame_index]

    def _get_anim(self, state: str | None = None) -> list:
        s    = state if state is not None else self._anim_state
        bank = self.anims_right if self.facing == 1 else self.anims_left
        return bank.get(s, bank["idle"])

    def _current_frame(self) -> pygame.Surface:
        frames = self._get_anim()
        return frames[self.frame_index % len(frames)]

    def _get_iframes_frame(self) -> pygame.Surface:
        """Frame tintado de vermelho para o efeito de piscar durante i-frames."""
        s    = self._anim_state
        bank = self._iframes_tint_right if self.facing == 1 else self._iframes_tint_left
        frames = bank.get(s, bank["idle"])
        idx = min(self.frame_index, len(frames) - 1)
        return frames[idx]

    # ─────────────────────────────────────────────────────────────────────────
    # MORTE
    # ─────────────────────────────────────────────────────────────────────────

    def _update_death(self, dt: float):
        """
        Fase 1 (0 → DEATH_ANIM_DURATION): animação roda, sem fade.
        Fase 2 (DEATH_ANIM_DURATION → +FADE_DURATION): fade out 255 → 0.
        """
        self.death_timer += dt
        self._animate(dt)   # continua avançando os frames da morte

        if self.death_timer >= DEATH_ANIM_DURATION:
            fade_progress    = (self.death_timer - DEATH_ANIM_DURATION) / FADE_DURATION
            self.death_alpha = max(0, int(255 * (1.0 - fade_progress)))
        else:
            self.death_alpha = 255

    @property
    def should_be_removed(self) -> bool:
        """True somente após animação completa E fade zerado."""
        return self.is_dead and self.death_alpha <= 0

    # ─────────────────────────────────────────────────────────────────────────
    # COMBAT
    # ─────────────────────────────────────────────────────────────────────────

    def take_damage(self, amount: int = 1):
        if self.invincible_timer > 0 or self.is_dead:
            return

        self.hp -= amount
        self.invincible_timer = 0.4   # i-frames após cada hit

        if self.hp <= 0:
            self.hp = 0
            self._start_death()
        else:
            self.is_hurt    = True
            self.hurt_timer = HURT_FLASH
            # Ataque NÃO é cancelado — boss commita o swing inteiro

        print(f"[boss] dano recebido! HP={self.hp}/{self.max_hp}", flush=True)

    def stun(self, duration: float) -> None:
        """Paralisa o boss pelo tempo dado (Raio Divino). Cancela ação em andamento."""
        if self.is_dead:
            return
        self.is_stunned    = True
        self.stun_timer    = duration
        self.is_attacking  = False
        self.atk_finished  = False
        self.is_recovering = False
        self.is_hurt       = False
        self.vel_x         = 0.0
        self.state         = "idle"
        print(f"[boss] Stun! {duration:.1f}s", flush=True)

    def _start_death(self):
        self.is_dead      = True
        self.is_attacking = False
        self.is_hurt      = False
        self.state        = "death"
        self._anim_state  = "death"
        self.frame_index  = 0
        self.anim_timer   = 0.0
        self.death_timer  = 0.0
        self.death_alpha  = 255
        self.vel_x        = 0.0
        self.particles.clear()
        print(f"[boss] BOSS DERROTADO! Animação de morte ({DEATH_ANIM_DURATION:.1f}s) iniciada.", flush=True)

    def _get_attack_rect(self) -> pygame.Rect | None:
        if not self.is_attacking:
            return None
        reach = 100
        if self.facing == 1:
            ax = self.hitbox.right
        else:
            ax = self.hitbox.left - reach
        return pygame.Rect(ax, self.hitbox.centery - 40, reach, 80)

    # ─────────────────────────────────────────────────────────────────────────
    # DRAW — SEM RETÂNGULO CINZA
    # ─────────────────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface):
        """
        Regras de renderização:
        1. Morte: blit normal + set_alpha para fade. set_alpha em surface
           SRCALPHA age sobre TODOS os pixels (incluindo os opacos) sem
           criar retângulo — comportamento correto.
        2. I-frames: alterna entre frame normal e frame pré-tintado.
           Pré-tintado foi gerado com _tint_frame() que preserva alpha.
           NENHUM blit com surface sem SRCALPHA sobre surface com SRCALPHA.
        """
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

        # I-frames: piscar alternando frame normal / frame tintado (pré-calculado)
        if self.invincible_timer > 0:
            tick = int(self.invincible_timer * 12) % 2
            if tick == 1:
                screen.blit(self._get_iframes_frame(), self.rect)
                return

        screen.blit(self.image, self.rect)

    # ─────────────────────────────────────────────────────────────────────────
    # HUD — healthbar com assets oficiais
    # ─────────────────────────────────────────────────────────────────────────

    def draw_hud(self, screen: pygame.Surface):
        if self.is_dead:
            return

        BAR_SCALE  = 3.0
        ui         = self.ui
        under_surf = ui.get("mino_health_under")
        prog_surf  = ui.get("mino_health_progress")
        over_surf  = ui.get("mino_health_over")

        if under_surf is None:
            self._draw_fallback_bar(screen)
            return

        def scaled(surf):
            if surf is None:
                return None
            return pygame.transform.scale(
                surf,
                (int(surf.get_width() * BAR_SCALE), int(surf.get_height() * BAR_SCALE))
            )

        under = scaled(under_surf)
        prog  = scaled(prog_surf)
        over  = scaled(over_surf)

        from settings import SCREEN_WIDTH
        bar_x = SCREEN_WIDTH // 2 - under.get_width() // 2
        bar_y = 10

        screen.blit(under, (bar_x, bar_y))

        if prog:
            hp_ratio = self.hp / self.max_hp
            fill_w   = int(prog.get_width() * hp_ratio)
            offset_x = (under.get_width() - prog.get_width()) // 2
            if fill_w > 0:
                screen.blit(prog, (bar_x + offset_x, bar_y),
                            area=pygame.Rect(0, 0, fill_w, prog.get_height()))

        if over:
            screen.blit(over, (bar_x, bar_y))

    def _draw_fallback_bar(self, screen: pygame.Surface):
        from settings import SCREEN_WIDTH, WHITE
        BAR_W, BAR_H = 300, 18
        bx = SCREEN_WIDTH // 2 - BAR_W // 2
        by = 12
        pygame.draw.rect(screen, (40, 10, 10),   (bx, by, BAR_W, BAR_H))
        fill = int(BAR_W * self.hp / self.max_hp)
        pygame.draw.rect(screen, (200, 30, 30),  (bx, by, fill, BAR_H))
        pygame.draw.rect(screen, (255, 100, 100), (bx, by, BAR_W, BAR_H), 2)
        font = pygame.font.SysFont("monospace", 13, bold=True)
        lbl  = font.render(f"BOSS  {self.hp}/{self.max_hp}", True, WHITE)
        screen.blit(lbl, (bx + BAR_W // 2 - lbl.get_width() // 2, by + 1))
