import pygame
import math
import random
import os
import json
 
# --- setup ---
# initialise pygame and create the window
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Police Chase - DRIVE!")
clock = pygame.time.Clock()
 
# basic colours used everywhere
WHITE = (255, 255, 255)
GREEN = (40, 150, 40)
BROWN = (101, 67, 33)
RED = (200, 50, 50)
GRAY = (40, 40, 40)
ORANGE = (255, 140, 0)
BLUE = (80, 180, 255)
BLACK = (0, 0, 0)
DARK_GRAY = (60, 60, 60)
LIGHT_GREEN = (60, 180, 60)
# dim version used for arrow key widget when the key isnt held
KEY_OFF = (80, 80, 80)
# bright version used when the key is being pressed
KEY_ON = (255, 255, 255)
 
# four font sizes - large for titles, tiny for small HUD labels
font_large  = pygame.font.Font(None, 72)
font_medium = pygame.font.Font(None, 48)
font_small  = pygame.font.Font(None, 36)
font_tiny   = pygame.font.Font(None, 24)
 
# where the car/police images and audio files live
ASSETS_DIR    = os.path.join(os.path.dirname(__file__), "assets")
HIGHSCORE_FILE = os.path.join(os.path.dirname(__file__), "highscores.json")
 
 
# --- audio loading ---
 
# tries .wav, .mp3, .ogg in order and returns the first one that works
# returns None if no matching file is found so the game still runs without audio
def load_sound(name):
    for ext in [".wav", ".mp3", ".ogg"]:
        path = os.path.join(ASSETS_DIR, name + ext)
        if os.path.exists(path):
            try:
                return pygame.mixer.Sound(path)
            except Exception:
                pass
    return None
 
# same idea but just returns the file path for pygame.mixer.music
def load_music(name):
    for ext in [".wav", ".mp3", ".ogg"]:
        path = os.path.join(ASSETS_DIR, name + ext)
        if os.path.exists(path):
            return path
    return None
 
# load all three audio files
snd_engine = load_sound("engine")
snd_siren  = load_sound("siren")
music_path = load_music("music")
 
# set default volumes so nothing blasts at full
if snd_engine: snd_engine.set_volume(0.4)
if snd_siren:  snd_siren.set_volume(0.5)
 
# start background music looping immediately when the game opens
if music_path:
    pygame.mixer.music.load(music_path)
    pygame.mixer.music.set_volume(0.3)
    pygame.mixer.music.play(-1)  # -1 means loop forever
 
# booleans to track whether each looping sound is currently active
# without these we would call .play() every single frame
engine_playing = False
siren_playing  = False
 
# current volume for each channel, updated when player adjusts the bars
vol_music  = 0.3
vol_engine = 0.4
vol_siren  = 0.5
 
# which audio row is highlighted in the options screen (0=music 1=engine 2=siren)
audio_selected = 0
 
 
# --- highscore file helpers ---
 
def load_highscores():
    # read the json file if it exists, otherwise start with an empty dict
    if os.path.exists(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}
 
