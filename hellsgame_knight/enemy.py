"""
enemy.py — Inimigos do jogo.

ALTERAÇÕES
----------
- SlimeEnemy REMOVIDO.
- SkeletonEnemy ADICIONADO (substitui Slime) — anda no chão, persegue player,
  animações completas: idle / walk / attack / take_hit / shield / death.
- DemonEnemy: persegue player no chão (usa gravidade + plataforma).
- FlyingDemonEnemy: flutua no ar em altura fixa, persegue player horizontalmente.
- Todos os inimigos têm o player como alvo.
- Bola de fogo: cooldown de 6s, disparo único, direção calculada para o player.
"""

import math
import pygame
from settings import *
from sprite_utils import load_sheet, flip_frames

# ── Frame sizes ───────────────────────────────────────────────────────────────
DEMON_W, DEMON_H   = 112, 166
SKEL_W,  SKEL_H    = 150, 150   # todas as sheets da caveira são 150×150
DROP_W,  DROP_H    = 128, 122

# ── Helper: fundo preto → transparente ───────────────────────────────────────
def _make_black_transparent(frames: list, threshold: int = 20) -> list:
    result = []
    for frame in frames:
        surf = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
        surf.blit(frame, (0, 0))
        w, h = surf.get_size()
        pixels = pygame.PixelArray(surf)
        for x in range(w):
            for y in range(h):
                col = surf.unmap_rgb(pixels[x, y])
                r, g, b = col[0], col[1], col[2]
                if r < threshold and g < threshold and b < threshold:
                    pixels[x, y] = surf.map_rgb(0, 0, 0, 0)
        del pixels
        result.append(surf)
    return result


_ENEMY_SHEET_CACHE: dict[tuple, list] = {}


def _load_demon_sheet(path, frame_w, frame_h, cols, scale=1.0):
    key = ("demon", path, frame_w, frame_h, cols, float(scale))
    if key in _ENEMY_SHEET_CACHE:
        return _ENEMY_SHEET_CACHE[key]
    frames = load_sheet(path, frame_w, frame_h, rows=1, cols=cols, scale=scale)
    out = _make_black_transparent(frames)
    _ENEMY_SHEET_CACHE[key] = out
    print(f"[enemy] carregando sprite (cached): {path} cols={cols} scale={scale}", flush=True)
    return out


def _crop_enemy_frames(frames, padding=4):
    """Remove padding transparente dos frames usando apenas pygame (sem numpy)."""
    cropped = []
    for surf in frames:
        rect = surf.get_bounding_rect(min_alpha=10)
        if rect.width <= 0 or rect.height <= 0:
            cropped.append(surf)
            continue
        x1 = max(0, rect.left   - padding)
        y1 = max(0, rect.top    - padding)
        x2 = min(surf.get_width(),  rect.right  + padding)
        y2 = min(surf.get_height(), rect.bottom + padding)
        w, h = x2 - x1, y2 - y1
        new_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        new_surf.blit(surf, (0, 0), area=pygame.Rect(x1, y1, w, h))
        cropped.append(new_surf)
    return cropped


def _load_skel_sheet(path, cols, scale=1.5):
    """Carrega sheet da caveira (fundo preto → transparente, padding removido)."""
    key = ("skel", path, cols, float(scale))
    if key in _ENEMY_SHEET_CACHE:
        return _ENEMY_SHEET_CACHE[key]
    frames = load_sheet(path, SKEL_W, SKEL_H, rows=1, cols=cols, scale=scale)
    out = _crop_enemy_frames(_make_black_transparent(frames))
    _ENEMY_SHEET_CACHE[key] = out
    print(f"[enemy] carregando sprite (cached): {path} cols={cols} scale={scale}", flush=True)
    return out


# ══════════════════════════════════════════════════════════════════════════════
#  BASE ENEMY
# ══════════════════════════════════════════════════════════════════════════════

