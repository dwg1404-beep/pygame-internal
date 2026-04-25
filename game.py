import pygame
import math
import random
import os
import json
 
# --- setup ---
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Police Chase - DRIVE!")
clock = pygame.time.Clock()
 
WHITE      = (255, 255, 255)
GREEN      = (40, 150, 40)
BROWN      = (101, 67, 33)
RED        = (200, 50, 50)
GRAY       = (40, 40, 40)
ORANGE     = (255, 140, 0)
BLUE       = (80, 180, 255)
BLACK      = (0, 0, 0)
DARK_GRAY  = (60, 60, 60)
LIGHT_GREEN = (60, 180, 60)
KEY_OFF    = (80, 80, 80)
KEY_ON     = (255, 255, 255)
YELLOW     = (255, 230, 0)
 
font_large  = pygame.font.Font(None, 72)
font_medium = pygame.font.Font(None, 48)
font_small  = pygame.font.Font(None, 36)
font_tiny   = pygame.font.Font(None, 24)
 
ASSETS_DIR     = os.path.join(os.path.dirname(__file__), "assets")
HIGHSCORE_FILE = os.path.join(os.path.dirname(__file__), "highscores.json")
 
 
# --- wrong-key hint system ---
# Any screen can set these; draw_hint() renders a tooltip for HINT_DURATION ms.
 
wrong_key_hint       = ""
wrong_key_hint_timer = 0
HINT_DURATION        = 2500   # milliseconds the hint stays visible
 
def set_hint(text):
    global wrong_key_hint, wrong_key_hint_timer
    wrong_key_hint       = text
    wrong_key_hint_timer = pygame.time.get_ticks()
 
def draw_hint():
    """Draws a yellow tooltip near the bottom of the screen while the hint is active."""
    if not wrong_key_hint:
        return
    if pygame.time.get_ticks() - wrong_key_hint_timer > HINT_DURATION:
        return
    padding = 10
    surf = font_small.render(f"  {wrong_key_hint}  ", True, BLACK)
    bg_rect = pygame.Rect(
        WIDTH // 2 - surf.get_width() // 2 - padding,
        HEIGHT - 110,
        surf.get_width() + padding * 2,
        surf.get_height() + padding * 2
    )
    pygame.draw.rect(screen, YELLOW, bg_rect, border_radius=8)
    pygame.draw.rect(screen, ORANGE, bg_rect, 3, border_radius=8)
    screen.blit(surf, (bg_rect.x + padding, bg_rect.y + padding))
 
 
# --- audio loading ---
 
def load_sound(name):
    for ext in [".wav", ".mp3", ".ogg"]:
        path = os.path.join(ASSETS_DIR, name + ext)
        if os.path.exists(path):
            try:
                return pygame.mixer.Sound(path)
            except Exception:
                pass
    return None
 
def load_music(name):
    for ext in [".wav", ".mp3", ".ogg"]:
        path = os.path.join(ASSETS_DIR, name + ext)
        if os.path.exists(path):
            return path
    return None
 
snd_engine = load_sound("engine")
snd_siren  = load_sound("siren")
music_path = load_music("music")
 
if snd_engine: snd_engine.set_volume(0.4)
if snd_siren:  snd_siren.set_volume(0.5)
 
if music_path:
    pygame.mixer.music.load(music_path)
    pygame.mixer.music.set_volume(0.3)
    pygame.mixer.music.play(-1)
 
engine_playing = False
siren_playing  = False
 
vol_music  = 0.3
vol_engine = 0.4
vol_siren  = 0.5
audio_selected = 0
 
 
# --- highscore helpers ---
 
def load_highscores():
    if os.path.exists(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}
 
