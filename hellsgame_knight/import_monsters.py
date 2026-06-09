"""
import_monsters.py — Loader e spawner dos novos inimigos.

Caminhos corrigidos:
    FlyEye   — assets/flyingeye_*.png
    Skeleton — assets/skeleton_*.png
    Mushroom — assets/new_monsters/Mushroom_*.png
    Worm     — assets/new_monsters/Worm_*.png
"""

import pygame
from sprite_utils import load_sheet, flip_frames
from settings import asset_path

_BASE_NM = asset_path("new_monsters")
_FM = 150   # frame size pack principal
_FW = 90    # frame size Fire Worm

# FlyEye — em assets/ com nome flyingeye_*
_FLYEYE_FLIGHT = asset_path("flyingeye_flight.png")
_FLYEYE_ATTACK = asset_path("flyingeye_attack.png")
_FLYEYE_DEATH  = asset_path("flyingeye_death.png")
_FLYEYE_HIT    = asset_path("flyingeye_hit.png")

# Skeleton — em assets/ com nome skeleton_*
_SKEL_IDLE     = asset_path("skeleton_idle.png")
_SKEL_WALK     = asset_path("skeleton_walk.png")
_SKEL_ATTACK   = asset_path("skeleton_attack.png")
_SKEL_DEATH    = asset_path("skeleton_death.png")
_SKEL_HIT      = asset_path("skeleton_hit.png")
_SKEL_SHIELD   = asset_path("skeleton_shield.png")

# Mushroom e Worm — em assets/new_monsters/
_MUSH_IDLE     = f"{_BASE_NM}/Mushroom_idle.png"
_MUSH_RUN      = f"{_BASE_NM}/Mushroom_run.png"
_MUSH_ATTACK   = f"{_BASE_NM}/Mushroom_attack.png"
_MUSH_DEATH    = f"{_BASE_NM}/Mushroom_death.png"
_MUSH_HIT      = f"{_BASE_NM}/Mushroom_hit.png"

_WORM_WALK     = f"{_BASE_NM}/Worm_walk.png"
_WORM_IDLE     = f"{_BASE_NM}/Worm_idle.png"
_WORM_ATTACK   = f"{_BASE_NM}/Worm_attack.png"
_WORM_DEATH    = f"{_BASE_NM}/Worm_death.png"
_WORM_HIT      = f"{_BASE_NM}/Worm_hit.png"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _crop_frames(frames, padding=4):
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


def load_flyeye(scale=3.0):
    F = _FM
    if not hasattr(load_flyeye, "_CACHE"):
        load_flyeye._CACHE = {}
    k = float(scale)
    if k in load_flyeye._CACHE:
        return load_flyeye._CACHE[k]
    out = {
        "flight": _crop_frames(load_sheet(_FLYEYE_FLIGHT, F, F, rows=1, cols=8, scale=scale)),
        "attack": _crop_frames(load_sheet(_FLYEYE_ATTACK, F, F, rows=1, cols=8, scale=scale)),
        "death":  _crop_frames(load_sheet(_FLYEYE_DEATH,  F, F, rows=1, cols=4, scale=scale)),
        "hit":    _crop_frames(load_sheet(_FLYEYE_HIT,    F, F, rows=1, cols=4, scale=scale)),
    }
    load_flyeye._CACHE[k] = out
    print(f"[enemy] carregando sprite (cached): flyeye scale={scale}", flush=True)
    return out