class BaseEnemy(pygame.sprite.Sprite):
    MAX_HP     = 3
    SPEED      = 80
    DAMAGE     = 1
    ANIM_SPEED = 7.0

    def __init__(self, x, y, frames_right):
        super().__init__()
        self.frames_right = frames_right
        self.frames_left  = flip_frames(frames_right)
        self.facing       = -1
        self.frame_index  = 0.0

        self.image = self.frames_right[0]
        self.rect  = self.image.get_rect(midbottom=(x, y))
        self.hitbox = self.rect.inflate(
            -int(self.rect.width * 0.15),
            -int(self.rect.height * 0.1)
        ).copy()

        self.hp              = self.MAX_HP
        self.vel_y           = 0.0
        self.hit_flash_timer = 0.0
        self._pooled = False
        self._pool_ref = None

    def set_pool(self, pool):
        self._pool_ref = pool
        self._pooled = pool is not None

    def kill(self):
        # Se tiver pool, libera para reuso após remover dos grupos.
        super().kill()
        if self._pooled and self._pool_ref is not None:
            try:
                self._pool_ref.release(self)
            except Exception:
                pass

    def reset_common(self, x: int, y: int):
        self.hp = self.MAX_HP
        self.vel_y = 0.0
        self.hit_flash_timer = 0.0
        self.frame_index = 0.0
        # reposiciona
        self.rect = self.image.get_rect(midbottom=(x, y))
        self.hitbox = self.rect.inflate(
            -int(self.rect.width * 0.15),
            -int(self.rect.height * 0.1)
        ).copy()
        self.hitbox.midbottom = self.rect.midbottom
        self._fy_acc = float(self.hitbox.y)
    def _apply_gravity_and_land(self, dt, platforms):
        # Acumulador float — evita int() truncar vel_y pequena (BUG histórico:
        # int(15 * 1/60) = 0 → inimigo imóvel por vários frames → afunda)
        if not hasattr(self, "_fy_acc"):
            self._fy_acc = float(self.hitbox.y)

        self.vel_y   += GRAVITY * dt
        self.vel_y    = min(self.vel_y, 900)
        self._fy_acc += self.vel_y * dt
        self.hitbox.y = round(self._fy_acc)

        # Probe expandido 1px detecta "touching" (colliderect retorna False
        # quando hitbox.bottom == solid_rect.top — apenas encostam sem overlap)
        probe = self.hitbox.inflate(0, 2)
        for plat in platforms:
            pr = plat.solid_rect
            if probe.colliderect(pr) and self.vel_y >= 0:
                self.hitbox.bottom = pr.top
                self._fy_acc       = float(self.hitbox.y)
                self.vel_y         = 0
                break

        self.rect.midbottom = (self.hitbox.centerx, self.hitbox.bottom)

    def _animate(self, dt):
        frames = self.frames_right if self.facing == 1 else self.frames_left
        self.frame_index = (self.frame_index + self.ANIM_SPEED * dt) % len(frames)
        self.image = frames[int(self.frame_index)]

    def take_damage(self, amount: int = 1):
        self.hp -= amount
        self.hit_flash_timer = 0.15
        if self.hp <= 0:
            self.kill()

    def draw(self, screen: pygame.Surface):
        if self.hit_flash_timer > 0:
            flash = self.image.copy()
            flash.fill((255, 255, 255, 160), special_flags=pygame.BLEND_RGBA_ADD)
            screen.blit(flash, self.rect)
        else:
            screen.blit(self.image, self.rect)
        self._draw_hp_bar(screen)

    def _draw_hp_bar(self, screen: pygame.Surface):
        bar_w = self.rect.width
        bar_h = 5
        bx    = self.rect.left
        by    = self.rect.top - 8
        ratio = max(0.0, self.hp / self.MAX_HP)
        pygame.draw.rect(screen, (60, 0, 0),   (bx, by, bar_w, bar_h))
        pygame.draw.rect(screen, (200, 30, 30), (bx, by, int(bar_w * ratio), bar_h))

    def _tick_flash(self, dt):
        self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)