def save_highscores(highscores):
    # write scores back to the json file, silently fails if theres a permission error
    try:
        with open(HIGHSCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(highscores, f, indent=2)
    except Exception:
        pass
 
 
# --- background image helper ---
 
def ensure_background_image(name, generator, size=(WIDTH, HEIGHT), scale=True):
    # load from file if it already exists and is the right size
    # otherwise generate it, save it, and return the surface
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
 
# draws grass blades and dark patches so it doesnt look flat
def _generate_grass_bg(surf):
    w, h = surf.get_size()
    surf.fill(GREEN)
    # 1200 short random lines to look like individual blades
    for _ in range(1200):
        x = random.randint(0, w)
        y = random.randint(0, h)
        grass_color = random.choice([(30, 130, 30), (35, 145, 35), (25, 120, 25), (60, 180, 60)])
        pygame.draw.line(surf, grass_color, (x, y), (x + random.randint(1, 3), y + random.randint(2, 5)), 1)
    # 60 darker circles for shadowy patches
    for _ in range(60):
        x = random.randint(0, w - 50)
        y = random.randint(0, h - 50)
        pygame.draw.circle(surf, (20, 100, 20), (x, y), random.randint(10, 30))
 
# tile is 200x200, tiled across the screen each frame as the player moves
GRASS_TILE_SIZE = (200, 200)
grass_bg = ensure_background_image("grass1.png", _generate_grass_bg, size=GRASS_TILE_SIZE, scale=False)
 
 
# --- asset loading ---
 
# tries to load the image file, falls back to a coloured rectangle if missing
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
 
car_img    = load_asset("carok.png",    BLUE)
police_img = load_asset("policecar.png", RED)
 
 
# --- game state ---
 
# integer constants for each screen, stored in a class to keep them together
class GameState:
    LOGIN       = 0
    MAIN_MENU   = 1
    LEVEL_SELECT = 2
    PLAYING     = 3
    GAME_OVER   = 4
    OPTIONS     = 5
 
current_state  = GameState.LOGIN
username       = ""
selected_level = "grass"
highscores     = load_highscores()
current_highscore = 0
login_context  = "new"  # "new" on first launch, "change" when swapping users
 
def get_user_scores(name):
    # create a blank entry if this username hasnt played before
    if name not in highscores or not isinstance(highscores[name], dict):
        highscores[name] = {"grass": 0, "highway": 0}
    else:
        highscores[name].setdefault("grass", 0)
        highscores[name].setdefault("highway", 0)
    return highscores[name]
 
def update_current_highscore():
    # refresh the displayed high score to match the current user and level
    global current_highscore
    if username:
        scores = get_user_scores(username)
        current_highscore = scores.get(selected_level, 0)
    else:
        current_highscore = 0
 
difficulty = 3  # default is medium
# these dicts map difficulty 1-5 to a speed/turn multiplier
difficulty_multiplier  = {1: 0.5, 2: 0.75, 3: 1.0, 4: 1.25, 5: 1.5}
turn_speed_multiplier  = {1: 0.5, 2: 0.75, 3: 1.0, 4: 1.25, 5: 1.5}
 
def reset():
    # fresh game state - called at the start and whenever the player replays
    return {
        "x": 0, "y": 0, "angle": 0,
        "police": [], "explosions": [],
        "obstacles": [],
        "score": 0, "dead": False, "start_time": pygame.time.get_ticks(),
        "spawn_timer": 0, "time_bonus_timer": 0
    }
 
def spawn_obstacles(game_state, count=35):
    # pick colour based on which level is loaded
    if selected_level == "grass":
        color = (80, 50, 20)   # dark brown rocks
    else:
        color = (255, 100, 0)  # orange cones
 
    # first wave - spread around the normal play area
    for _ in range(count):
        ox = random.randint(-2000, 2000)
        oy = random.randint(-2000, 2000)
        # dont spawn right on top of the player start position
        if math.hypot(ox, oy) < 200:
            continue
        size = random.randint(18, 30)
        game_state["obstacles"].append({"x": ox, "y": oy, "size": size, "color": color})
 
    # second wave - further out so theres stuff waiting when you drive far
    for _ in range(25):
        ox = random.randint(-5000, 5000)
        oy = random.randint(-5000, 5000)
        # only place these in the outer ring, not overlapping the first wave area
        if math.hypot(ox, oy) < 2200:
            continue
        size = random.randint(18, 30)
        game_state["obstacles"].append({"x": ox, "y": oy, "size": size, "color": color})
 
# initialise the first game and obstacle set before the loop starts
g = reset()
spawn_obstacles(g)
running = True
 
 
# --- input box class ---
 
class InputBox:
    # simple text input used on the login screen
    def __init__(self, x, y, w, h):
        self.rect  = pygame.Rect(x, y, w, h)
        self.text  = ""
        self.active = True
 
    def handle_event(self, event):
        # backspace removes the last character, printable keys get appended
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode.isprintable() and len(self.text) < 20:
                self.text += event.unicode
 
    def draw(self, surface):
        # white border box with the current text inside
        pygame.draw.rect(surface, WHITE, self.rect, 3)
        text_surf = font_small.render(self.text, True, WHITE)
        surface.blit(text_surf, (self.rect.x + 10, self.rect.y + 10))
 
input_box = InputBox(WIDTH//2 - 150, HEIGHT//2 + 50, 300, 60)
 
 
# --- screen drawing functions ---
 
def draw_login_screen():
    screen.fill(DARK_GRAY)
    # title changes depending on whether the player is logging in fresh or swapping accounts
    if login_context == "change":
        title = font_large.render("CHANGE USER", True, LIGHT_GREEN)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 80))
        # show who is currently signed in so they know who theyre replacing
        if username:
            logged_in_text = font_tiny.render(f"Logged in as: {username}", True, ORANGE)
            screen.blit(logged_in_text, (WIDTH//2 - logged_in_text.get_width()//2, 165))
    else:
        title = font_large.render("POLICE CHASE", True, ORANGE)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 80))
    prompt = font_medium.render("Enter Username:", True, WHITE)
    screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, HEIGHT//2 - 100))
    input_box.draw(screen)
    hint = font_tiny.render("Press ENTER to continue", True, WHITE)
    screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 50))
 