def load_skeleton(scale=3.3):
    F = _FM
    if not hasattr(load_skeleton, "_CACHE"):
        load_skeleton._CACHE = {}
    k = float(scale)
    if k in load_skeleton._CACHE:
        return load_skeleton._CACHE[k]
    out = {
        "idle":   _crop_frames(load_sheet(_SKEL_IDLE,   F, F, rows=1, cols=4, scale=scale)),
        "walk":   _crop_frames(load_sheet(_SKEL_WALK,   F, F, rows=1, cols=4, scale=scale)),
        "attack": _crop_frames(load_sheet(_SKEL_ATTACK, F, F, rows=1, cols=8, scale=scale)),
        "death":  _crop_frames(load_sheet(_SKEL_DEATH,  F, F, rows=1, cols=4, scale=scale)),
        "hit":    _crop_frames(load_sheet(_SKEL_HIT,    F, F, rows=1, cols=4, scale=scale)),
        "shield": _crop_frames(load_sheet(_SKEL_SHIELD, F, F, rows=1, cols=4, scale=scale)),
    }
    load_skeleton._CACHE[k] = out
    print(f"[enemy] carregando sprite (cached): skeleton scale={scale}", flush=True)
    return out


def load_mushroom(scale=2.8):
    F = _FM
    if not hasattr(load_mushroom, "_CACHE"):
        load_mushroom._CACHE = {}
    k = float(scale)
    if k in load_mushroom._CACHE:
        return load_mushroom._CACHE[k]
    out = {
        "idle":   _crop_frames(load_sheet(_MUSH_IDLE,   F, F, rows=1, cols=4, scale=scale)),
        "walk":   _crop_frames(load_sheet(_MUSH_RUN,    F, F, rows=1, cols=8, scale=scale)),
        "attack": _crop_frames(load_sheet(_MUSH_ATTACK, F, F, rows=1, cols=8, scale=scale)),
        "death":  _crop_frames(load_sheet(_MUSH_DEATH,  F, F, rows=1, cols=4, scale=scale)),
        "hit":    _crop_frames(load_sheet(_MUSH_HIT,    F, F, rows=1, cols=4, scale=scale)),
    }
    load_mushroom._CACHE[k] = out
    print(f"[enemy] carregando sprite (cached): mushroom scale={scale}", flush=True)
    return out


def load_worm(scale=3.3):
    F = _FW
    if not hasattr(load_worm, "_CACHE"):
        load_worm._CACHE = {}
    k = float(scale)
    if k in load_worm._CACHE:
        return load_worm._CACHE[k]
    out = {
        "idle":   _crop_frames(load_sheet(_WORM_IDLE,   F, F, rows=1, cols=9,  scale=scale)),
        "walk":   _crop_frames(load_sheet(_WORM_WALK,   F, F, rows=1, cols=9,  scale=scale)),
        "attack": _crop_frames(load_sheet(_WORM_ATTACK, F, F, rows=1, cols=16, scale=scale)),
        "death":  _crop_frames(load_sheet(_WORM_DEATH,  F, F, rows=1, cols=8,  scale=scale)),
        "hit":    _crop_frames(load_sheet(_WORM_HIT,    F, F, rows=1, cols=3,  scale=scale)),
    }
    load_worm._CACHE[k] = out
    print(f"[enemy] carregando sprite (cached): worm scale={scale}", flush=True)
    return out


# ══════════════════════════════════════════════════════════════════════════════
#  ANIMATED GROUND ENEMY
# ══════════════════════════════════════════════════════════════════════════════