# ══════════════════════════════════════════════════════════════════════════════
#  SKELETON ENEMY — substitui o Slime
# ══════════════════════════════════════════════════════════════════════════════

class SkeletonEnemy(BaseEnemy):
    """
    Caveira guerreira que anda no chão e persegue o player.

    Animações:
        idle     — parado (4 frames)
        walk     — andando (4 frames)
        attack   — ataque corpo a corpo (8 frames)
        take_hit — leva dano (4 frames)
        shield   — bloqueio (4 frames) — usado ao receber dano com HP alto
        death    — morte (4 frames)

    Sprites: assets/skeleton_*.png (150×150 px por frame, fundo preto)
    """
    MAX_HP      = 3
    SPEED       = 70
    DAMAGE      = 1
    MELEE_RANGE = 60
    AGGRO_RANGE = 500
    ANIM_SPEED  = 8.0

    STATE_IDLE    = "idle"
    STATE_WALK    = "walk"
    STATE_ATTACK  = "attack"
    STATE_HURT    = "hurt"
    STATE_DEATH   = "death"

    def __init__(self, x, y, frames_override=None, _player=None):
        # scale=3.3 -> conteudo visual ~167px (maior que player 152px)
        SCALE = 3.3
        # Cache + pré-flip (CRÍTICO: não flipar a cada frame)
        if not hasattr(SkeletonEnemy, "_ANIM_CACHE"):
            SkeletonEnemy._ANIM_CACHE = {}
        cache_key = ("skel_anim", float(SCALE))
        if cache_key not in SkeletonEnemy._ANIM_CACHE:
            right = {
                self.STATE_IDLE:   _load_skel_sheet(SKEL_IDLE_SHEET,    cols=4, scale=SCALE),
                self.STATE_WALK:   _load_skel_sheet(SKEL_WALK_SHEET,    cols=4, scale=SCALE),
                self.STATE_ATTACK: _load_skel_sheet(SKEL_ATTACK_SHEET,  cols=8, scale=SCALE),
                self.STATE_HURT:   _load_skel_sheet(SKEL_HIT_SHEET,     cols=4, scale=SCALE),
                self.STATE_DEATH:  _load_skel_sheet(SKEL_DEATH_SHEET,   cols=4, scale=SCALE),
            }
            left = {k: flip_frames(v) for k, v in right.items()}
            SkeletonEnemy._ANIM_CACHE[cache_key] = (right, left)

        self._anim_right, self._anim_left = SkeletonEnemy._ANIM_CACHE[cache_key]
        # Se chamado pelo import_monsters com frames externos, substitui idle/walk
        if frames_override is not None:
            self._anim_right = dict(self._anim_right)
            self._anim_left = dict(self._anim_left)
            self._anim_right[self.STATE_IDLE] = frames_override
            self._anim_right[self.STATE_WALK] = frames_override
            self._anim_left[self.STATE_IDLE] = flip_frames(frames_override)
            self._anim_left[self.STATE_WALK] = flip_frames(frames_override)

        super().__init__(x, y, self._anim_right[self.STATE_IDLE])
        # FIX #2 — garantir que rect.midbottom == hitbox.midbottom após __init__
        self.rect.midbottom = self.hitbox.midbottom

        self.state         = self.STATE_IDLE
        self._state_frame  = 0.0
        self._hurt_timer   = 0.0
        self._attack_cd    = 0.0
        self._dead         = False
        self._hit_this_atk = False   # dano ao player uma vez por swing

    def reset(self, x: int, y: int, frames_override=None):
        # Reuso via pool
        if frames_override is not None:
            self._anim_right[self.STATE_IDLE] = frames_override
            self._anim_right[self.STATE_WALK] = frames_override
            self._anim_left[self.STATE_IDLE] = flip_frames(frames_override)
            self._anim_left[self.STATE_WALK] = flip_frames(frames_override)

        self.frames_right = self._anim_right[self.STATE_IDLE]
        self.frames_left = self._anim_left[self.STATE_IDLE]
        self.facing = -1
        self.state = self.STATE_IDLE
        self._state_frame = 0.0
        self._hurt_timer = 0.0
        self._attack_cd = 0.0
        self._dead = False
        self._hit_this_atk = False
        self.image = self._anim_right[self.STATE_IDLE][0]
        self.reset_common(x, y)

    # ── Estado ─────────────────────────────────────────────────────────────

    def _set_state(self, s):
        if self.state != s:
            self.state       = s
            self._state_frame = 0.0

    def _get_frames(self, state, facing):
        bank = self._anim_right if facing == 1 else self._anim_left
        return bank[state]

    def _advance(self, dt) -> bool:
        n = len(self._get_frames(self.state, self.facing))
        self._state_frame += self.ANIM_SPEED * dt
        if self._state_frame >= n:
            self._state_frame %= n
            return True
        return False

    def _cur_image(self):
        frames = self._get_frames(self.state, self.facing)
        return frames[int(self._state_frame) % len(frames)]

    # ── Dano ───────────────────────────────────────────────────────────────

    def take_damage(self, amount: int = 1):
        if self._dead:
            return
        self.hp -= amount
        self.hit_flash_timer = 0.12
        if self.hp <= 0:
            self._dead = True
            self._set_state(self.STATE_DEATH)
        else:
            self._set_state(self.STATE_HURT)
            self._hurt_timer = 0.35

    # ── Update ─────────────────────────────────────────────────────────────

    def update(self, dt, platforms, player, projectiles):
        # Morte
        if self._dead:
            done = self._advance(dt)
            self.image = self._cur_image()
            self._apply_gravity_and_land(dt, platforms)
            if done:
                self.kill()
            return

        # Hurt
        if self.state == self.STATE_HURT:
            self._hurt_timer -= dt
            self._advance(dt)
            self.image = self._cur_image()
            self._tick_flash(dt)
            self._apply_gravity_and_land(dt, platforms)
            if self._hurt_timer <= 0:
                self._set_state(self.STATE_WALK)
            return

        dx = player.rect.centerx - self.rect.centerx
        dist = abs(dx)
        self.facing = 1 if dx > 0 else -1
        self._attack_cd = max(0.0, self._attack_cd - dt)

        # Ataque corpo a corpo
        if self.state == self.STATE_ATTACK:
            prev = int(self._state_frame)
            done = self._advance(dt)
            curr = int(self._state_frame)
            self.image = self._cur_image()
            # Aplica dano no frame 3 (meio do swing)
            if prev < 3 <= curr and not self._hit_this_atk:
                self._hit_this_atk = True
                if dist < self.MELEE_RANGE + 20:
                    player.take_damage(self.DAMAGE)
            if done:
                self._hit_this_atk = False
                self._set_state(self.STATE_WALK)
            self._apply_gravity_and_land(dt, platforms)
            return

        # Persegue / idle
        if dist < self.AGGRO_RANGE:
            if dist < self.MELEE_RANGE and self._attack_cd == 0.0:
                self._set_state(self.STATE_ATTACK)
                self._state_frame  = 0.0
                self._hit_this_atk = False
                self._attack_cd    = 1.2
            else:
                self._set_state(self.STATE_WALK)
                move = int(self.SPEED * dt * self.facing)
                self.hitbox.x += move
        else:
            self._set_state(self.STATE_IDLE)

        self._apply_gravity_and_land(dt, platforms)
        self._advance(dt)
        self.image = self._cur_image()
        self._tick_flash(dt)

    def draw(self, screen):
        screen.blit(self.image, self.rect)
        self._draw_hp_bar(screen)


