"""
debug_sprites.py — Sprite Diagnostic Tool
==========================================
Run this INSTEAD of main.py to diagnose sprite loading issues.

Usage:
    python debug_sprites.py

It will print a step-by-step diagnosis to the terminal AND
render the first valid sprite it finds on screen.

READ THE TERMINAL OUTPUT — every failure is explained with an exact fix.
"""

import pygame
import sys
import os

pygame.init()

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION — edit these to match your actual files
# ══════════════════════════════════════════════════════════════════════════════

TESTS = [
    {
        "label":    "Player Move Sheet",
        "path":     "assets/player_move.png",
        "frame_w":  130,   # ← change to your measured value
        "frame_h":  150,   # ← change to your measured value
        "rows":     2,
        "cols":     4,
    },
    {
        "label":    "Player Attack Sheet",
        "path":     "assets/player_attack.png",
        "frame_w":  130,
        "frame_h":  150,
        "rows":     2,
        "cols":     4,
    },
    {
        "label":    "Background",
        "path":     "assets/background.png",
        "frame_w":  None,   # None = don't slice, show full image
        "frame_h":  None,
        "rows":     1,
        "cols":     1,
    },
]

SCREEN_W = 960
SCREEN_H = 540

# ══════════════════════════════════════════════════════════════════════════════
#  TERMINAL COLOURS (Windows-safe fallback)
# ══════════════════════════════════════════════════════════════════════════════

try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(
        ctypes.windll.kernel32.GetStdHandle(-11), 7)
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
except Exception:
    RED = GREEN = YELLOW = CYAN = RESET = BOLD = ""

def ok(msg):    print(f"  {GREEN}✓ {msg}{RESET}")
def fail(msg):  print(f"  {RED}✗ FAIL: {msg}{RESET}")
def warn(msg):  print(f"  {YELLOW}⚠ WARN: {msg}{RESET}")
def info(msg):  print(f"  {CYAN}→ {msg}{RESET}")
def header(msg):print(f"\n{BOLD}{'═'*60}\n  {msg}\n{'═'*60}{RESET}")

# ══════════════════════════════════════════════════════════════════════════════
#  DIAGNOSTIC FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def step1_check_path(path: str) -> bool:
    """STEP 1 — Does the file actually exist on disk?"""
    header(f"STEP 1 · File Exists?  [{path}]")

    abs_path = os.path.abspath(path)
    info(f"Absolute path resolved to:\n    {abs_path}")

    # Check working directory
    cwd = os.getcwd()
    info(f"Current working directory:\n    {cwd}")

    if not os.path.exists(abs_path):
        fail(f"File NOT FOUND: {abs_path}")
        print(f"""
  {RED}━━━ HOW TO FIX ━━━{RESET}
  The file '{path}' does not exist at the expected location.

  Option A — Wrong folder:
      Make sure your PNG is inside:
          {os.path.join(cwd, 'assets')}
      Current files in that folder:""")

        assets_dir = os.path.join(cwd, "assets")
        if os.path.isdir(assets_dir):
            files = os.listdir(assets_dir)
            if files:
                for f in files:
                    print(f"          - {f}")
            else:
                print(f"          (folder is EMPTY)")
        else:
            print(f"          (folder 'assets/' does not exist at all!)")
            print(f"\n  {RED}Create the folder:{RESET}  mkdir assets")

        print(f"""
  Option B — Wrong extension:
      Your file might be .jpg or .jpeg instead of .png
      Rename it: rename player_move.jpeg player_move.png
      OR update the path in settings.py

  Option C — Wrong filename case (Linux is case-sensitive):
      'Player_Move.png' ≠ 'player_move.png'
""")
        return False

    size = os.path.getsize(abs_path)
    ok(f"File found! Size: {size:,} bytes")

    if size == 0:
        fail("File is 0 bytes — it is empty or corrupted.")
        print(f"  Fix: Re-export/re-save the image from your editor.\n")
        return False

    if size < 200:
        warn(f"File is very small ({size} bytes). "
             f"May be a broken export. Continue with caution.")

    return True