def save_highscores(highscores):
    try:
        with open(HIGHSCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(highscores, f, indent=2)
    except Exception:
        pass
 
 
# --- background image helper ---
 
def ensure_background_image(name, generator, size=(WIDTH, HEIGHT), scale=True):
    path = os.path.join(ASSETS_DIR, name)
    if os.path.exists(path):
        try:
            img = pygame.image.load(path).convert()
            if img.get_size() != size:
                raise ValueError("Wrong size")
            return pygame.transform.scale(img, (WIDTH, HEIGHT)) if scale else img
        except Exception:
            pass
    surf = pygame.Surface(size)
    generator(surf)
    try:
        pygame.image.save(surf, path)
    except Exception:
        pass
    return pygame.transform.scale(surf, (WIDTH, HEIGHT)) if scale else surf
 
def _generate_grass_bg(surf):
    w, h = surf.get_size()
    surf.fill(GREEN)
    for _ in range(1200):
        x = random.randint(0, w)
        y = random.randint(0, h)
        grass_color = random.choice([(30, 130, 30), (35, 145, 35), (25, 120, 25), (60, 180, 60)])
        pygame.draw.line(surf, grass_color, (x, y), (x + random.randint(1, 3), y + random.randint(2, 5)), 1)
    for _ in range(60):
        x = random.randint(0, w - 50)
        y = random.randint(0, h - 50)
        pygame.draw.circle(surf, (20, 100, 20), (x, y), random.randint(10, 30))
 
GRASS_TILE_SIZE = (200, 200)
grass_bg = ensure_background_image("grass1.png", _generate_grass_bg, size=GRASS_TILE_SIZE, scale=False)
 
 
# --- asset loading ---
 
def load_asset(name, color):
    try:
        path = os.path.join(ASSETS_DIR, name)
        img = pygame.image.load(path).convert_alpha()
        img = pygame.transform.scale(img, (60, 120))
        return pygame.transform.rotate(img, 90)
    except:
        surf = pygame.Surface((60, 120), pygame.SRCALPHA)
        surf.fill(color)
        return pygame.transform.rotate(surf, 90)
 
car_img    = load_asset("carok.png",     BLUE)
police_img = load_asset("policecar.png", RED)
 
 
# --- game state ---
 
class GameState:
    LOGIN        = 0
    MAIN_MENU    = 1
    LEVEL_SELECT = 2
    PLAYING      = 3
    GAME_OVER    = 4
    OPTIONS      = 5
 
current_state     = GameState.LOGIN
username          = ""
selected_level    = "grass"
highscores        = load_highscores()
current_highscore = 0
login_context     = "new"
 
def get_user_scores(name):
    if name not in highscores or not isinstance(highscores[name], dict):
        highscores[name] = {"grass": 0, "highway": 0}
    else:
        highscores[name].setdefault("grass", 0)
        highscores[name].setdefault("highway", 0)
    return highscores[name]
 
def update_current_highscore():
    global current_highscore
    if username:
        scores = get_user_scores(username)
        current_highscore = scores.get(selected_level, 0)
    else:
        current_highscore = 0
 
difficulty = 3
difficulty_multiplier = {1: 0.5, 2: 0.75, 3: 1.0, 4: 1.25, 5: 1.5}
turn_speed_multiplier = {1: 0.5, 2: 0.75, 3: 1.0, 4: 1.25, 5: 1.5}
 
# max health scales with difficulty (easier = more health)
MAX_HEALTH = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}
# invincibility frames after a pothole hit (ms)
INVINCIBLE_DURATION = 1500
 
def reset():
    return {
        "x": 0, "y": 0, "angle": 0,
        "police": [], "explosions": [],
        "obstacles": [],
        "score": 0, "dead": False,
        "start_time": pygame.time.get_ticks(),
        "spawn_timer": 0, "time_bonus_timer": 0,
        # --- health / damage system ---
        "health": MAX_HEALTH[difficulty],   # starts full for current difficulty
        "invincible_timer": 0,              # timestamp of last pothole hit
        "damage_flash": 0,                  # countdown frames for red screen flash
    }
 
def spawn_obstacles(game_state, count=35):
    # grass level = potholes (dark), highway level = cones (orange)
    if selected_level == "grass":
        color = (25, 25, 25)   # near-black pothole
    else:
        color = (255, 100, 0)  # orange cones
 
    for _ in range(count):
        ox = random.randint(-2000, 2000)
        oy = random.randint(-2000, 2000)
        if math.hypot(ox, oy) < 200:
            continue
        size = random.randint(18, 30)
        game_state["obstacles"].append({"x": ox, "y": oy, "size": size, "color": color})
 
    for _ in range(25):
        ox = random.randint(-5000, 5000)
        oy = random.randint(-5000, 5000)
        if math.hypot(ox, oy) < 2200:
            continue
        size = random.randint(18, 30)
        game_state["obstacles"].append({"x": ox, "y": oy, "size": size, "color": color})
 