# ══════════════════════════════════════════════════════════════════════════════
#  DEMON ENEMY — persegue player no chão
# ══════════════════════════════════════════════════════════════════════════════

class DemonEnemy(BaseEnemy):
    MAX_HP      = 5
    SPEED       = 85
    DAMAGE      = 1
    MELEE_RANGE = 55
    AGGRO_RANGE = 500

    def __init__(self, x, y):
        frames = load_sheet(DEMON_SHEET, DEMON_W, DEMON_H, rows=2, cols=6)
        super().__init__(x, y, frames)
        self.attack_cd = 0.0

    def update(self, dt, platforms, player, projectiles):
        dx = player.rect.centerx - self.rect.centerx
        if abs(dx) < self.AGGRO_RANGE:
            self.facing    = 1 if dx > 0 else -1
            move = int(self.SPEED * dt * self.facing)
            self.hitbox.x += move

        self._apply_gravity_and_land(dt, platforms)
        self._animate(dt)
        self._tick_flash(dt)

        self.attack_cd = max(0.0, self.attack_cd - dt)
        if abs(dx) < self.MELEE_RANGE and self.attack_cd == 0.0:
            player.take_damage(self.DAMAGE)
            self.attack_cd = 1.1


# ══════════════════════════════════════════════════════════════════════════════
#  FLYING DEMON PROJECTILE — bola de fogo
# ══════════════════════════════════════════════════════════════════════════════

