import pygame
import math
import random
import os
import json

# --- makes screen visible - - -
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Police Chase - DRIVE!")
clock = pygame.time.Clock()

# Colors for the brain of the code
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

# a data base for fonts needed
font_large = pygame.font.Font(None, 72)
font_medium = pygame.font.Font(None, 48)
font_small = pygame.font.Font(None, 36)
font_tiny = pygame.font.Font(None, 24)

# --- HIGH SCORE STORAGE ---
HIGHSCORE_FILE = os.path.join(os.path.dirname(__file__), "highscores.json")

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

# --- BACKGROUND IMAGE HELPERS ---
def ensure_background_image(name, generator, size=(WIDTH, HEIGHT), scale=True):
    path = os.path.join(os.path.dirname(__file__), name)
    if os.path.exists(path):
        try:
            img = pygame.image.load(path).convert()
            if img.get_size() != size:
                # regenerate if saved image is wrong size
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

# --- GRASS TEXTURE ---
# NOTE: this texture is saved/loaded as an image file named grass1.png
def _generate_grass_bg(surf):
    w, h = surf.get_size()
    surf.fill(GREEN)
    # Create grass detail
    for _ in range(1200):
        x = random.randint(0, w)
        y = random.randint(0, h)
        grass_color = random.choice([(30, 130, 30), (35, 145, 35), (25, 120, 25), (60, 180, 60)])
        pygame.draw.line(surf, grass_color, (x, y), (x + random.randint(1, 3), y + random.randint(2, 5)), 1)
    # Add some darker patches for variation
    for _ in range(60):
        x = random.randint(0, w - 50)
        y = random.randint(0, h - 50)
        pygame.draw.circle(surf, (20, 100, 20), (x, y), random.randint(10, 30))

# load the grass tile from file (or create it if missing)
# grass1.png acts as a repeating tile texture
GRASS_TILE_SIZE = (200, 200)
grass_bg = ensure_background_image("grass1.png", _generate_grass_bg, size=GRASS_TILE_SIZE, scale=False)

# --- ASSET LOADING --- eg car, grass, police car
def load_asset(name, color):
    try:
        path = os.path.join(os.path.dirname(__file__), name)
        img = pygame.image.load(path).convert_alpha()
        img = pygame.transform.scale(img, (60, 120))
        return pygame.transform.rotate(img, 90)
    except:
        surf = pygame.Surface((60, 120), pygame.SRCALPHA)
        surf.fill(color)
        return pygame.transform.rotate(surf, 90)

car_img = load_asset("carok.png", BLUE)
police_img = load_asset("policecar.png", RED)

# --- GAME STATES that define the different screens ---
class GameState:
    LOGIN = 0
    MAIN_MENU = 1
    LEVEL_SELECT = 2
    PLAYING = 3
    GAME_OVER = 4
    OPTIONS = 5

current_state = GameState.LOGIN
username = "" # the username of the current player, used for high score tracking
selected_level = "grass" #check which level is selected for high score tracking (grass or highway)
# High score persistence (username -> {level: score})
highscores = load_highscores()
current_highscore = 0

def get_user_scores(name): #stores highscores for each user and level, initializes if new user
    if name not in highscores or not isinstance(highscores[name], dict):
        highscores[name] = {"grass": 0, "highway": 0}
    else:
        # Ensure both levels exist
        highscores[name].setdefault("grass", 0)
        highscores[name].setdefault("highway", 0)
    return highscores[name]


def update_current_highscore(): #if new highscore is achieved, update the high score for the current user and level
    global current_highscore
    if username:
        scores = get_user_scores(username)
        current_highscore = scores.get(selected_level, 0)
    else:
        current_highscore = 0

difficulty = 3  # 1-5, default 3 changes police speed, spawn rate, and turn speed due to different difficulty multipliers. Higher difficulty means faster police, more frequent spawns, and sharper turns.
difficulty_multiplier = {1: 0.5, 2: 0.75, 3: 1.0, 4: 1.25, 5: 1.5}
turn_speed_multiplier = {1: 0.5, 2: 0.75, 3: 1.0, 4: 1.25, 5: 1.5}