def step2_load_image(path: str):
    """STEP 2 — Can Pygame load the file and read its dimensions?"""
    header(f"STEP 2 · Load Image  [{path}]")

    # ── 2a: Load WITHOUT convert_alpha first (to isolate format errors) ──
    try:
        raw = pygame.image.load(path)
        ok(f"pygame.image.load() succeeded")
    except pygame.error as e:
        fail(f"pygame.image.load() raised an error:\n      {e}")
        print(f"""
  {RED}━━━ HOW TO FIX ━━━{RESET}
  Pygame cannot read this file. Common causes:

  1. The file is a JPEG renamed to .png
     Open in Paint/GIMP → Export As → PNG (not just rename)

  2. The file is corrupted
     Try opening it in an image viewer first

  3. The file format is unsupported (e.g. .webp, .psd, .aseprite)
     Export from Aseprite/Photoshop as PNG before using in Pygame
""")
        return None

    w, h = raw.get_width(), raw.get_height()
    info(f"Raw image size: {w} × {h} pixels")
    info(f"Raw pixel format: {raw.get_bitsize()}-bit  "
         f"(flags: {raw.get_flags()})")

    if w == 0 or h == 0:
        fail(f"Image has zero dimension ({w}×{h}). The file is broken.")
        return None

    # ── 2b: Load WITH convert_alpha (the correct way) ─────────────────────
    header(f"STEP 3 · Transparency  (convert_alpha)")
    try:
        img = pygame.image.load(path).convert_alpha()
        ok("convert_alpha() succeeded")
    except pygame.error as e:
        fail(f"convert_alpha() failed: {e}")
        print(f"""
  {RED}━━━ HOW TO FIX ━━━{RESET}
  This usually means pygame.display was not initialized before loading.
  Ensure you call pygame.display.set_mode() BEFORE any image loading.
  In this script that's already handled — so the file itself may be
  an unusual format. Try re-exporting as PNG-32 (with alpha channel).
""")
        warn("Falling back to convert() without alpha")
        img = pygame.image.load(path).convert()

    has_alpha = img.get_alpha() is not None or img.get_flags() & pygame.SRCALPHA
    if has_alpha:
        ok("Image has transparency (alpha channel present)")
    else:
        warn("Image has NO alpha channel. "
             "Transparent areas will appear as solid colour (usually black/white).")
        print(f"""
  If your sprite has a grey checkerboard background in Aseprite,
  that IS transparency — but it needs to be exported as PNG with
  'Export with transparency' / 'Alpha channel' enabled.
""")

    return img


def step3_check_scale(img: pygame.Surface, label: str):
    """STEP 4 — Is the image a reasonable size to appear on screen?"""
    header(f"STEP 4 · Scale & Position Check  [{label}]")
    w, h = img.get_size()
    info(f"Image size: {w} × {h} px")

    if w > SCREEN_W or h > SCREEN_H:
        warn(f"Image ({w}×{h}) is LARGER than the screen ({SCREEN_W}×{SCREEN_H}).")
        warn("If placed at (0,0), most of it will be off-screen.")
        print(f"  Consider: pygame.transform.scale(img, ({SCREEN_W}, {SCREEN_H}))")
    elif w < 4 or h < 4:
        fail(f"Image is tiny ({w}×{h} px). It may be invisible on screen.")
        print(f"  Your frame size constants may be wrong.\n"
              f"  Measure a single frame in your sprite sheet and update FRAME_W/FRAME_H.")
        return False
    else:
        ok(f"Size looks reasonable for display")

    return True