class FlyingDemonProjectile(pygame.sprite.Sprite):
    SPEED = 320

    def __init__(self, x, y, dir_x: float, dir_y: float = 0.0):
        super().__init__()
        # Cache de frames (CRÍTICO: não carregar sheet a cada projétil)
        if not hasattr(FlyingDemonProjectile, "_FRAMES_CACHE"):
            FlyingDemonProjectile._FRAMES_CACHE = {}
        k = ("proj", float(2.0))
        if k not in FlyingDemonProjectile._FRAMES_CACHE:
            fr = _load_demon_sheet(
                FLYING_DEMON_PROJ_SHEET,
                FLYING_DEMON_PROJ_W, FLYING_DEMON_PROJ_H,
                cols=1, scale=2.0
            )
            FlyingDemonProjectile._FRAMES_CACHE[k] = (fr, flip_frames(fr))

        right_frames, left_frames = FlyingDemonProjectile._FRAMES_CACHE[k]
        self.frame_index = 0.0

        length = math.hypot(dir_x, dir_y) or 1.0
        self.dir_x = dir_x / length
        self.dir_y = dir_y / length

        self._frames = left_frames if self.dir_x < 0 else right_frames
        self.image = self._frames[0]
        self.rect  = self.image.get_rect(center=(x, y))
        self._fx   = float(x)
        self._fy   = float(y)

    def update(self, dt, platforms, player):
        self._fx += self.SPEED * self.dir_x * dt
        self._fy += self.SPEED * self.dir_y * dt
        self.rect.center = (int(self._fx), int(self._fy))

        self.frame_index = (self.frame_index + 10 * dt) % len(self._frames)
        self.image = self._frames[int(self.frame_index)]

        if self.rect.colliderect(player.hitbox):
            player.take_damage(1)
            self.kill()
            return

        if (self.rect.right < -60 or self.rect.left > SCREEN_WIDTH + 60 or
                self.rect.bottom < -60 or self.rect.top > SCREEN_HEIGHT + 60):
            self.kill()

    def draw(self, screen):
        screen.blit(self.image, self.rect)


BloodDrop = FlyingDemonProjectile


# ══════════════════════════════════════════════════════════════════════════════
#  FLYING DEMON ENEMY — flutua em altura fixa, persegue player
# ══════════════════════════════════════════════════════════════════════════════