class AnimatedGroundEnemy(pygame.sprite.Sprite):
    STATE_IDLE   = "idle"
    STATE_WALK   = "walk"
    STATE_ATTACK = "attack"
    STATE_HURT   = "hurt"
    STATE_DEATH  = "death"

    def __init__(self, x, y, anims,
                 max_hp=3, speed=65, damage=1,
                 melee_range=55, aggro_range=480,
                 anim_speed=8.0, attack_frame=None, attack_cd=1.2):
        super().__init__()

        self._anims_right = anims
        self._anims_left  = {k: flip_frames(v) for k, v in anims.items()}

        self.MAX_HP      = max_hp
        self.hp          = max_hp
        self.SPEED       = speed
        self.DAMAGE      = damage
        self.MELEE_RANGE = melee_range
        self.AGGRO_RANGE = aggro_range
        self.ANIM_SPEED  = anim_speed
        self.ATTACK_CD   = attack_cd

        atk_len = len(anims.get("attack", [None]))
        self._attack_frame = attack_frame if attack_frame is not None else atk_len // 2

        self.facing      = -1
        self._state      = self.STATE_IDLE
        self._frame      = 0.0
        self._attack_cd  = 0.0
        self._hurt_timer = 0.0
        self._dead       = False
        self._hit_this_atk = False
        self.hit_flash_timer = 0.0
        self.vel_y  = 0.0
        self._fy_acc = float(y)

        first = anims.get("idle", anims.get("walk"))[0]
        self.image  = first
        self.rect   = self.image.get_rect(midbottom=(x, y))
        self.hitbox = self.rect.inflate(
            -int(self.rect.width  * 0.15),
            -int(self.rect.height * 0.10)
        ).copy()
        self.hitbox.bottom = y
        self.rect.midbottom = self.hitbox.midbottom
        self._fy_acc = float(self.hitbox.y)
        self._pooled = False
        self._pool_ref = None

    def set_pool(self, pool):
        self._pool_ref = pool
        self._pooled = pool is not None

    def kill(self):
        super().kill()
        if self._pooled and self._pool_ref is not None:
            try:
                self._pool_ref.release(self)
            except Exception:
                pass

    def reset(self, x: int, y: int):
        self.hp = self.MAX_HP
        self.facing = -1
        self._state = self.STATE_IDLE
        self._frame = 0.0
        self._attack_cd = 0.0
        self._hurt_timer = 0.0
        self._dead = False
        self._hit_this_atk = False
        self.hit_flash_timer = 0.0
        self.vel_y = 0.0

        first = self._anims_right.get("idle", self._anims_right.get("walk"))[0]
        self.image = first
        self.rect = self.image.get_rect(midbottom=(x, y))
        self.hitbox = self.rect.inflate(
            -int(self.rect.width  * 0.15),
            -int(self.rect.height * 0.10)
        ).copy()
        self.hitbox.bottom = y
        self.rect.midbottom = self.hitbox.midbottom
        self._fy_acc = float(self.hitbox.y)

    def _set_state(self, s):
        if self._state != s:
            self._state = s
            self._frame = 0.0

    def _frames(self):
        bank = self._anims_right if self.facing == 1 else self._anims_left
        return bank.get(self._state, bank.get(self.STATE_IDLE))

    def _advance(self, dt) -> bool:
        frames = self._frames()
        self._frame += self.ANIM_SPEED * dt
        if self._frame >= len(frames):
            self._frame %= len(frames)
            return True
        return False

    def _cur_image(self):
        frames = self._frames()
        return frames[int(self._frame) % len(frames)]

    def _gravity(self, dt, platforms):
        from settings import GRAVITY
        self.vel_y   += GRAVITY * dt
        self.vel_y    = min(self.vel_y, 900)
        self._fy_acc += self.vel_y * dt
        self.hitbox.y = round(self._fy_acc)
        probe = self.hitbox.inflate(0, 2)
        for plat in platforms:
            pr = plat.solid_rect
            if probe.colliderect(pr) and self.vel_y >= 0:
                self.hitbox.bottom = pr.top
                self._fy_acc       = float(self.hitbox.y)
                self.vel_y         = 0
                break
        self.rect.midbottom = (self.hitbox.centerx, self.hitbox.bottom)

    def take_damage(self, amount=1):
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

    def update(self, dt, platforms, player, projectiles):
        self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)
        self._attack_cd      = max(0.0, self._attack_cd - dt)

        if self._dead:
            done = self._advance(dt)
            self.image = self._cur_image()
            self._gravity(dt, platforms)
            if done:
                self.kill()
            return

        if self._state == self.STATE_HURT:
            self._hurt_timer -= dt
            self._advance(dt)
            self.image = self._cur_image()
            self._gravity(dt, platforms)
            if self._hurt_timer <= 0:
                self._set_state(self.STATE_WALK)
            return

        dx   = player.rect.centerx - self.rect.centerx
        dist = abs(dx)
        self.facing = 1 if dx > 0 else -1

        if self._state == self.STATE_ATTACK:
            prev = int(self._frame)
            done = self._advance(dt)
            curr = int(self._frame)
            self.image = self._cur_image()
            if prev < self._attack_frame <= curr and not self._hit_this_atk:
                self._hit_this_atk = True
                if dist < self.MELEE_RANGE + 20:
                    player.take_damage(self.DAMAGE)
            if done:
                self._hit_this_atk = False
                self._attack_cd = self.ATTACK_CD
                self._set_state(self.STATE_WALK)
            self._gravity(dt, platforms)
            return

        if dist < self.AGGRO_RANGE:
            if dist < self.MELEE_RANGE and self._attack_cd == 0.0:
                self._set_state(self.STATE_ATTACK)
                self._frame        = 0.0
                self._hit_this_atk = False
            else:
                self._set_state(self.STATE_WALK)
                self.hitbox.x += int(self.SPEED * dt * self.facing)
        else:
            self._set_state(self.STATE_IDLE)

        self._gravity(dt, platforms)
        self._advance(dt)
        self.image = self._cur_image()

    def draw(self, screen):
        if self.hit_flash_timer > 0:
            flash = self.image.copy()
            flash.fill((255, 255, 255, 160), special_flags=pygame.BLEND_RGBA_ADD)
            screen.blit(flash, self.rect)
        else:
            screen.blit(self.image, self.rect)
        self._draw_hp_bar(screen)

    def _draw_hp_bar(self, screen):
        bar_w = self.rect.width
        bar_h = 5
        bx    = self.rect.left
        by    = self.rect.top - 8
        ratio = max(0.0, self.hp / self.MAX_HP)
        pygame.draw.rect(screen, (60, 0, 0),   (bx, by, bar_w, bar_h))
        pygame.draw.rect(screen, (200, 30, 30), (bx, by, int(bar_w * ratio), bar_h))