# --- GAME STATE ---
def reset():
    return {
        "x": 0, "y": 0, "angle": 0,
        "police": [], "explosions": [],
        "score": 0, "dead": False, "start_time": pygame.time.get_ticks(),
        "spawn_timer": 0, "time_bonus_timer": 0
    }

g = reset()
running = True

# --- INPUT BOX ---
class InputBox:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = ""
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

input_box = InputBox(WIDTH//2 - 150, HEIGHT//2 + 50, 300, 60)

# --- making the main menus and other screens ---
def draw_login_screen():
    screen.fill(DARK_GRAY)
    title = font_large.render("POLICE CHASE", True, ORANGE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 80))
    
    prompt = font_medium.render("Enter Username:", True, WHITE)
    screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, HEIGHT//2 - 100))
    
    input_box.draw(screen)
    
    hint = font_tiny.render("Press ENTER to continue", True, GRAY)
    screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 50))

def draw_main_menu():
    screen.fill(DARK_GRAY)
    title = font_large.render("POLICE CHASE", True, ORANGE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    
    welcome = font_small.render(f"Welcome, {username}!", True, LIGHT_GREEN)
    screen.blit(welcome, (WIDTH//2 - welcome.get_width()//2, 150))
    
    # Menu Options that lead to different screens, also display current high score for selected level
    play_text = font_medium.render("1. PLAY", True, WHITE)
    screen.blit(play_text, (WIDTH//2 - play_text.get_width()//2, 250))
    #brings to the options screen where you change the difficulty settings
    options_text = font_medium.render("2. OPTIONS", True, WHITE)
    screen.blit(options_text, (WIDTH//2 - options_text.get_width()//2, 330))
    #quits the game
    quit_text = font_medium.render("3. QUIT", True, WHITE)
    screen.blit(quit_text, (WIDTH//2 - quit_text.get_width()//2, 410))
    #tells the user how to navigate screens
    hint = font_tiny.render("Press 1, 2, or 3", True, WHITE)
    screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 50))
    #tells the user what to do
def draw_level_select():
    screen.fill(DARK_GRAY)
    title = font_large.render("SELECT LEVEL", True, ORANGE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))

    # Display high score for both maps
    scores = get_user_scores(username) if username else {"grass": 0, "highway": 0}
    grass_score_text = font_small.render(f"Grass High Score: {scores.get('grass', 0)}", True, WHITE)
    highway_score_text = font_small.render(f"Highway High Score: {scores.get('highway', 0)}", True, WHITE)
    screen.blit(grass_score_text, (WIDTH//2 - grass_score_text.get_width()//2, 130))
    screen.blit(highway_score_text, (WIDTH//2 - highway_score_text.get_width()//2, 160))
    
    # when Grass Level is selected, the player will be on a grassy field with no roads, just open space and grass textures. 
    grass_rect = pygame.Rect(80, 250, 280, 150)
    pygame.draw.rect(screen, GREEN, grass_rect)
    pygame.draw.rect(screen, WHITE, grass_rect, 3)
    grass_text = font_medium.render("GRASSY LAND", True, WHITE)
    screen.blit(grass_text, (grass_rect.centerx - grass_text.get_width()//2, grass_rect.y + 30))
    click_text = font_tiny.render("Press 1", True, GRAY)
    screen.blit(click_text, (grass_rect.centerx - click_text.get_width()//2, grass_rect.y + 100))
    
    # puts player in the Highway Level and draws it
    highway_rect = pygame.Rect(440, 250, 280, 150)
    pygame.draw.rect(screen, GRAY, highway_rect)
    pygame.draw.rect(screen, WHITE, highway_rect, 3)
    highway_text = font_medium.render("HIGHWAY", True, WHITE)
    screen.blit(highway_text, (highway_rect.centerx - highway_text.get_width()//2, highway_rect.y + 30))
    click_text = font_tiny.render("Press 2", True, GRAY)
    screen.blit(click_text, (highway_rect.centerx - click_text.get_width()//2, highway_rect.y + 100))
    #tells player how to navigate screens
    back_text = font_tiny.render("Press M to return to menu", True, GRAY)
    screen.blit(back_text, (WIDTH//2 - back_text.get_width()//2, HEIGHT - 50))
    
    return grass_rect, highway_rect

def draw_options():
    screen.fill(DARK_GRAY)
    title = font_large.render("OPTIONS", True, ORANGE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    
    difficulty_label = font_medium.render("DIFFICULTY SETTINGS", True, WHITE)
    screen.blit(difficulty_label, (WIDTH//2 - difficulty_label.get_width()//2, 120))
    #displays the diffeent dificulties
    difficulties = [
        (1, "EASY", WHITE),
        (2, "NORMAL", LIGHT_GREEN),
        (3, "MEDIUM", ORANGE),
        (4, "HARD", RED),
        (5, "EXTREME", (255, 0, 0))
    ]
    #shows current difficulty
    current_diff_text = font_small.render(f"Current: {difficulty}", True, ORANGE)
    screen.blit(current_diff_text, (WIDTH//2 - current_diff_text.get_width()//2, 190))
    
    y_pos = 260
    for num, name, color in difficulties:
        marker = "<<" if num == difficulty else "  "
        text = font_tiny.render(f"{marker} {num}. {name} {marker}", True, color)
        screen.blit(text, (WIDTH//2 - text.get_width()//2, y_pos))
        y_pos += 40
    #shows player what to press
    hint = font_tiny.render("Press 1-5 to change difficulty", True, GRAY)
    screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 80))
    #tells player how to navigate screens
    back_text = font_tiny.render("Press M to return to menu", True, GRAY)
    screen.blit(back_text, (WIDTH//2 - back_text.get_width()//2, HEIGHT - 50))

def draw_game():
    def world_to_screen(wx, wy):
        return wx - g["x"] + WIDTH//2, wy - g["y"] + HEIGHT//2

    if selected_level == "grass":
        # Tile the grass image background and move with the player
        tile_w, tile_h = grass_bg.get_size()
        offset_x = int(g["x"]) % tile_w
        offset_y = int(g["y"]) % tile_h
        for ix in range(-1, WIDTH // tile_w + 2):
            for iy in range(-1, HEIGHT // tile_h + 2):
                screen.blit(grass_bg, (ix * tile_w - offset_x, iy * tile_h - offset_y))

        # No road on grass level: grass-only background
    else:
        # Highway: solid grass sides, road is part of the world and scrolls
        screen.fill(GREEN)
        road_width = 400
        road_x_world = -road_width // 2
        # draw repeated roads so you can drive onto another road as you move horizontally
        repeat_count = 3
        for i in range(-repeat_count, repeat_count + 1):
            segment_x_world = road_x_world + i * (road_width + 200)
            road_x_screen, _ = world_to_screen(segment_x_world, 0)
            pygame.draw.rect(screen, DARK_GRAY, (road_x_screen, 0, road_width, HEIGHT))
            # Lane markings
            lane_count = 3
            lane_width = road_width // lane_count
            for j in range(1, lane_count):
                lane_x_world = segment_x_world + j * lane_width
                lane_x_screen, _ = world_to_screen(lane_x_world, 0)
                for y in range(0, HEIGHT, 40):
                    pygame.draw.rect(screen, WHITE, (lane_x_screen - 2, y + (g["y"] % 40), 4, 20))
            # Road edges
            pygame.draw.rect(screen, ORANGE, (road_x_screen, 0, 6, HEIGHT))
            pygame.draw.rect(screen, ORANGE, (road_x_screen + road_width - 6, 0, 6, HEIGHT))
    
    # Draw Police cars
    for p in g["police"]:
        img = pygame.transform.rotate(police_img, -p["angle"])
        screen.blit(img, img.get_rect(center=(p["x"] - g["x"] + WIDTH//2, p["y"] - g["y"] + HEIGHT//2)))

    # Draw arrows for off-screen police that face them
    for p in g["police"]:
        px = p["x"] - g["x"] + WIDTH//2
        py = p["y"] - g["y"] + HEIGHT//2
        if px < 0 or px > WIDTH or py < 0 or py > HEIGHT:
            # Clamp arrow position to screen edge
            arrow_x = min(max(px, 20), WIDTH - 20)
            arrow_y = min(max(py, 20), HEIGHT - 20)
            # Calculate angle from player to police
            dx = px - WIDTH//2
            dy = py - HEIGHT//2
            angle = math.atan2(dy, dx)
            # Draw arrow
            length = 30
            tip_x = arrow_x + math.cos(angle) * length
            tip_y = arrow_y + math.sin(angle) * length
            pygame.draw.line(screen, RED, (arrow_x, arrow_y), (tip_x, tip_y), 4)
            # Draw arrowhead
            left = angle + math.pi * 0.75
            right = angle - math.pi * 0.75
            pygame.draw.line(screen, RED, (tip_x, tip_y), (tip_x + math.cos(left) * 12, tip_y + math.sin(left) * 12), 3)
            pygame.draw.line(screen, RED, (tip_x, tip_y), (tip_x + math.cos(right) * 12, tip_y + math.sin(right) * 12), 3)

    # Draw Players car
    p_img = pygame.transform.rotate(car_img, -g["angle"])
    screen.blit(p_img, p_img.get_rect(center=(WIDTH//2, HEIGHT//2)))

    # Draw Username above player car (pure white)
    username_text = font_small.render(username, True, WHITE)
    screen.blit(username_text, (WIDTH//2 - username_text.get_width()//2, HEIGHT//2 - 80))

    # Draw Explosions when police cars colide
    for exp in g["explosions"][:]:
        exp["t"] -= 1
        if exp["t"] <= 0:
            g["explosions"].remove(exp)
        else:
            size = int(30 * (1 - exp["t"] / 20))
            pygame.draw.circle(screen, ORANGE, (int(exp["x"] - g["x"] + WIDTH//2), 
                                               int(exp["y"] - g["y"] + HEIGHT//2)), size)

    # Draw UI elements: Time, Score, Difficulty
    elapsed = (pygame.time.get_ticks() - g["start_time"]) // 1000
    time_text = font_small.render(f"TIME: {elapsed}s", True, WHITE)
    screen.blit(time_text, (20, 20))
    #displays score
    score_surf = font_small.render(f"SCORE: {g['score']}", True, WHITE)
    screen.blit(score_surf, (20, 70))
    #displays difficulty
    difficulty_text = font_tiny.render(f"DIFFICULTY: {difficulty}", True, ORANGE)
    screen.blit(difficulty_text, (20, 120))
#when dead, show busted
def draw_game_over():
    screen.fill(DARK_GRAY)
    over_text = font_large.render("BUSTED!", True, RED)
    screen.blit(over_text, (WIDTH//2 - over_text.get_width()//2, 80))
    #stops timer when dead
    elapsed = (g["end_time"] - g["start_time"]) // 1000
    time_text = font_medium.render(f"Time: {elapsed}s", True, WHITE)
    screen.blit(time_text, (WIDTH//2 - time_text.get_width()//2, 200))
    #displays final score
    score_text = font_medium.render(f"Score: {g['score']}", True, WHITE)
    screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 280))
    #shows difficulty of the game that just ended
    diff_text = font_small.render(f"Difficulty: {difficulty}", True, ORANGE)
    screen.blit(diff_text, (WIDTH//2 - diff_text.get_width()//2, 350))
    #tells player how to play again
    replay_text = font_small.render("Press R to Replay or M for Menu", True, ORANGE)
    screen.blit(replay_text, (WIDTH//2 - replay_text.get_width()//2, HEIGHT - 80))

# --- MAIN LOOP ---
while running:
    clock.tick(60)
    now = pygame.time.get_ticks()
    
    # INPUT
    for event in pygame.event.get():
        if event.type == pygame.QUIT: 
            running = False
        #login state
        if current_state == GameState.LOGIN:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and len(input_box.text) > 0:
                    username = input_box.text
                    update_current_highscore()
                    current_state = GameState.MAIN_MENU
                else:
                    input_box.handle_event(event)
        #if enter is pressed when box is empty do nothing
        elif current_state == GameState.MAIN_MENU:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    current_state = GameState.LEVEL_SELECT
                elif event.key == pygame.K_2:
                    current_state = GameState.OPTIONS
                elif event.key == pygame.K_3:
                    running = False
        #level select
        elif current_state == GameState.LEVEL_SELECT:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    selected_level = "grass"
                    update_current_highscore()
                    g = reset()
                    current_state = GameState.PLAYING
                elif event.key == pygame.K_2:
                    selected_level = "highway"
                    update_current_highscore()
                    g = reset()
                    current_state = GameState.PLAYING
                elif event.key == pygame.K_m:
                    current_state = GameState.MAIN_MENU
        #game options button
        elif current_state == GameState.OPTIONS:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]:
                    difficulty = int(event.unicode)
                elif event.key == pygame.K_m:
                    current_state = GameState.MAIN_MENU
        #the state of the game when the player is playing, if escape is pressed, go back to main menu
        elif current_state == GameState.PLAYING:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                current_state = GameState.MAIN_MENU
        #showing the game over
        elif current_state == GameState.GAME_OVER:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    g = reset()
                    current_state = GameState.PLAYING
                elif event.key == pygame.K_m:
                    current_state = GameState.MAIN_MENU

    # GAME LOGIC
    if current_state == GameState.PLAYING and not g["dead"]:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]: g["angle"] -= 4 * turn_speed_multiplier[difficulty]
        if keys[pygame.K_RIGHT]: g["angle"] += 4 * turn_speed_multiplier[difficulty]
        
        # Move Forward with difficulty multipliers speed change
        speed = 5 * difficulty_multiplier[difficulty]
        g["x"] += math.cos(math.radians(g["angle"])) * speed
        g["y"] += math.sin(math.radians(g["angle"])) * speed

        # Time Bonus (points every 5 seconds) 
        if now - g["time_bonus_timer"] > 5000:
            g["score"] += 1
            g["time_bonus_timer"] = now

        # Spawn Police every 3 seconds (adjusted by difficulty)
        spawn_rate = 3000 / difficulty_multiplier[difficulty]
        if now - g["spawn_timer"] > spawn_rate:
            side_angle = random.uniform(0, 360)
            spawn_x = g["x"] + math.cos(math.radians(side_angle)) * 500
            spawn_y = g["y"] + math.sin(math.radians(side_angle)) * 500
            g["police"].append({"x": spawn_x, "y": spawn_y, "angle": 0})
            g["spawn_timer"] = now

        # Police AI & Collision/ driving
        for p in g["police"][:]:
            dx, dy = g["x"] - p["x"], g["y"] - p["y"]
            target = math.degrees(math.atan2(dy, dx))
            p["angle"] += ((target - p["angle"] + 180) % 360 - 180) * 0.04
            police_speed = 5.5 * difficulty_multiplier[difficulty]
            p["x"] += math.cos(math.radians(p["angle"])) * police_speed
            p["y"] += math.sin(math.radians(p["angle"])) * police_speed
            
            # if police Hit Player
            if math.hypot(g["x"] - p["x"], g["y"] - p["y"]) < 35:
                g["dead"] = True
                g["end_time"] = pygame.time.get_ticks()
                current_state = GameState.GAME_OVER
                # Update high score for this username and current map
                if username:
                    scores = get_user_scores(username)
                    prev = scores.get(selected_level, 0)
                    if g["score"] > prev:
                        scores[selected_level] = g["score"]
                        current_highscore = g["score"]
                        save_highscores(highscores)

        # Police hitting each other: remove any cluster of 2+ cars
        threshold = 30
        n = len(g["police"])
        adj = [[] for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                p1 = g["police"][i]
                p2 = g["police"][j]
                if math.hypot(p1["x"] - p2["x"], p1["y"] - p2["y"]) < threshold:
                    adj[i].append(j)
                    adj[j].append(i)

        visited = [False] * n
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
                # explode all cars in group if crashed in a pile
                for idx in group:
                    if idx not in to_remove and idx < len(g["police"]):
                        p = g["police"][idx]
                        g["explosions"].append({"x": p["x"], "y": p["y"], "t": 20})
                        to_remove.add(idx)
                g["score"] += len(group)

        # Remove police in reverse order to avoid index issues
        for idx in sorted(to_remove, reverse=True):
            if idx < len(g["police"]):
                g["police"].pop(idx)

    # --- DRAWING the buttons
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