class FlyingDemonEnemy(BaseEnemy):
    """
    Demônio voador.
    - Flutua em altura fixa (hover sinusoidal).
    - Persegue o player horizontalmente.
    - Dispara bola de fogo a cada FIRE_INTERVAL segundos (cooldown 6s).
    - Disparo único por ciclo de ataque.
    """
    MAX_HP        = 4
    SPEED         = 60
    ANIM_SPEED    = 8.0
    FIRE_INTERVAL = 6.0
    AGGRO_RANGE   = 500

    STATE_IDLE   = "idle"
    STATE_FLY    = "fly"
    STATE_ATTACK = "attack"
    STATE_HURT   = "hurt"
    STATE_DEATH  = "death"

    def __init__(self, x, y):
        self._anim = {}
        SCALE = 2.0
        self._anim[self.STATE_IDLE]   = _load_demon_sheet(FLYING_DEMON_IDLE_SHEET,   FLYING_DEMON_W, FLYING_DEMON_H, cols=4, scale=SCALE)
        self._anim[self.STATE_FLY]    = _load_demon_sheet(FLYING_DEMON_FLYING_SHEET, FLYING_DEMON_W, FLYING_DEMON_H, cols=4, scale=SCALE)
        self._anim[self.STATE_ATTACK] = _load_demon_sheet(FLYING_DEMON_ATTACK_SHEET, FLYING_DEMON_ATK_W, FLYING_DEMON_H, cols=8, scale=SCALE)
        self._anim[self.STATE_HURT]   = _load_demon_sheet(FLYING_DEMON_HURT_SHEET,   FLYING_DEMON_W, FLYING_DEMON_H, cols=4, scale=SCALE)
        self._anim[self.STATE_DEATH]  = _load_demon_sheet(FLYING_DEMON_DEATH_SHEET,  FLYING_DEMON_DEATH_W, FLYING_DEMON_H, cols=7, scale=SCALE)

        super().__init__(x, y, self._anim[self.STATE_FLY])

        self.hover_y           = float(y)
        self.hover_offset      = 0.0
        self.fire_timer        = self.FIRE_INTERVAL
        self.state             = self.STATE_IDLE
        self._state_frame      = 0.0
        self._hurt_timer       = 0.0
        self._dead             = False
        self._shot_this_attack = False

    def _set_state(self, s):
        if self.state != s:
            self.state        = s
            self._state_frame = 0.0

    def _get_frames(self, state, facing):
        base = self._anim[state]
        return flip_frames(base) if facing == -1 else base

    def _advance_frame(self, dt) -> bool:
        n = len(self._get_frames(self.state, self.facing))
        self._state_frame += self.ANIM_SPEED * dt
        if self._state_frame >= n:
            self._state_frame %= n
            return True
        return False

    def _current_frame(self):
        frames = self._get_frames(self.state, self.facing)
        return frames[int(self._state_frame) % len(frames)]

    def take_damage(self, amount: int = 1):
        if self._dead:
            return
        self.hp -= amount
        self.hit_flash_timer = 0.12
        if self.hp <= 0:
            self._dead = True
            self._set_state(self.STATE_DEATH)
        else:
            self._set_state(self.STATE_HURT)
            self._hurt_timer = 0.4

    def update(self, dt, platforms, player, projectiles):
        dx = player.rect.centerx - self.rect.centerx

        if self._dead:
            death_frames = self._anim[self.STATE_DEATH]
            n = len(death_frames)
            self._state_frame += self.ANIM_SPEED * dt
            if self._state_frame >= n:
                self.image = death_frames[n - 1]
                self.kill()
                return
            self.image = death_frames[int(self._state_frame)]
            return

        if self.state == self.STATE_HURT:
            self._hurt_timer -= dt
            self._advance_frame(dt)
            self.image = self._current_frame()
            self._tick_flash(dt)
            if self._hurt_timer <= 0:
                self._set_state(self.STATE_FLY)
            return

        if self.state == self.STATE_ATTACK:
            prev = int(self._state_frame)
            done = self._advance_frame(dt)
            curr = int(self._state_frame)
            self.image = self._current_frame()

            if prev < 4 <= curr and not self._shot_this_attack:
                self._shot_this_attack = True
                fire_x = self.rect.centerx + self.facing * int(self.rect.width * 0.4)
                fire_y = self.rect.centery
                dir_x  = player.rect.centerx - fire_x
                dir_y  = player.rect.centery  - fire_y
                projectiles.add(FlyingDemonProjectile(fire_x, fire_y, dir_x, dir_y))

            if done:
                self._shot_this_attack = False
                self._set_state(self.STATE_FLY)
            return

        # Movimento hover
        self.facing = 1 if dx > 0 else -1
        if abs(dx) < self.AGGRO_RANGE:
            self._set_state(self.STATE_FLY)
            self.hitbox.x += int(self.SPEED * dt * self.facing)
        else:
            self._set_state(self.STATE_IDLE)

        self.hover_offset += dt * 2.0
        self.rect.y    = int(self.hover_y + math.sin(self.hover_offset) * 18)
        self.hitbox.y  = self.rect.y
        self.rect.x    = self.hitbox.x

        self.fire_timer -= dt
        if self.fire_timer <= 0:
            self.fire_timer        = self.FIRE_INTERVAL
            self._set_state(self.STATE_ATTACK)
            self._state_frame      = 0.0
            self._shot_this_attack = False

        self._advance_frame(dt)
        self.image = self._current_frame()
        self._tick_flash(dt)

    def draw(self, screen: pygame.Surface):
        screen.blit(self.image, self.rect)
        self._draw_hp_bar(screen)


