"""
settings.py — All constants in one place.
"""

# Paths devem ser resolvidos relativos a este arquivo (project/),
# não ao cwd de execução. Isso evita “sumiu tudo” quando o jogo é rodado
# a partir da raiz com `python project/main.py`.
import os

# --- Display ---
SCREEN_WIDTH  = 960
SCREEN_HEIGHT = 540
FPS           = 60
TITLE         = "CombatGods — Prototype v2"

# --- Physics ---
GRAVITY       = 900
JUMP_SPEED    = -520
PLAYER_SPEED  = 220
DASH_SPEED    = 580
DASH_DURATION = 0.18
DASH_COOLDOWN = 0.9

# --- Colors ---
BLACK      = (  0,   0,   0)
WHITE      = (255, 255, 255)
PINK       = (255, 160, 180)
DARK_RED   = ( 80,  10,  10)
ORANGE     = (210,  90,  20)
LAVA_GLOW  = (200,  60,   0)
PLATFORM_C = ( 90,  30,  20)
GREEN      = ( 50, 200,  50)
YELLOW     = (255, 220,   0)

# --- Asset paths ---
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR  = os.path.join(PROJECT_DIR, "assets")

def asset_path(*parts: str) -> str:
    return os.path.join(ASSETS_DIR, *parts)

BACKGROUND_PATH     = asset_path("background.png")
PLAYER_ATTACK_SHEET = asset_path("player_attack.png")
PLAYER_SPIN_SHEET   = asset_path("player_spin_up.png")
PLAYER_MOVE_SHEET   = asset_path("player_move.png")
PLAYER_DASH_SHEET   = asset_path("player_dash.png")   # 4 frames, 1 linha
PLAYER_JUMP_SHEET   = asset_path("player_jump.png")   # 4 frames, 1 linha
DEMON_SHEET         = asset_path("demon.png")
TILE_SHEET          = asset_path("platform_tiles.png")
TILE_SIZE           = 96

# Paths legados
SLIME_SHEET = asset_path("slime.png")
EYE_SHEET   = asset_path("eye.png")
DROP_SHEET  = asset_path("blood_drop.png")

# ── Skeleton ──────────────────────────────────────────────────────────────────
SKEL_ATTACK_SHEET = asset_path("skeleton_attack.png")
SKEL_DEATH_SHEET  = asset_path("skeleton_death.png")
SKEL_IDLE_SHEET   = asset_path("skeleton_idle.png")
SKEL_SHIELD_SHEET = asset_path("skeleton_shield.png")
SKEL_HIT_SHEET    = asset_path("skeleton_hit.png")
SKEL_WALK_SHEET   = asset_path("skeleton_walk.png")

# ── Flying demon sprites ──────────────────────────────────────────────────────
# OBS: este projeto não possui as artes `demon_idle.png`, `demon_flying.png`, etc.
# Para evitar placeholders, apontamos para as artes existentes do FlyEye.
FLYING_DEMON_IDLE_SHEET    = asset_path("flyingeye_flight.png")
FLYING_DEMON_FLYING_SHEET  = asset_path("flyingeye_flight.png")
FLYING_DEMON_ATTACK_SHEET  = asset_path("flyingeye_attack.png")
FLYING_DEMON_HURT_SHEET    = asset_path("flyingeye_hit.png")
FLYING_DEMON_DEATH_SHEET   = asset_path("flyingeye_death.png")
FLYING_DEMON_PROJ_SHEET    = asset_path("demon_projectile.png")

FLYING_DEMON_W       = 79
FLYING_DEMON_H       = 69
FLYING_DEMON_ATK_W   = 79
FLYING_DEMON_DEATH_W = 79
FLYING_DEMON_PROJ_W  = 48
FLYING_DEMON_PROJ_H  = 32