def step4_slice_sheet(img: pygame.Surface, path: str,
                      frame_w: int, frame_h: int, rows: int, cols: int):
    """STEP 5 — Validate sprite sheet slicing."""
    header(f"STEP 5 · Sprite Sheet Slicing  [{path}]")

    sw, sh = img.get_size()
    info(f"Sheet total size:    {sw} × {sh} px")
    info(f"Expected frame size: {frame_w} × {frame_h} px")
    info(f"Expected grid:       {cols} cols × {rows} rows = {cols*rows} frames")

    expected_w = frame_w * cols
    expected_h = frame_h * rows
    info(f"Expected sheet size: {expected_w} × {expected_h} px")

    errors = False

    if sw < expected_w:
        fail(f"Sheet width {sw}px < expected {expected_w}px  "
             f"({cols} cols × {frame_w}px)")
        print(f"""
  {RED}━━━ HOW TO FIX ━━━{RESET}
  Your FRAME_W ({frame_w}) or cols ({cols}) is wrong.

  To find the correct values:
    1. Open the sprite sheet in GIMP or Aseprite
    2. Count the number of columns of sprites
    3. Divide sheet width by column count:
       FRAME_W = {sw} ÷ {cols} = {sw // cols if cols else '?'} px
    4. Update frame_w in the TESTS list in this script
       and FRAME_W in player.py / enemy.py
""")
        errors = True

    if sh < expected_h:
        fail(f"Sheet height {sh}px < expected {expected_h}px  "
             f"({rows} rows × {frame_h}px)")
        print(f"""
  {RED}━━━ HOW TO FIX ━━━{RESET}
  Your FRAME_H ({frame_h}) or rows ({rows}) is wrong.

    Correct FRAME_H = {sh} ÷ {rows} = {sh // rows if rows else '?'} px
    Update frame_h in this script and FRAME_H in player.py
""")
        errors = True

    if errors:
        return []

    # ── Slice the frames ────────────────────────────────────────────────────
    frames = []
    for row in range(rows):
        for col in range(cols):
            x = col * frame_w
            y = row * frame_h
            try:
                frame = img.subsurface(pygame.Rect(x, y, frame_w, frame_h))
                frames.append(frame)
            except ValueError as e:
                fail(f"Frame [{row},{col}] at ({x},{y}) failed: {e}")
                print(f"""
  subsurface() raised an error — the Rect goes outside the image.
  This means your frame size is too large for the sheet.
  Recalculate: FRAME_W = sheet_width ÷ cols = {sw} ÷ {cols} = {sw//cols}
               FRAME_H = sheet_height ÷ rows = {sh} ÷ {rows} = {sh//rows}
""")
                return frames   # return what we have so far

    ok(f"Sliced {len(frames)} frames successfully")

    # Check first frame isn't all transparent (common mistake)
    first = frames[0]
    # Sample 4 corner pixels
    corners = [
        first.get_at((0, 0)),
        first.get_at((first.get_width()-1, 0)),
        first.get_at((0, first.get_height()-1)),
        first.get_at((first.get_width()-1, first.get_height()-1)),
    ]
    all_transparent = all(c[3] == 0 for c in corners)
    if all_transparent:
        warn("All 4 corners of frame[0] are fully transparent.")
        warn("The sprite might be invisible even when rendered correctly.")
        print(f"""
  Possible causes:
  a) Frame size is off — the frame rect contains empty space, not the sprite
     Try: FRAME_W = {sw // cols}, FRAME_H = {sh // rows}
  b) The sprite sheet has extra padding/margins around frames
     Check in Aseprite: Sprite > Sprite Properties to see frame layout
  c) The image was exported with white background instead of transparency
""")
    else:
        ok("Frame[0] has visible pixels (not fully transparent)")

    return frames