g = reset()
spawn_obstacles(g)
running = True
 
 
# --- input box ---
 
class InputBox:
    def __init__(self, x, y, w, h):
        self.rect   = pygame.Rect(x, y, w, h)
        self.text   = ""
        self.active = True
 
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode.isprintable() and len(self.text) < 20:
                self.text += event.unicode
 
    def draw(self, surface):
        pygame.draw.rect(surface, WHITE, self.rect, 3)
        text_surf = font_small.render(self.text, True, WHITE)
        surface.blit(text_surf, (self.rect.x + 10, self.rect.y + 10))
 
input_box = InputBox(WIDTH // 2 - 150, HEIGHT // 2 + 50, 300, 60)
 
 
# --- screen drawing ---
 
def draw_login_screen():
    screen.fill(DARK_GRAY)
    if login_context == "change":
        title = font_large.render("CHANGE USER", True, LIGHT_GREEN)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))
        if username:
            t = font_tiny.render(f"Logged in as: {username}", True, ORANGE)
            screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 165))
    else:
        title = font_large.render("POLICE CHASE", True, ORANGE)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))
    prompt = font_medium.render("Enter Username:", True, WHITE)
    screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 2 - 100))
    input_box.draw(screen)
    # show a nudge if they hit ENTER with an empty box
    hint = font_tiny.render("Press ENTER to continue", True, WHITE)
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 50))
    draw_hint()
 