def draw_main_menu():
    screen.fill(DARK_GRAY)
    title = font_large.render("POLICE CHASE", True, ORANGE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    # greet the player by name once they've logged in
    welcome = font_small.render(f"Welcome, {username}!", True, LIGHT_GREEN)
    screen.blit(welcome, (WIDTH//2 - welcome.get_width()//2, 150))
    play_text = font_medium.render("1. PLAY", True, WHITE)
    screen.blit(play_text, (WIDTH//2 - play_text.get_width()//2, 230))
    options_text = font_medium.render("2. OPTIONS", True, WHITE)
    screen.blit(options_text, (WIDTH//2 - options_text.get_width()//2, 300))
    quit_text = font_medium.render("3. QUIT", True, WHITE)
    screen.blit(quit_text, (WIDTH//2 - quit_text.get_width()//2, 370))
    # change user sits at the bottom in green so it stands out from the other options
    change_text = font_medium.render("4. CHANGE USER", True, LIGHT_GREEN)
    screen.blit(change_text, (WIDTH//2 - change_text.get_width()//2, 440))
    hint = font_tiny.render("Press 1, 2, 3, or 4", True, WHITE)
    screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 50))
 
def draw_level_select():
    screen.fill(DARK_GRAY)
    title = font_large.render("SELECT LEVEL", True, ORANGE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    # pull scores for this user so we can show their best on each map
    scores = get_user_scores(username) if username else {"grass": 0, "highway": 0}
    grass_score_text   = font_small.render(f"Grass High Score: {scores.get('grass', 0)}",   True, WHITE)
    highway_score_text = font_small.render(f"Highway High Score: {scores.get('highway', 0)}", True, WHITE)
    screen.blit(grass_score_text,   (WIDTH//2 - grass_score_text.get_width()//2,   130))
    screen.blit(highway_score_text, (WIDTH//2 - highway_score_text.get_width()//2, 160))
    # grass level button - green rectangle
    grass_rect = pygame.Rect(80, 250, 280, 150)
    pygame.draw.rect(screen, GREEN, grass_rect)
    pygame.draw.rect(screen, WHITE, grass_rect, 3)
    grass_text = font_medium.render("GRASSY LAND", True, WHITE)
    screen.blit(grass_text, (grass_rect.centerx - grass_text.get_width()//2, grass_rect.y + 30))
    click_text = font_tiny.render("Press 1", True, WHITE)
    screen.blit(click_text, (grass_rect.centerx - click_text.get_width()//2, grass_rect.y + 100))
    # highway level button - gray rectangle
    highway_rect = pygame.Rect(440, 250, 280, 150)
    pygame.draw.rect(screen, GRAY, highway_rect)
    pygame.draw.rect(screen, WHITE, highway_rect, 3)
    highway_text = font_medium.render("HIGHWAY", True, WHITE)
    screen.blit(highway_text, (highway_rect.centerx - highway_text.get_width()//2, highway_rect.y + 30))
    click_text = font_tiny.render("Press 2", True, WHITE)
    screen.blit(click_text, (highway_rect.centerx - click_text.get_width()//2, highway_rect.y + 100))
    back_text = font_tiny.render("Press M to return to menu", True, WHITE)
    screen.blit(back_text, (WIDTH//2 - back_text.get_width()//2, HEIGHT - 50))
    return grass_rect, highway_rect
 
 
# --- volume bar helper ---
 
def draw_volume_bar(label, volume, y, selected):
    # draws one labelled row with a fillable bar and a percentage readout
    # the label and fill turn orange when this row is selected
    label_color = ORANGE if selected else WHITE
    label_surf  = font_small.render(label, True, label_color)
    screen.blit(label_surf, (80, y))
 
    # background track - always full width so you can see the whole range
    bar_x = 260
    bar_y = y + 4
    bar_w = 300
    bar_h = 22
    pygame.draw.rect(screen, GRAY, (bar_x, bar_y, bar_w, bar_h))
 
    # filled portion scales with the current volume value
    filled_w   = int(bar_w * volume)
    fill_color = ORANGE if selected else LIGHT_GREEN
    if filled_w > 0:
        pygame.draw.rect(screen, fill_color, (bar_x, bar_y, filled_w, bar_h))
 
    # white border so the bar reads clearly on dark background
    pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_w, bar_h), 2)
 
    # percentage number to the right so the player knows the exact value
    pct = font_tiny.render(f"{int(volume * 100)}%", True, WHITE)
    screen.blit(pct, (bar_x + bar_w + 10, bar_y + 2))
 
def draw_options():
    screen.fill(DARK_GRAY)
    title = font_large.render("OPTIONS", True, ORANGE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
 
    # difficulty section - press 1-5 to change
    difficulty_label = font_medium.render("DIFFICULTY", True, WHITE)
    screen.blit(difficulty_label, (WIDTH//2 - difficulty_label.get_width()//2, 110))
    difficulties = [
        (1, "EASY",    WHITE),
        (2, "NORMAL",  LIGHT_GREEN),
        (3, "MEDIUM",  ORANGE),
        (4, "HARD",    RED),
        (5, "EXTREME", (255, 0, 0))
    ]
    current_diff_text = font_small.render(f"Current: {difficulty}", True, ORANGE)
    screen.blit(current_diff_text, (WIDTH//2 - current_diff_text.get_width()//2, 155))
    y_pos = 190
    for num, name, color in difficulties:
        # << markers show which difficulty is active
        marker = "<<" if num == difficulty else "  "
        text = font_tiny.render(f"{marker} {num}. {name} {marker}", True, color)
        screen.blit(text, (WIDTH//2 - text.get_width()//2, y_pos))
        y_pos += 28
 
    # audio section - up/down to select a bar, left/right to adjust it
    audio_label = font_medium.render("AUDIO", True, WHITE)
    screen.blit(audio_label, (WIDTH//2 - audio_label.get_width()//2, 350))
    draw_volume_bar("MUSIC",  vol_music,  390, audio_selected == 0)
    draw_volume_bar("ENGINE", vol_engine, 430, audio_selected == 1)
    draw_volume_bar("SIREN",  vol_siren,  470, audio_selected == 2)
 
    hint = font_tiny.render("Press 1-5 for difficulty  |  UP/DOWN to pick audio  |  LEFT/RIGHT to adjust", True, WHITE)
    screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 80))
    back_text = font_tiny.render("Press M to return to menu", True, WHITE)
    screen.blit(back_text, (WIDTH//2 - back_text.get_width()//2, HEIGHT - 50))
 
 
# --- arrow key widget ---
 
# draws the left/right arrow triangles in the bottom right corner
# each one lights up white when its key is held, stays dark gray when not
def draw_arrow_keys(keys):
    # anchor point for the whole widget
    base_x = WIDTH - 160
    base_y = HEIGHT - 60
 
    # left arrow - triangle pointing left
    left_cx    = base_x
    left_cy    = base_y
    left_color = KEY_ON if keys[pygame.K_LEFT] else KEY_OFF
    left_points = [
        (left_cx - 28, left_cy),       # tip (leftmost point)
        (left_cx + 12, left_cy - 22),  # top right corner
        (left_cx + 12, left_cy + 22),  # bottom right corner
    ]
    pygame.draw.polygon(screen, left_color, left_points)
    # thin black border so it reads on any background colour
    pygame.draw.polygon(screen, BLACK, left_points, 2)
 
    # small label between the two arrows
    label = font_tiny.render("TURN", True, (120, 120, 120))
    screen.blit(label, (base_x + 18, base_y - 8))
 
    # right arrow - mirrored version of the left one
    right_cx    = base_x + 110
    right_cy    = base_y
    right_color = KEY_ON if keys[pygame.K_RIGHT] else KEY_OFF
    right_points = [
        (right_cx + 28, right_cy),       # tip (rightmost point)
        (right_cx - 12, right_cy - 22),  # top left corner
        (right_cx - 12, right_cy + 22),  # bottom left corner
    ]
    pygame.draw.polygon(screen, right_color, right_points)
    pygame.draw.polygon(screen, BLACK, right_points, 2)
 
 
# --- gameplay drawing ---
 
def draw_game():
    # converts a world coordinate to a screen pixel position
    # the player is always at the centre so everything else shifts around them
    def world_to_screen(wx, wy):
        return wx - g["x"] + WIDTH//2, wy - g["y"] + HEIGHT//2
 
    if selected_level == "grass":
        # tile the grass texture so it scrolls without a seam
        tile_w, tile_h = grass_bg.get_size()
        offset_x = int(g["x"]) % tile_w
        offset_y = int(g["y"]) % tile_h
        for ix in range(-1, WIDTH // tile_w + 2):
            for iy in range(-1, HEIGHT // tile_h + 2):
                screen.blit(grass_bg, (ix * tile_w - offset_x, iy * tile_h - offset_y))
    else:
        # grass fills the whole screen first, road sits on top in world space
        screen.fill(GREEN)
        road_width = 400
        # road is centred at world x=0, converted to screen each frame
        road_x_screen, _ = world_to_screen(-road_width // 2, 0)
        # road is very tall so you never see the top or bottom end while driving
        road_height = 6000
        _, road_y_screen = world_to_screen(0, -road_height // 2)
        pygame.draw.rect(screen, DARK_GRAY, (road_x_screen, road_y_screen, road_width, road_height))
        # lane dividers follow the road in world space
        lane_count = 3
        lane_width = road_width // lane_count
        for j in range(1, lane_count):
            lane_x_screen = road_x_screen + j * lane_width
            for y in range(0, road_height, 40):
                pygame.draw.rect(screen, WHITE, (lane_x_screen - 2, road_y_screen + y, 4, 20))
        # orange kerb strips on both edges
        pygame.draw.rect(screen, ORANGE, (road_x_screen, road_y_screen, 6, road_height))
        pygame.draw.rect(screen, ORANGE, (road_x_screen + road_width - 6, road_y_screen, 6, road_height))
 
    # draw rocks or cones at their world positions
    for obs in g["obstacles"]:
        ox, oy = world_to_screen(obs["x"], obs["y"])
        pygame.draw.circle(screen, obs["color"], (int(ox), int(oy)), obs["size"])
 
    # draw all police cars
    for p in g["police"]:
        img = pygame.transform.rotate(police_img, -p["angle"])
        screen.blit(img, img.get_rect(center=(p["x"] - g["x"] + WIDTH//2, p["y"] - g["y"] + HEIGHT//2)))
 
    # red arrows point toward cops that have gone off screen
    for p in g["police"]:
        px = p["x"] - g["x"] + WIDTH//2
        py = p["y"] - g["y"] + HEIGHT//2
        if px < 0 or px > WIDTH or py < 0 or py > HEIGHT:
            # clamp the arrow to the screen edge
            arrow_x = min(max(px, 20), WIDTH - 20)
            arrow_y = min(max(py, 20), HEIGHT - 20)
            dx = px - WIDTH//2
            dy = py - HEIGHT//2
            angle  = math.atan2(dy, dx)
            length = 30
            tip_x  = arrow_x + math.cos(angle) * length
            tip_y  = arrow_y + math.sin(angle) * length
            pygame.draw.line(screen, RED, (arrow_x, arrow_y), (tip_x, tip_y), 4)
            # arrowhead lines on each side of the tip
            left  = angle + math.pi * 0.75
            right = angle - math.pi * 0.75
            pygame.draw.line(screen, RED, (tip_x, tip_y), (tip_x + math.cos(left)  * 12, tip_y + math.sin(left)  * 12), 3)
            pygame.draw.line(screen, RED, (tip_x, tip_y), (tip_x + math.cos(right) * 12, tip_y + math.sin(right) * 12), 3)
 
    # player car is always drawn dead centre on the screen
    p_img = pygame.transform.rotate(car_img, -g["angle"])
    screen.blit(p_img, p_img.get_rect(center=(WIDTH//2, HEIGHT//2)))
 
    # username floats just above the player car
    username_text = font_small.render(username, True, WHITE)
    screen.blit(username_text, (WIDTH//2 - username_text.get_width()//2, HEIGHT//2 - 80))
 
    # shrink the explosion circle over time until it disappears
    for exp in g["explosions"][:]:
        exp["t"] -= 1
        if exp["t"] <= 0:
            g["explosions"].remove(exp)
        else:
            size = int(30 * (1 - exp["t"] / 20))
            pygame.draw.circle(screen, ORANGE, (int(exp["x"] - g["x"] + WIDTH//2),
                                                int(exp["y"] - g["y"] + HEIGHT//2)), size)
 
    # top left HUD - time, score, difficulty, obstacle count
    elapsed = (pygame.time.get_ticks() - g["start_time"]) // 1000
    time_text = font_small.render(f"TIME: {elapsed}s", True, WHITE)
    screen.blit(time_text, (20, 20))
    score_surf = font_small.render(f"SCORE: {g['score']}", True, WHITE)
    screen.blit(score_surf, (20, 70))
    difficulty_text = font_tiny.render(f"DIFFICULTY: {difficulty}", True, ORANGE)
    screen.blit(difficulty_text, (20, 120))
    obs_text = font_tiny.render(f"OBSTACLES: {len(g['obstacles'])}", True, BROWN)
    screen.blit(obs_text, (20, 145))
 
    # read which keys are held and pass to the arrow key widget
    keys = pygame.key.get_pressed()
    draw_arrow_keys(keys)
 
def draw_game_over():
    screen.fill(DARK_GRAY)
    over_text = font_large.render("BUSTED!", True, RED)
    screen.blit(over_text, (WIDTH//2 - over_text.get_width()//2, 80))
    # use end_time so the displayed time freezes at the moment of death
    elapsed = (g["end_time"] - g["start_time"]) // 1000
    time_text = font_medium.render(f"Time: {elapsed}s", True, WHITE)
    screen.blit(time_text, (WIDTH//2 - time_text.get_width()//2, 200))
    score_text = font_medium.render(f"Score: {g['score']}", True, WHITE)
    screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 280))
    diff_text = font_small.render(f"Difficulty: {difficulty}", True, ORANGE)
    screen.blit(diff_text, (WIDTH//2 - diff_text.get_width()//2, 350))
    replay_text = font_small.render("Press R to Replay or M for Menu", True, ORANGE)
    screen.blit(replay_text, (WIDTH//2 - replay_text.get_width()//2, HEIGHT - 80))
 
 
# --- main loop ---
 
while running:
    clock.tick(60)  # cap at 60 fps
    now = pygame.time.get_ticks()
 
    # --- event handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
 
        if current_state == GameState.LOGIN:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and len(input_box.text) > 0:
                    # confirm the username and head to the main menu
                    username      = input_box.text
                    login_context = "new"
                    update_current_highscore()
                    current_state = GameState.MAIN_MENU
                else:
                    input_box.handle_event(event)
 
        elif current_state == GameState.MAIN_MENU:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    current_state = GameState.LEVEL_SELECT
                elif event.key == pygame.K_2:
                    current_state = GameState.OPTIONS
                elif event.key == pygame.K_3:
                    running = False
                elif event.key == pygame.K_4:
                    # clear the input box so the old name doesnt pre-fill
                    login_context = "change"
                    input_box.text = ""
                    current_state  = GameState.LOGIN
 
        elif current_state == GameState.LEVEL_SELECT:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    selected_level = "grass"
                    update_current_highscore()
                    g = reset()
                    spawn_obstacles(g)
                    current_state = GameState.PLAYING
                elif event.key == pygame.K_2:
                    selected_level = "highway"
                    update_current_highscore()
                    g = reset()
                    spawn_obstacles(g)
                    current_state = GameState.PLAYING
                elif event.key == pygame.K_m:
                    current_state = GameState.MAIN_MENU
 
        elif current_state == GameState.OPTIONS:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]:
                    difficulty = int(event.unicode)
                elif event.key == pygame.K_m:
                    current_state = GameState.MAIN_MENU
                # up/down moves the highlight between the three audio bars
                elif event.key == pygame.K_UP:
                    audio_selected = (audio_selected - 1) % 3
                elif event.key == pygame.K_DOWN:
                    audio_selected = (audio_selected + 1) % 3
                # left/right adjusts the selected bar by 10%, clamped to 0-1
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
 
        elif current_state == GameState.PLAYING:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                current_state = GameState.MAIN_MENU
 
        elif current_state == GameState.GAME_OVER:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    g = reset()
                    spawn_obstacles(g)
                    current_state = GameState.PLAYING
                elif event.key == pygame.K_m:
                    current_state = GameState.MAIN_MENU
 
    # --- sound management ---
    # engine loops while the player is alive and playing, stops otherwise
    if current_state == GameState.PLAYING and not g["dead"]:
        if snd_engine and not engine_playing:
            snd_engine.play(-1)
            engine_playing = True
    else:
        if snd_engine and engine_playing:
            snd_engine.stop()
            engine_playing = False
 
    # siren loops whenever at least one cop is visible on screen
    if current_state == GameState.PLAYING and not g["dead"]:
        police_on_screen = any(
            0 <= p["x"] - g["x"] + WIDTH//2 <= WIDTH and
            0 <= p["y"] - g["y"] + HEIGHT//2 <= HEIGHT
            for p in g["police"]
        )
        if snd_siren:
            if police_on_screen and not siren_playing:
                snd_siren.play(-1)
                siren_playing = True
            elif not police_on_screen and siren_playing:
                snd_siren.stop()
                siren_playing = False
    else:
        # make sure siren stops when leaving the play screen
        if snd_siren and siren_playing:
            snd_siren.stop()
            siren_playing = False
 
    # --- game logic ---
    if current_state == GameState.PLAYING and not g["dead"]:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:  g["angle"] -= 4 * turn_speed_multiplier[difficulty]
        if keys[pygame.K_RIGHT]: g["angle"] += 4 * turn_speed_multiplier[difficulty]
 
        # move the player forward along their current angle
        speed = 5 * difficulty_multiplier[difficulty]
        g["x"] += math.cos(math.radians(g["angle"])) * speed
        g["y"] += math.sin(math.radians(g["angle"])) * speed
 
        # check if the player drove into a rock or cone
        for obs in g["obstacles"]:
            if math.hypot(g["x"] - obs["x"], g["y"] - obs["y"]) < obs["size"] + 20:
                g["dead"]    = True
                g["end_time"] = pygame.time.get_ticks()
                current_state = GameState.GAME_OVER
                if username:
                    scores = get_user_scores(username)
                    if g["score"] > scores.get(selected_level, 0):
                        scores[selected_level] = g["score"]
                        current_highscore      = g["score"]
                        save_highscores(highscores)
                break
 
        # give a point every 5 seconds just for staying alive
        if now - g["time_bonus_timer"] > 5000:
            g["score"] += 1
            g["time_bonus_timer"] = now
 
        # spawn a new cop on a random side, faster on higher difficulties
        spawn_rate = 3000 / difficulty_multiplier[difficulty]
        if now - g["spawn_timer"] > spawn_rate:
            side_angle = random.uniform(0, 360)
            spawn_x = g["x"] + math.cos(math.radians(side_angle)) * 500
            spawn_y = g["y"] + math.sin(math.radians(side_angle)) * 500
            g["police"].append({"x": spawn_x, "y": spawn_y, "angle": 0})
            g["spawn_timer"] = now
 
        for p in g["police"][:]:
            # steer the cop toward the player each frame using a smooth turn
            dx, dy  = g["x"] - p["x"], g["y"] - p["y"]
            target  = math.degrees(math.atan2(dy, dx))
            p["angle"] += ((target - p["angle"] + 180) % 360 - 180) * 0.04
            police_speed = 5.5 * difficulty_multiplier[difficulty]
            p["x"] += math.cos(math.radians(p["angle"])) * police_speed
            p["y"] += math.sin(math.radians(p["angle"])) * police_speed
 
            # cop hits an obstacle - blow it up and give the player a point
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
 
            # cop touches the player - game over
            if math.hypot(g["x"] - p["x"], g["y"] - p["y"]) < 35:
                g["dead"]     = True
                g["end_time"] = pygame.time.get_ticks()
                current_state = GameState.GAME_OVER
                if username:
                    scores = get_user_scores(username)
                    prev = scores.get(selected_level, 0)
                    if g["score"] > prev:
                        scores[selected_level] = g["score"]
                        current_highscore      = g["score"]
                        save_highscores(highscores)
 
        # build an adjacency list for cops that are close enough to have crashed
        threshold = 30
        n   = len(g["police"])
        adj = [[] for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                p1 = g["police"][i]
                p2 = g["police"][j]
                if math.hypot(p1["x"] - p2["x"], p1["y"] - p2["y"]) < threshold:
                    adj[i].append(j)
                    adj[j].append(i)
 
        # flood fill to find connected crash groups, then remove and explode them all
        visited   = [False] * n
        to_remove = set()
        for i in range(n):
            if visited[i]:
                continue
            stack = [i]
            group = []
            while stack:
                u = stack.pop()
                if visited[u]:
                    continue
                visited[u] = True
                group.append(u)
                for v in adj[u]:
                    if not visited[v]:
                        stack.append(v)
            if len(group) >= 2:
                for idx in group:
                    if idx not in to_remove and idx < len(g["police"]):
                        p = g["police"][idx]
                        g["explosions"].append({"x": p["x"], "y": p["y"], "t": 20})
                        to_remove.add(idx)
                g["score"] += len(group)
 
        # remove in reverse order so the indices dont shift as we delete
        for idx in sorted(to_remove, reverse=True):
            if idx < len(g["police"]):
                g["police"].pop(idx)
 
    # --- draw the correct screen ---
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
 
    pygame.display.flip()  # push everything drawn this frame to the screen
 
pygame.quit()