# ══════════════════════════════════════════════════════════════════════════════
#  SPAWN
# ══════════════════════════════════════════════════════════════════════════════

def spawn_enemies(group, player, pool=None):
    from enemy import FlyingDemonEnemy, SkeletonEnemy
    from settings import SCREEN_HEIGHT, TILE_SIZE

    # Atualizado para nova plataforma: 111px altura, TOP_INSET=10
    PLATFORM_IMG_H = 111
    SOLID_TOP = SCREEN_HEIGHT - PLATFORM_IMG_H + 10   # 439
    FLY_Y     = int(SCREEN_HEIGHT * 0.28)

    flyeye_anims   = load_flyeye(scale=3.0)
    skeleton_anims = load_skeleton(scale=3.3)
    mushroom_anims = load_mushroom(scale=2.8)
    worm_anims     = load_worm(scale=3.3)

    # ── FlyEye ───────────────────────────────────────────────────────────────
    flyeye = FlyingDemonEnemy(420, FLY_Y)
    flyeye._anim[flyeye.STATE_FLY]    = flyeye_anims["flight"]
    flyeye._anim[flyeye.STATE_IDLE]   = flyeye_anims["flight"]
    flyeye._anim[flyeye.STATE_ATTACK] = flyeye_anims["attack"]
    flyeye._anim[flyeye.STATE_HURT]   = flyeye_anims["hit"]
    flyeye._anim[flyeye.STATE_DEATH]  = flyeye_anims["death"]
    flyeye.frames_right = flyeye_anims["flight"]
    flyeye.frames_left  = flip_frames(flyeye_anims["flight"])
    flyeye.hover_y = float(FLY_Y)
    flyeye.image   = flyeye_anims["flight"][0]
    flyeye.rect    = flyeye.image.get_rect(center=(420, FLY_Y))
    flyeye.hitbox  = flyeye.rect.inflate(
        -int(flyeye.rect.width * 0.15),
        -int(flyeye.rect.height * 0.1)
    ).copy()
    flyeye.hitbox.midbottom = flyeye.rect.midbottom
    flyeye.vel_y = 0.0
    group.add(flyeye)

    # ── Skeleton ─────────────────────────────────────────────────────────────
    if pool is not None:
        skeleton = pool.acquire(SkeletonEnemy, 620, SOLID_TOP, frames_override=skeleton_anims["idle"])
        if hasattr(skeleton, "set_pool"):
            skeleton.set_pool(pool)
    else:
        skeleton = SkeletonEnemy(620, SOLID_TOP, frames_override=skeleton_anims["idle"])

    # Atualiza animações (compatível com cache novo do SkeletonEnemy)
    if hasattr(skeleton, "_anim_right") and hasattr(skeleton, "_anim_left"):
        skeleton._anim_right[skeleton.STATE_WALK]   = skeleton_anims["walk"]
        skeleton._anim_right[skeleton.STATE_ATTACK] = skeleton_anims["attack"]
        skeleton._anim_right[skeleton.STATE_HURT]   = skeleton_anims["hit"]
        skeleton._anim_right[skeleton.STATE_DEATH]  = skeleton_anims["death"]
        skeleton._anim_left[skeleton.STATE_WALK]   = flip_frames(skeleton_anims["walk"])
        skeleton._anim_left[skeleton.STATE_ATTACK] = flip_frames(skeleton_anims["attack"])
        skeleton._anim_left[skeleton.STATE_HURT]   = flip_frames(skeleton_anims["hit"])
        skeleton._anim_left[skeleton.STATE_DEATH]  = flip_frames(skeleton_anims["death"])
        skeleton.frames_right = skeleton._anim_right[skeleton.STATE_IDLE]
        skeleton.frames_left  = skeleton._anim_left[skeleton.STATE_IDLE]
    else:
        # fallback legado
        skeleton._anim[skeleton.STATE_WALK]   = skeleton_anims["walk"]
        skeleton._anim[skeleton.STATE_ATTACK] = skeleton_anims["attack"]
        skeleton._anim[skeleton.STATE_HURT]   = skeleton_anims["hit"]
        skeleton._anim[skeleton.STATE_DEATH]  = skeleton_anims["death"]
    skeleton.hitbox.bottom  = SOLID_TOP
    skeleton.rect.midbottom = skeleton.hitbox.midbottom
    skeleton._fy_acc = float(skeleton.hitbox.y)
    skeleton.vel_y   = 0.0
    group.add(skeleton)

    # ── Mushroom ─────────────────────────────────────────────────────────────
    if pool is not None:
        mushroom = pool.acquire(
            AnimatedGroundEnemy,
            820, SOLID_TOP, mushroom_anims,
            max_hp=3, speed=60, damage=1,
            melee_range=55, aggro_range=480,
            anim_speed=8.0, attack_frame=4, attack_cd=1.2
        )
        if hasattr(mushroom, "set_pool"):
            mushroom.set_pool(pool)
    else:
        mushroom = AnimatedGroundEnemy(
            820, SOLID_TOP, mushroom_anims,
            max_hp=3, speed=60, damage=1,
            melee_range=55, aggro_range=480,
            anim_speed=8.0, attack_frame=4, attack_cd=1.2
        )
    group.add(mushroom)

    # ── Worm ─────────────────────────────────────────────────────────────────
    if pool is not None:
        worm = pool.acquire(
            AnimatedGroundEnemy,
            700, SOLID_TOP, worm_anims,
            max_hp=4, speed=50, damage=1,
            melee_range=60, aggro_range=480,
            anim_speed=10.0, attack_frame=8, attack_cd=1.5
        )
        if hasattr(worm, "set_pool"):
            worm.set_pool(pool)
    else:
        worm = AnimatedGroundEnemy(
            700, SOLID_TOP, worm_anims,
            max_hp=4, speed=50, damage=1,
            melee_range=60, aggro_range=480,
            anim_speed=10.0, attack_frame=8, attack_cd=1.5
        )
    group.add(worm)