def draw_main_menu():
    screen.fill(DARK_GRAY)
    title = font_large.render("POLICE CHASE", True, ORANGE)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))
    welcome = font_small.render(f"Welcome, {username}!", True, LIGHT_GREEN)
    screen.blit(welcome, (WIDTH // 2 - welcome.get_width() // 2, 150))
    screen.blit(font_medium.render("1. PLAY",        True, WHITE),       (WIDTH//2 - 80, 230))
    screen.blit(font_medium.render("2. OPTIONS",     True, WHITE),       (WIDTH//2 - 100, 300))
    screen.blit(font_medium.render("3. QUIT",        True, WHITE),       (WIDTH//2 - 60, 370))
    screen.blit(font_medium.render("4. CHANGE USER", True, LIGHT_GREEN), (WIDTH//2 - 140, 440))
    screen.blit(font_tiny.render("Press 1, 2, 3, or 4", True, WHITE),   (WIDTH//2 - 95, HEIGHT - 50))
    draw_hint()
 
def draw_level_select():
    screen.fill(DARK_GRAY)
    title = font_large.render("SELECT LEVEL", True, ORANGE)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))
    scores = get_user_scores(username) if username else {"grass": 0, "highway": 0}
    g_text = font_small.render(f"Grass High Score: {scores.get('grass', 0)}",   True, WHITE)
    h_text = font_small.render(f"Highway High Score: {scores.get('highway', 0)}", True, WHITE)
    screen.blit(g_text, (WIDTH // 2 - g_text.get_width() // 2, 130))
    screen.blit(h_text, (WIDTH // 2 - h_text.get_width() // 2, 160))
    grass_rect   = pygame.Rect(80,  250, 280, 150)
    highway_rect = pygame.Rect(440, 250, 280, 150)
    pygame.draw.rect(screen, GREEN, grass_rect);   pygame.draw.rect(screen, WHITE, grass_rect,   3)
    pygame.draw.rect(screen, GRAY,  highway_rect); pygame.draw.rect(screen, WHITE, highway_rect, 3)
    for rect, label in [(grass_rect, "GRASSY LAND"), (highway_rect, "HIGHWAY")]:
        t = font_medium.render(label, True, WHITE)
        screen.blit(t, (rect.centerx - t.get_width() // 2, rect.y + 30))
    screen.blit(font_tiny.render("Press 1", True, WHITE), (grass_rect.centerx   - 25, grass_rect.y   + 100))
    screen.blit(font_tiny.render("Press 2", True, WHITE), (highway_rect.centerx - 25, highway_rect.y + 100))
    screen.blit(font_tiny.render("Press M to return to menu", True, WHITE), (WIDTH//2 - 110, HEIGHT - 50))
    draw_hint()
    return grass_rect, highway_rect
 
 
# --- volume bar ---
 
def draw_volume_bar(label, volume, y, selected):
    label_color = ORANGE if selected else WHITE
    screen.blit(font_small.render(label, True, label_color), (80, y))
    bar_x, bar_y, bar_w, bar_h = 260, y + 4, 300, 22
    pygame.draw.rect(screen, GRAY, (bar_x, bar_y, bar_w, bar_h))
    filled_w = int(bar_w * volume)
    if filled_w > 0:
        pygame.draw.rect(screen, ORANGE if selected else LIGHT_GREEN, (bar_x, bar_y, filled_w, bar_h))
    pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_w, bar_h), 2)
    screen.blit(font_tiny.render(f"{int(volume * 100)}%", True, WHITE), (bar_x + bar_w + 10, bar_y + 2))
 
def draw_options():
    screen.fill(DARK_GRAY)
    screen.blit(font_large.render("OPTIONS", True, ORANGE), (WIDTH//2 - 80, 50))
    screen.blit(font_medium.render("DIFFICULTY", True, WHITE), (WIDTH//2 - 100, 110))
    difficulties = [(1,"EASY",WHITE),(2,"NORMAL",LIGHT_GREEN),(3,"MEDIUM",ORANGE),(4,"HARD",RED),(5,"EXTREME",(255,0,0))]
    screen.blit(font_small.render(f"Current: {difficulty}", True, ORANGE), (WIDTH//2 - 70, 155))
    y_pos = 190
    for num, name, color in difficulties:
        marker = "<<" if num == difficulty else "  "
        t = font_tiny.render(f"{marker} {num}. {name} {marker}", True, color)
        screen.blit(t, (WIDTH//2 - t.get_width()//2, y_pos))
        y_pos += 28
    screen.blit(font_medium.render("AUDIO", True, WHITE), (WIDTH//2 - 55, 350))
    draw_volume_bar("MUSIC",  vol_music,  390, audio_selected == 0)
    draw_volume_bar("ENGINE", vol_engine, 430, audio_selected == 1)
    draw_volume_bar("SIREN",  vol_siren,  470, audio_selected == 2)
    screen.blit(font_tiny.render("Press 1-5 for difficulty  |  UP/DOWN to pick audio  |  LEFT/RIGHT to adjust", True, WHITE),
                (WIDTH//2 - 310, HEIGHT - 80))
    screen.blit(font_tiny.render("Press M to return to menu", True, WHITE), (WIDTH//2 - 110, HEIGHT - 50))
    draw_hint()
 
 
# --- health bar drawing ---
 
def draw_health_bar():
    """Draws hearts in the top-right corner representing the player's health."""
    max_hp = MAX_HEALTH[difficulty]
    hp     = g["health"]
    heart_size = 22
    gap        = 6
    start_x    = WIDTH - (heart_size + gap) * max_hp - 15
    y          = 20
 
    # label
    screen.blit(font_tiny.render("HP:", True, WHITE), (start_x - 35, y + 2))
 
    for i in range(max_hp):
        x = start_x + i * (heart_size + gap)
        color = RED if i < hp else DARK_GRAY
        border = WHITE if i < hp else GRAY
        # draw a simple filled square heart icon with a border
        pygame.draw.rect(screen, color,  (x, y, heart_size, heart_size), border_radius=4)
        pygame.draw.rect(screen, border, (x, y, heart_size, heart_size), 2, border_radius=4)
        # small "♥" text inside each cell
        h_surf = font_tiny.render("♥", True, WHITE if i < hp else (80, 80, 80))
        screen.blit(h_surf, (x + heart_size//2 - h_surf.get_width()//2,
                              y + heart_size//2 - h_surf.get_height()//2))
 
 
# --- arrow key widget ---
 
def draw_arrow_keys(keys):
    base_x = WIDTH - 160
    base_y = HEIGHT - 60
    left_color  = KEY_ON if keys[pygame.K_LEFT]  else KEY_OFF
    right_color = KEY_ON if keys[pygame.K_RIGHT] else KEY_OFF
    left_points = [(base_x-28, base_y), (base_x+12, base_y-22), (base_x+12, base_y+22)]
    pygame.draw.polygon(screen, left_color, left_points)
    pygame.draw.polygon(screen, BLACK,      left_points, 2)
    screen.blit(font_tiny.render("TURN", True, (120, 120, 120)), (base_x + 18, base_y - 8))
    right_cx = base_x + 110
    right_points = [(right_cx+28, base_y), (right_cx-12, base_y-22), (right_cx-12, base_y+22)]
    pygame.draw.polygon(screen, right_color, right_points)
    pygame.draw.polygon(screen, BLACK,       right_points, 2)
 
 
# --- pothole drawing helper ---
 
def draw_pothole(surface, cx, cy, size):
    """Renders a pothole as a dark rough circle with a cracked inner ring."""
    # outer rough ring (slightly lighter asphalt colour)
    pygame.draw.circle(surface, (50, 45, 40), (cx, cy), size)
    # inner dark hole
    inner = max(4, size - 7)
    pygame.draw.circle(surface, (15, 12, 10), (cx, cy), inner)
    # small highlight arc to suggest depth
    pygame.draw.circle(surface, (70, 65, 58), (cx - size//4, cy - size//4), max(2, size//5))
 
 
# --- gameplay drawing ---
 
def draw_game():
    def world_to_screen(wx, wy):
        return wx - g["x"] + WIDTH//2, wy - g["y"] + HEIGHT//2
 
    # --- background ---
    if selected_level == "grass":
        tile_w, tile_h = grass_bg.get_size()
        offset_x = int(g["x"]) % tile_w
        offset_y = int(g["y"]) % tile_h
        for ix in range(-1, WIDTH  // tile_w + 2):
            for iy in range(-1, HEIGHT // tile_h + 2):
                screen.blit(grass_bg, (ix * tile_w - offset_x, iy * tile_h - offset_y))
    else:
        screen.fill(GREEN)
        road_width  = 400
        road_height = 6000
        road_x_screen, _ = world_to_screen(-road_width // 2, 0)
        _, road_y_screen  = world_to_screen(0, -road_height // 2)
        pygame.draw.rect(screen, DARK_GRAY, (road_x_screen, road_y_screen, road_width, road_height))
        lane_count = 3
        lane_width = road_width // lane_count
        for j in range(1, lane_count):
            lx = road_x_screen + j * lane_width
            for y in range(0, road_height, 40):
                pygame.draw.rect(screen, WHITE, (lx - 2, road_y_screen + y, 4, 20))
        pygame.draw.rect(screen, ORANGE, (road_x_screen, road_y_screen, 6, road_height))
        pygame.draw.rect(screen, ORANGE, (road_x_screen + road_width - 6, road_y_screen, 6, road_height))
 
    # --- obstacles ---
    for obs in g["obstacles"]:
        ox, oy = world_to_screen(obs["x"], obs["y"])
        if selected_level == "grass":
            # render as a pothole
            draw_pothole(screen, int(ox), int(oy), obs["size"])
        else:
            # keep orange cones as-is
            pygame.draw.circle(screen, obs["color"], (int(ox), int(oy)), obs["size"])
 
    # --- police cars ---
    for p in g["police"]:
        img = pygame.transform.rotate(police_img, -p["angle"])
        screen.blit(img, img.get_rect(center=(p["x"] - g["x"] + WIDTH//2,
                                              p["y"] - g["y"] + HEIGHT//2)))
 
    # --- off-screen cop arrows ---
    for p in g["police"]:
        px = p["x"] - g["x"] + WIDTH//2
        py = p["y"] - g["y"] + HEIGHT//2
        if px < 0 or px > WIDTH or py < 0 or py > HEIGHT:
            arrow_x = min(max(px, 20), WIDTH  - 20)
            arrow_y = min(max(py, 20), HEIGHT - 20)
            dx, dy  = px - WIDTH//2, py - HEIGHT//2
            angle   = math.atan2(dy, dx)
            tip_x   = arrow_x + math.cos(angle) * 30
            tip_y   = arrow_y + math.sin(angle) * 30
            pygame.draw.line(screen, RED, (arrow_x, arrow_y), (tip_x, tip_y), 4)
            for side in [angle + math.pi * 0.75, angle - math.pi * 0.75]:
                pygame.draw.line(screen, RED, (tip_x, tip_y),
                                 (tip_x + math.cos(side)*12, tip_y + math.sin(side)*12), 3)
 
    # --- player car (flicker white when invincible) ---
    invincible = (pygame.time.get_ticks() - g["invincible_timer"]) < INVINCIBLE_DURATION
    show_car   = True
    if invincible:
        # flicker every 8 frames
        show_car = (pygame.time.get_ticks() // 80) % 2 == 0
    if show_car:
        p_img = pygame.transform.rotate(car_img, -g["angle"])
        screen.blit(p_img, p_img.get_rect(center=(WIDTH//2, HEIGHT//2)))
 
    # username above car
    un = font_small.render(username, True, WHITE)
    screen.blit(un, (WIDTH//2 - un.get_width()//2, HEIGHT//2 - 80))
 
    # --- explosions ---
    for exp in g["explosions"][:]:
        exp["t"] -= 1
        if exp["t"] <= 0:
            g["explosions"].remove(exp)
        else:
            size = int(30 * (1 - exp["t"] / 20))
            pygame.draw.circle(screen, ORANGE,
                               (int(exp["x"] - g["x"] + WIDTH//2),
                                int(exp["y"] - g["y"] + HEIGHT//2)), size)
 
    # --- HUD top-left ---
    elapsed = (pygame.time.get_ticks() - g["start_time"]) // 1000
    screen.blit(font_small.render(f"TIME: {elapsed}s",      True, WHITE),  (20, 20))
    screen.blit(font_small.render(f"SCORE: {g['score']}",   True, WHITE),  (20, 70))
    screen.blit(font_tiny.render(f"DIFFICULTY: {difficulty}", True, ORANGE),(20, 120))
    screen.blit(font_tiny.render(f"OBSTACLES: {len(g['obstacles'])}", True, BROWN), (20, 145))
 
    # --- health bar top-right ---
    draw_health_bar()
 
    # --- damage flash overlay (red tint) ---
    if g["damage_flash"] > 0:
        g["damage_flash"] -= 1
        alpha  = int(160 * g["damage_flash"] / 20)
        flash  = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        flash.fill((220, 30, 30, alpha))
        screen.blit(flash, (0, 0))
 
        # big "POTHOLE!" warning text while flashing
        warn = font_medium.render("POTHOLE!", True, YELLOW)
        screen.blit(warn, (WIDTH//2 - warn.get_width()//2, HEIGHT//2 + 60))
 
    # --- arrow key widget ---
    keys = pygame.key.get_pressed()
    draw_arrow_keys(keys)
    draw_hint()
 
def draw_game_over():
    screen.fill(DARK_GRAY)
    screen.blit(font_large.render("BUSTED!", True, RED), (WIDTH//2 - 120, 80))
    elapsed = (g["end_time"] - g["start_time"]) // 1000
    screen.blit(font_medium.render(f"Time: {elapsed}s",    True, WHITE),  (WIDTH//2 - 100, 200))
    screen.blit(font_medium.render(f"Score: {g['score']}", True, WHITE),  (WIDTH//2 - 100, 270))
    screen.blit(font_small.render(f"Difficulty: {difficulty}", True, ORANGE), (WIDTH//2 - 100, 340))
    screen.blit(font_small.render("Press R to Replay or M for Menu", True, ORANGE), (WIDTH//2 - 210, HEIGHT - 80))
    draw_hint()
 
 
# --- main loop ---
 
while running:
    clock.tick(60)
    now = pygame.time.get_ticks()
 
    # --- event handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
 
        # ---- LOGIN ----
        if current_state == GameState.LOGIN:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if len(input_box.text) > 0:
                        username      = input_box.text
                        login_context = "new"
                        update_current_highscore()
                        current_state = GameState.MAIN_MENU
                    else:
                        set_hint("Type a username first, then press ENTER")
                else:
                    input_box.handle_event(event)
 
        # ---- MAIN MENU ----
        elif current_state == GameState.MAIN_MENU:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    current_state = GameState.LEVEL_SELECT
                elif event.key == pygame.K_2:
                    current_state = GameState.OPTIONS
                elif event.key == pygame.K_3:
                    running = False
                elif event.key == pygame.K_4:
                    login_context  = "change"
                    input_box.text = ""
                    current_state  = GameState.LOGIN
                else:
                    # any other key → helpful nudge
                    set_hint("Press 1 (Play)  2 (Options)  3 (Quit)  4 (Change User)")
 
        # ---- LEVEL SELECT ----
        elif current_state == GameState.LEVEL_SELECT:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    selected_level = "grass"
                    update_current_highscore()
                    g = reset(); spawn_obstacles(g)
                    current_state = GameState.PLAYING
                elif event.key == pygame.K_2:
                    selected_level = "highway"
                    update_current_highscore()
                    g = reset(); spawn_obstacles(g)
                    current_state = GameState.PLAYING
                elif event.key == pygame.K_m:
                    current_state = GameState.MAIN_MENU
                else:
                    set_hint("Press 1 (Grassy Land)  2 (Highway)  M (Back)")
 
        # ---- OPTIONS ----
        elif current_state == GameState.OPTIONS:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]:
                    difficulty = int(event.unicode)
                elif event.key == pygame.K_m:
                    current_state = GameState.MAIN_MENU
                elif event.key == pygame.K_UP:
                    audio_selected = (audio_selected - 1) % 3
                elif event.key == pygame.K_DOWN:
                    audio_selected = (audio_selected + 1) % 3
                elif event.key == pygame.K_LEFT:
                    if audio_selected == 0:
                        vol_music  = max(0.0, round(vol_music  - 0.1, 1))
                        pygame.mixer.music.set_volume(vol_music)
                    elif audio_selected == 1:
                        vol_engine = max(0.0, round(vol_engine - 0.1, 1))
                        if snd_engine: snd_engine.set_volume(vol_engine)
                    elif audio_selected == 2:
                        vol_siren  = max(0.0, round(vol_siren  - 0.1, 1))
                        if snd_siren: snd_siren.set_volume(vol_siren)
                elif event.key == pygame.K_RIGHT:
                    if audio_selected == 0:
                        vol_music  = min(1.0, round(vol_music  + 0.1, 1))
                        pygame.mixer.music.set_volume(vol_music)
                    elif audio_selected == 1:
                        vol_engine = min(1.0, round(vol_engine + 0.1, 1))
                        if snd_engine: snd_engine.set_volume(vol_engine)
                    elif audio_selected == 2:
                        vol_siren  = min(1.0, round(vol_siren  + 0.1, 1))
                        if snd_siren: snd_siren.set_volume(vol_siren)
                else:
                    set_hint("1-5: difficulty  ↑↓: pick audio  ←→: adjust  M: back")
 
        # ---- PLAYING ----
        elif current_state == GameState.PLAYING:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    current_state = GameState.MAIN_MENU
                elif event.key not in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_ESCAPE):
                    set_hint("Use ← → to turn  |  ESC to pause")
 
        # ---- GAME OVER ----
        elif current_state == GameState.GAME_OVER:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    g = reset(); spawn_obstacles(g)
                    current_state = GameState.PLAYING
                elif event.key == pygame.K_m:
                    current_state = GameState.MAIN_MENU
                else:
                    set_hint("Press R to replay  or  M for menu")
 
    # --- sound management ---
    if current_state == GameState.PLAYING and not g["dead"]:
        if snd_engine and not engine_playing:
            snd_engine.play(-1); engine_playing = True
    else:
        if snd_engine and engine_playing:
            snd_engine.stop();   engine_playing = False
 
    if current_state == GameState.PLAYING and not g["dead"]:
        police_on_screen = any(
            0 <= p["x"] - g["x"] + WIDTH//2  <= WIDTH and
            0 <= p["y"] - g["y"] + HEIGHT//2 <= HEIGHT
            for p in g["police"]
        )
        if snd_siren:
            if police_on_screen and not siren_playing:
                snd_siren.play(-1); siren_playing = True
            elif not police_on_screen and siren_playing:
                snd_siren.stop();   siren_playing = False
    else:
        if snd_siren and siren_playing:
            snd_siren.stop(); siren_playing = False
 
    # --- game logic ---
    if current_state == GameState.PLAYING and not g["dead"]:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:  g["angle"] -= 4 * turn_speed_multiplier[difficulty]
        if keys[pygame.K_RIGHT]: g["angle"] += 4 * turn_speed_multiplier[difficulty]
 
        speed  = 5 * difficulty_multiplier[difficulty]
        g["x"] += math.cos(math.radians(g["angle"])) * speed
        g["y"] += math.sin(math.radians(g["angle"])) * speed
 
        # --- pothole collision: damage not instant death ---
        invincible = (now - g["invincible_timer"]) < INVINCIBLE_DURATION
        if not invincible:
            for obs in g["obstacles"]:
                if math.hypot(g["x"] - obs["x"], g["y"] - obs["y"]) < obs["size"] + 20:
                    g["health"]       -= 1
                    g["invincible_timer"] = now
                    g["damage_flash"] = 20   # frames of red overlay
 
                    # knock the player back so they bounce out of the pothole
                    bounce = 60
                    g["x"] -= math.cos(math.radians(g["angle"])) * bounce
                    g["y"] -= math.sin(math.radians(g["angle"])) * bounce
 
                    if g["health"] <= 0:
                        g["dead"]     = True
                        g["end_time"] = now
                        current_state = GameState.GAME_OVER
                        if username:
                            scores = get_user_scores(username)
                            if g["score"] > scores.get(selected_level, 0):
                                scores[selected_level] = g["score"]
                                current_highscore      = g["score"]
                                save_highscores(highscores)
                    break
 
        # time bonus
        if now - g["time_bonus_timer"] > 5000:
            g["score"] += 1
            g["time_bonus_timer"] = now
 
        # spawn police
        spawn_rate = 3000 / difficulty_multiplier[difficulty]
        if now - g["spawn_timer"] > spawn_rate:
            side_angle = random.uniform(0, 360)
            g["police"].append({
                "x": g["x"] + math.cos(math.radians(side_angle)) * 500,
                "y": g["y"] + math.sin(math.radians(side_angle)) * 500,
                "angle": 0
            })
            g["spawn_timer"] = now
 
        for p in g["police"][:]:
            dx, dy = g["x"] - p["x"], g["y"] - p["y"]
            target = math.degrees(math.atan2(dy, dx))
            p["angle"] += ((target - p["angle"] + 180) % 360 - 180) * 0.04
            police_speed = 5.5 * difficulty_multiplier[difficulty]
            p["x"] += math.cos(math.radians(p["angle"])) * police_speed
            p["y"] += math.sin(math.radians(p["angle"])) * police_speed
 
            hit_obs = False
            for obs in g["obstacles"]:
                if math.hypot(p["x"] - obs["x"], p["y"] - obs["y"]) < obs["size"] + 18:
                    g["explosions"].append({"x": p["x"], "y": p["y"], "t": 20})
                    g["score"] += 1
                    g["police"].remove(p)
                    hit_obs = True
                    break
            if hit_obs:
                continue
 
            if math.hypot(g["x"] - p["x"], g["y"] - p["y"]) < 35:
                g["dead"]     = True
                g["end_time"] = now
                current_state = GameState.GAME_OVER
                if username:
                    scores = get_user_scores(username)
                    if g["score"] > scores.get(selected_level, 0):
                        scores[selected_level] = g["score"]
                        current_highscore      = g["score"]
                        save_highscores(highscores)
 
        # cop crash detection (flood fill)
        threshold = 30
        n   = len(g["police"])
        adj = [[] for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                if math.hypot(g["police"][i]["x"] - g["police"][j]["x"],
                              g["police"][i]["y"] - g["police"][j]["y"]) < threshold:
                    adj[i].append(j); adj[j].append(i)
 
        visited   = [False] * n
        to_remove = set()
        for i in range(n):
            if visited[i]: continue
            stack, group = [i], []
            while stack:
                u = stack.pop()
                if visited[u]: continue
                visited[u] = True; group.append(u)
                for v in adj[u]:
                    if not visited[v]: stack.append(v)
            if len(group) >= 2:
                for idx in group:
                    if idx not in to_remove and idx < len(g["police"]):
                        g["explosions"].append({"x": g["police"][idx]["x"],
                                                "y": g["police"][idx]["y"], "t": 20})
                        to_remove.add(idx)
                g["score"] += len(group)
 
        for idx in sorted(to_remove, reverse=True):
            if idx < len(g["police"]):
                g["police"].pop(idx)
 
    # --- draw ---
    if current_state == GameState.LOGIN:
        draw_login_screen()
    elif current_state == GameState.MAIN_MENU:
        draw_main_menu()
    elif current_state == GameState.LEVEL_SELECT:
        draw_level_select()
    elif current_state == GameState.OPTIONS:
        draw_options()
    elif current_state == GameState.PLAYING:
        draw_game()
    elif current_state == GameState.GAME_OVER:
        draw_game_over()
 
    pygame.display.flip()
 
pygame.quit()