def step5_render_test(screen, img: pygame.Surface, frames: list, label: str):
    """STEP 6 — Force render on screen to confirm visibility."""
    header(f"STEP 6 · Render Test  [{label}]")

    screen.fill((30, 5, 5))   # dark red background

    # Draw the full sheet at top-left
    sheet_display = img
    if img.get_width() > SCREEN_W or img.get_height() > SCREEN_H // 2:
        scale_factor = min(SCREEN_W / img.get_width(),
                          (SCREEN_H // 2) / img.get_height())
        new_w = int(img.get_width()  * scale_factor)
        new_h = int(img.get_height() * scale_factor)
        sheet_display = pygame.transform.scale(img, (new_w, new_h))
        info(f"Sheet scaled to {new_w}×{new_h} for display")

    screen.blit(sheet_display, (10, 10))

    # Draw first 4 frames individually below
    if frames:
        x = 10
        y = SCREEN_H // 2 + 20
        shown = min(4, len(frames))
        for i in range(shown):
            frame = frames[i]
            fw, fh = frame.get_size()
            # Scale up if tiny
            if fw < 40:
                frame = pygame.transform.scale(frame, (fw*3, fh*3))
                fw, fh = frame.get_size()
            screen.blit(frame, (x, y))
            # Label
            font = pygame.font.SysFont("monospace", 12)
            lbl = font.render(f"[{i}] {frames[i].get_width()}×{frames[i].get_height()}", True, (200,200,200))
            screen.blit(lbl, (x, y + fh + 2))
            x += fw + 20

        ok(f"Rendered {shown} frames at y={SCREEN_H//2+20}")
    else:
        warn("No frames to display — sheet was not sliced")

    # Instruction overlay
    font = pygame.font.SysFont("monospace", 15, bold=True)
    screen.blit(font.render(f"TESTING: {label}", True, (255,220,0)), (10, SCREEN_H - 50))
    screen.blit(font.render("SPACE = next sprite   ESC = quit", True, (180,180,180)),
                (10, SCREEN_H - 28))

    pygame.display.flip()
    info("Rendered to screen. Check the window now.")
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN DIAGNOSTIC LOOP
# ══════════════════════════════════════════════════════════════════════════════

def run_diagnostics():
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Sprite Debugger — Read the terminal!")
    clock  = pygame.time.Clock()

    print(f"""
{BOLD}{'═'*60}
  COMBATGODS SPRITE DEBUGGER
  Read this terminal output carefully.
  Each FAIL tells you exactly what to fix.
{'═'*60}{RESET}
""")

    test_index = 0
    results    = []   # store (label, passed, img, frames) per test

    # Pre-run all diagnostic checks
    for test in TESTS:
        label   = test["label"]
        path    = test["path"]
        frame_w = test["frame_w"]
        frame_h = test["frame_h"]
        rows    = test["rows"]
        cols    = test["cols"]

        print(f"\n{BOLD}{'▶'*3}  Testing: {label}{RESET}")

        # Step 1: path exists?
        if not step1_check_path(path):
            results.append((label, False, None, []))
            print(f"  {RED}⛔ STOPPED at Step 1 — fix the file path first.{RESET}")
            continue

        # Step 2+3: load + transparency
        img = step2_load_image(path)
        if img is None:
            results.append((label, False, None, []))
            print(f"  {RED}⛔ STOPPED at Step 2 — fix the image format first.{RESET}")
            continue

        # Step 4: scale check
        if not step3_check_scale(img, label):
            results.append((label, False, img, []))
            continue

        # Step 5: slice sheet (skip for full images)
        if frame_w and frame_h:
            frames = step4_slice_sheet(img, path, frame_w, frame_h, rows, cols)
        else:
            frames = [img]   # treat full image as single frame
            ok(f"Full image — no slicing needed")

        passed = len(frames) > 0
        results.append((label, passed, img, frames))

    # ── Summary ───────────────────────────────────────────────────────────
    header("DIAGNOSTIC SUMMARY")
    all_passed = True
    for (label, passed, _, frames) in results:
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        nf     = len(frames) if frames else 0
        print(f"  {status}  {label}  ({nf} frames)")
        if not passed:
            all_passed = False

    if all_passed:
        print(f"\n  {GREEN}{BOLD}All sprites loaded successfully!{RESET}")
        print(f"  Use SPACE in the window to cycle through each sprite sheet.\n")
    else:
        print(f"\n  {RED}{BOLD}Some sprites FAILED — scroll up and read each FAIL message.{RESET}")
        print(f"  Fix the issues shown above, then re-run this script.\n")

    # ── Interactive render loop ────────────────────────────────────────────
    valid_results = [(l, img, frames) for (l, passed, img, frames)
                     in results if img is not None]

    if not valid_results:
        print(f"  {RED}No sprites could be loaded at all.{RESET}")
        print(f"  Fix your asset paths and re-run.\n")
        pygame.quit()
        return

    idx = 0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_SPACE:
                    idx = (idx + 1) % len(valid_results)

        label, img, frames = valid_results[idx]
        step5_render_test(screen, img, frames, label)
        clock.tick(30)


if __name__ == "__main__":
    run_diagnostics()
