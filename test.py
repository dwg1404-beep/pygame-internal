import pygame
import sys

print("1. Initializing...")
pygame.init()

print("2. Attempting to open window...")
# We use a tiny window and NO special flags to start
screen = pygame.display.set_mode((400, 300))

print("3. SUCCESS! Window is open.")
print("Close the window to exit.")

running = True
while running:
    screen.fill((255, 0, 0)) # Bright Red
    pygame.display.flip()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

pygame.quit()
print("4. Closed safely.")