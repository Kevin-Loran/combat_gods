"""
game.py — Main game orchestrator.

Arenas suportadas:
  "minotaur" → MinotaurArena + MinotaurBoss   (padrão)
  "night"    → NightArena    + NightBoss
  "sombrio"  → SombrioArena  + SombrioBoss
"""

import pygame
import os
import sys
import time
import math
import random
from settings import *
from menu import PauseMenu, GameOverMenu, VictoryMenu
from analytics import tracker as combat_tracker
from divine_lightning import DivineThunder
from magic_projectile import MagicProjectile

# Sequência de bosses em ordem. Altere aqui para adicionar ou reordenar.
_BOSS_SEQUENCE = ("minotaur", "night", "sombrio")

# ── Plataforma ────────────────────────────────────────────────────────────────
PLATFORM_IMG_H = 111
TOP_INSET      = 10
SOLID_TOP      = SCREEN_HEIGHT - PLATFORM_IMG_H + TOP_INSET  # 439

PLATFORM_DATA = [
    (0, SCREEN_HEIGHT - PLATFORM_IMG_H, 1),
]

# ── Parallax ──────────────────────────────────────────────────────────────────
PARALLAX_LAYERS = [
    ("parallax-demon-woods-bg.png",          0.1),
    ("parallax-demon-woods-far-trees.png",   0.3),
    ("parallax-demon-woods-mid-trees.png",   0.6),
    ("parallax-demon-woods-close-trees.png", 0.9),
]


class ParallaxLayer:
    def __init__(self, image: pygame.Surface, factor: float):
        self.factor   = factor
        self.offset_x = 0.0
        orig_w, orig_h = image.get_size()
        scale = SCREEN_HEIGHT / orig_h
        new_w = int(orig_w * scale)
        self.image = pygame.transform.scale(image, (new_w, SCREEN_HEIGHT))
        self.img_w = new_w

    def update(self, player_vel_x: float, dt: float):
        self.offset_x += player_vel_x * self.factor * dt
        self.offset_x %= self.img_w

    def draw(self, surface: pygame.Surface):
        x = -int(self.offset_x)
        while x < SCREEN_WIDTH:
            surface.blit(self.image, (x, 0))
            x += self.img_w