EyeEnemy = FlyingDemonEnemy


# ══════════════════════════════════════════════════════════════════════════════
#  GROUND ENEMY — inimigo genérico de chão (usado para Mushroom e similares)
# ══════════════════════════════════════════════════════════════════════════════

class GroundEnemy(BaseEnemy):
    """
    Inimigo de chão genérico — recebe lista de frames via construtor.
    Anda em direção ao player, aplica dano por contato (melee).
    Usado para Mushroom e qualquer sprite de chão futuro.
    """
    MAX_HP      = 3
    SPEED       = 65
    DAMAGE      = 1
    MELEE_RANGE = 50
    AGGRO_RANGE = 480
    ANIM_SPEED  = 8.0

    def __init__(self, x, y, frames, player=None):
        super().__init__(x, y, frames)
        self.rect.midbottom = self.hitbox.midbottom
        self._attack_cd = 0.0

    def update(self, dt, platforms, player, projectiles):
        dx = player.rect.centerx - self.rect.centerx
        dist = abs(dx)
        if dist < self.AGGRO_RANGE:
            self.facing = 1 if dx > 0 else -1
            self.hitbox.x += int(self.SPEED * dt * self.facing)

        self._apply_gravity_and_land(dt, platforms)
        self._animate(dt)
        self._tick_flash(dt)

        self._attack_cd = max(0.0, self._attack_cd - dt)
        if dist < self.MELEE_RANGE and self._attack_cd == 0.0:
            player.take_damage(self.DAMAGE)
            self._attack_cd = 1.0


# ══════════════════════════════════════════════════════════════════════════════
#  WAVE MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class WaveManager:
    def __init__(self, spawn_queue: list, pool=None, max_alive: int = 3):
        self.queue   = sorted(spawn_queue, key=lambda e: e["delay"])
        self.elapsed = 0.0
        self.pool = pool
        self.max_alive = max_alive

    def update(self, dt: float, enemies: pygame.sprite.Group):
        self.elapsed += dt
        if len(enemies) >= self.max_alive:
            return
        while self.queue and self.queue[0]["delay"] <= self.elapsed:
            entry = self.queue.pop(0)
            cls = entry["cls"]
            if self.pool is not None:
                e = self.pool.acquire(cls, entry["x"], entry["y"])
                if hasattr(e, "set_pool"):
                    e.set_pool(self.pool)
            else:
                e = cls(entry["x"], entry["y"])
            # Fixar hitbox.bottom=y e inicializar acumulador float
            # (sem _fy_acc correto, _apply_gravity_and_land afunda o inimigo)
            if hasattr(e, "hitbox"):
                e.hitbox.bottom = entry["y"]
                e.rect.midbottom = e.hitbox.midbottom
                e._fy_acc = float(e.hitbox.y)
                e.vel_y = 0.0
            enemies.add(e)
            print(f"[enemy] spawnando inimigo: {cls.__name__} x={entry['x']} y={entry['y']}", flush=True)

    @property
    def done(self) -> bool:
        return len(self.queue) == 0