class Game:

    def __init__(self, screen: pygame.Surface, arena_type: str = "minotaur"):
        self.screen      = screen
        self._arena_type = arena_type   # "minotaur" | "night" | "sombrio"
        self.font        = pygame.font.SysFont("monospace", 20, bold=True)
        self.big_font    = pygame.font.SysFont("monospace", 52, bold=True)
        self.med_font    = pygame.font.SysFont("monospace", 28, bold=True)

        # Surface intermediária para screen shake (criada uma vez)
        self._game_surface = pygame.Surface(screen.get_size())

        # Serão populados por _build_level via a arena escolhida
        self.parallax_layers = []
        self.fallback_bg     = None
        self._perf_last_log  = 0.0
        self._perf_last_fps  = 0.0

        # ── Menus (criados uma vez, resetados ao reiniciar) ───────────────
        self.pause_menu    = PauseMenu()
        self.gameover_menu = GameOverMenu()
        self.victory_menu  = VictoryMenu()
        self.paused        = False

        self._build_level()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _load_parallax(self) -> list:
        layers = []
        for filename, factor in PARALLAX_LAYERS:
            path = asset_path(filename)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    layers.append(ParallaxLayer(img, factor))
                except pygame.error as e:
                    print(f"[parallax] Erro ao carregar {path}: {e}")
        return layers

    def _make_fallback_background(self) -> pygame.Surface:
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for y in range(SCREEN_HEIGHT):
            t = y / SCREEN_HEIGHT
            r = int(15 + t * 55)
            g = int(3  + t * 4)
            pygame.draw.line(surf, (r, g, 3), (0, y), (SCREEN_WIDTH, y))
        return surf

    def _build_level(self):
        from player import Player

        self.game_over     = False
        self.boss_defeated = False
        self.analytics_finalized = False
        self.elapsed       = 0.0
        self.paused        = False
        self.pause_menu.reset()
        self.gameover_menu.reset()
        self.victory_menu.reset()
        combat_tracker.reset_session()
        self._lightnings:   list[DivineThunder]    = []
        self._projectiles:  list[MagicProjectile]  = []
        self._shake_timer = 0.0
        self._prev_player_rolling  = False
        self._prev_player_potions  = 3

        if self._arena_type == "night":
            self._load_night_arena(Player)
            self.rock_system = None
        elif self._arena_type == "sombrio":
            self._load_sombrio_arena(Player)
            self.rock_system = None
        else:
            self._load_minotaur_arena(Player)
            from rock_hazard import RockHazardSystem, _rock_asset
            self.rock_system = RockHazardSystem()
            self.rock_system.load_sprites(
                _rock_asset("Irregular rock Spritesheet.png"),
                _rock_asset("Impact Spritesheet.png"),
            )

    def _load_minotaur_arena(self, Player):
        """Arena original do Minotauro."""
        from boss import MinotaurBoss
        from minotaur_arena import MinotaurArena

        arena = MinotaurArena()
        self.arena           = arena
        self.parallax_layers = arena.parallax_layers
        self.fallback_bg     = arena.fallback_bg
        self.platforms       = arena.platforms
        self.player          = Player(*arena.player_spawn)
        self.boss            = MinotaurBoss(*arena.boss_spawn)

        print(
            f"[game] Minotaur Arena carregada — "
            f"player={arena.player_spawn}  boss={arena.boss_spawn}",
            flush=True,
        )

    def _load_sombrio_arena(self, Player):
        """Arena Sombria — Bringer of Death / Morthak."""
        from sombrio_boss import SombrioBoss
        from sombrio_arena import SombrioArena

        arena = SombrioArena()
        self.arena           = arena
        self.parallax_layers = arena.parallax_layers
        self.fallback_bg     = arena.fallback_bg
        self.platforms       = arena.platforms
        self.player          = Player(*arena.player_spawn)
        self.boss            = SombrioBoss(*arena.boss_spawn)

        print(
            f"[game] Sombrio Arena carregada — "
            f"player={arena.player_spawn}  boss={arena.boss_spawn}",
            flush=True,
        )

    def _load_night_arena(self, Player):
        """Arena Noturna — Night Town."""
        from night_boss import NightBoss
        from night_arena import NightArena

        arena = NightArena()
        self.arena           = arena
        self.parallax_layers = arena.parallax_layers
        self.fallback_bg     = arena.fallback_bg
        self.platforms       = arena.platforms
        self.player          = Player(*arena.player_spawn)
        self.boss            = NightBoss(*arena.boss_spawn)

        print(
            f"[game] Night Arena carregada — "
            f"player={arena.player_spawn}  boss={arena.boss_spawn}",
            flush=True,
        )

    # ── Boss progression ──────────────────────────────────────────────────────

    def _next_arena(self) -> str | None:
        """Retorna o tipo da próxima arena na sequência, ou None se for o último boss."""
        try:
            idx = _BOSS_SEQUENCE.index(self._arena_type)
            return _BOSS_SEQUENCE[idx + 1] if idx + 1 < len(_BOSS_SEQUENCE) else None
        except ValueError:
            return None

    def _is_final_boss(self) -> bool:
        return self._arena_type == _BOSS_SEQUENCE[-1]

    # ── Event handling ────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """
        Processa eventos de teclado para menus.
        Retorna 'quit' se o jogo deve fechar, None caso contrário.
        """
        if event.type == pygame.KEYDOWN:
            # ESC: fecha pausa ou sai do jogo
            if event.key == pygame.K_ESCAPE:
                if self.paused:
                    self.paused = False
                    self.pause_menu.reset()
                    return None
                return "quit"

            # P: toggle pausa (só durante gameplay)
            if event.key == pygame.K_p and not self.game_over and not self.boss_defeated:
                self.paused = not self.paused
                if not self.paused:
                    self.pause_menu.reset()
                return None

        # Delegar evento ao menu de pausa
        if self.paused:
            action = self.pause_menu.handle(event)
            if action == "resume":
                self.paused = False
                self.pause_menu.reset()
            elif action == "restart":
                self._build_level()
            elif action == "exit":
                return "quit"

        # Delegar evento ao menu de game over
        if self.game_over:
            action = self.gameover_menu.handle(event)
            if action == "restart":
                self._build_level()
            elif action == "exit":
                return "quit"

        # Delegar evento ao menu de vitória
        if self.boss_defeated:
            action = self.victory_menu.handle(event)
            if action == "retry":
                self._build_level()
            elif action == "next_battle":
                next_arena = self._next_arena()
                if next_arena:
                    self._arena_type = next_arena
                    self._build_level()
                else:
                    return "quit"
            elif action == "menu":
                return "quit"
            elif action == "quit_game":
                return "exit_game"

        return None

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, keys, dt: float, fps: float | None = None):
        # Pausa: congela tudo
        if self.paused:
            return

        # Game over: só atualiza o fade-in do menu
        if self.game_over:
            if not self.analytics_finalized:
                combat_tracker.finalize_fight(won=False)
                self.analytics_finalized = True
            self.gameover_menu.update(dt)
            return

        # Vitória: congela gameplay, atualiza apenas o menu
        if self.boss_defeated:
            if not self.analytics_finalized:
                combat_tracker.finalize_fight(won=True)
                self.analytics_finalized = True
            self.victory_menu.update(dt)
            return

        if fps is not None:
            self._perf_last_fps = fps

        self.elapsed += dt

        # Player
        self.player.update(keys, dt, self.platforms)

        # Parallax
        for layer in self.parallax_layers:
            layer.update(self.player.vel_x, dt)

        # Boss
        if not self.boss.should_be_removed:
            self.boss.update(dt, self.platforms, self.player)
            if self.rock_system is not None:
                self.rock_system.update(dt, self.player, SOLID_TOP)
            
            # Track distance for analytics
            dist = math.hypot(self.player.hitbox.centerx - self.boss.hitbox.centerx, 
                              self.player.hitbox.centery - self.boss.hitbox.centery)
            combat_tracker.update_distance(dist)
        elif not self.boss_defeated:
            self.boss_defeated = True
            if self.rock_system is not None:
                self.rock_system.clear()
            self.victory_menu.configure(is_final=self._is_final_boss())
            print("[game] Boss derrotado — fase limpa!", flush=True)

        # Ataques do player contra o boss
        atk_rect = self.player.get_attack_rect()
        if atk_rect and not self.boss.is_dead:
            if atk_rect.colliderect(self.boss.hitbox):
                boss_id = id(self.boss)
                if boss_id not in self.player.attack_hit_enemies:
                    self.boss.take_damage(1)
                    self.player.attack_hit_enemies.add(boss_id)
                    combat_tracker.log_event("hit_boss")
                    if not self.player.on_ground:
                        combat_tracker.log_event("air_attacks")

        # Raio Divino — ativar novo raio se player sinalizou
        if self.player.lightning_pending:
            if not self.boss.is_dead:
                self._lightnings.append(
                    DivineThunder(self.boss.hitbox.centerx, self.boss.hitbox.centery)
                )
                if hasattr(self.boss, 'on_lightning_used'):
                    self.boss.on_lightning_used()
            self.player.lightning_pending = False

        # Projetil Magico — criar se player sinalizou
        if self.player.projectile_pending:
            if not self.boss.is_dead:
                px = (self.player.hitbox.right if self.player.facing == 1
                      else self.player.hitbox.left)
                py = self.player.hitbox.centery
                self._projectiles.append(MagicProjectile(px, py, self.player.facing))
                if hasattr(self.boss, 'on_projectile_fired'):
                    self.boss.on_projectile_fired()
            self.player.projectile_pending = False

        # Atualizar projeteis e checar colisao com o boss
        for proj in self._projectiles:
            proj.update(dt)
            if not proj.done and not self.boss.is_dead:
                if proj.hitbox.colliderect(self.boss.hitbox):
                    self.boss.take_damage(1)
                    combat_tracker.log_event("hit_boss")
                    proj.done = True
        self._projectiles = [p for p in self._projectiles if not p.done]

        # Eventos adaptativos do boss (roll e poção)
        if hasattr(self.boss, 'on_player_rolled') and not self.boss.is_dead:
            cur_rolling = self.player.is_rolling
            if cur_rolling and not self._prev_player_rolling:
                self.boss.on_player_rolled(self.player.facing)
            self._prev_player_rolling = cur_rolling

            cur_potions = self.player.potions
            if cur_potions < self._prev_player_potions:
                self.boss.on_potion_used()
            self._prev_player_potions = cur_potions

        # Decaimento do screen shake
        self._shake_timer = max(0.0, self._shake_timer - dt)

        # Atualizar raios ativos e aplicar stun/dano/shake no momento do impacto
        for lt in self._lightnings:
            lt.update(dt)
            if lt.should_hit and not self.boss.is_dead:
                self.boss.take_damage(1)
                self.boss.stun(3.0)
                combat_tracker.log_event("hit_boss")
            if lt.should_shake:
                self._shake_timer = 0.25
        self._lightnings = [lt for lt in self._lightnings if not lt.done]

        # Colisão física sólida player ↔ boss (exceto durante roll)
        if not self.boss.should_be_removed:
            self._resolve_player_boss_collision()

        # Checar morte do player
        if not self.player.alive:
            self.game_over = True

        # Log de performance
        now = time.perf_counter()
        if now - self._perf_last_log >= 1.0:
            self._perf_last_log = now
            print(
                f"[perf] FPS={self._perf_last_fps:.1f}  "
                f"boss_hp={self.boss.hp}/{self.boss.max_hp}  "
                f"boss_state={self.boss.state}",
                flush=True
            )

    # ── Colisão física player ↔ boss ─────────────────────────────────────────

    def _resolve_player_boss_collision(self):
        """
        Bloqueia o player fisicamente no corpo do boss.
        Durante o roll o player é intangível e passa livremente.
        Ao sair do roll dentro do boss, o player é empurrado para o lado correto.
        """
        if self.player.is_rolling or self.boss.is_dead:
            return

        p = self.player.hitbox
        b = self.boss.hitbox

        if not p.colliderect(b):
            return

        # Calcular sobreposição em X nos dois sentidos
        overlap_left  = p.right - b.left   # quanto o player invadiu pela esquerda do boss
        overlap_right = b.right - p.left   # quanto o player invadiu pela direita do boss

        # Empurrar pelo lado com menor sobreposição (resolve sem jitter)
        if overlap_left <= overlap_right:
            # Player veio pela esquerda → empurrar para a esquerda
            self.player.hitbox.right = b.left
            self.player.vel_x = min(0.0, self.player.vel_x)
        else:
            # Player veio pela direita → empurrar para a direita
            self.player.hitbox.left = b.right
            self.player.vel_x = max(0.0, self.player.vel_x)

        self.player._align_rect()

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self):
        surf = self._game_surface

        # Fundo
        if self.parallax_layers:
            for layer in self.parallax_layers:
                layer.draw(surf)
        else:
            surf.blit(self.fallback_bg, (0, 0))

        # Plataformas
        self.platforms.draw(surf)

        # Boss
        if not self.boss.should_be_removed:
            self.boss.draw(surf)
            self.boss.particles.draw(surf)

        # Pedras ambientais — somente na arena do Minotauro
        if self.rock_system is not None:
            self.rock_system.draw(surf)

        # Player
        self.player.draw(surf)

        # Projeteis magicos
        for proj in self._projectiles:
            proj.draw(surf)

        # Raio Divino (sobre o campo de batalha, sob os HUDs)
        for lt in self._lightnings:
            lt.draw(surf)

        # HUDs (sempre visíveis, inclusive durante pausa/game over)
        self.player.draw_hud(surf)
        if not self.boss.should_be_removed:
            self.boss.draw_hud(surf)

        # Overlays de estado do jogo
        if self.game_over:
            self.gameover_menu.draw(surf)
        elif self.paused:
            self.pause_menu.draw(surf)
        elif self.boss_defeated:
            self.victory_menu.draw(surf)

        # Screen shake: blit com offset aleatorio, bordas preenchidas de preto
        if self._shake_timer > 0:
            intensity = max(1, int(8 * (self._shake_timer / 0.25)))
            ox = random.randint(-intensity, intensity)
            oy = random.randint(-intensity, intensity)
            self.screen.fill((0, 0, 0))
            self.screen.blit(surf, (ox, oy))
        else:
            self.screen.blit(surf, (0, 0))

