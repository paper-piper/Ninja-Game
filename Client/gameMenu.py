import pygame
import sys

MAIN_MENU_IMAGE_PATH = r'../Assets/Map/detailedMap.png'

# Music paths
MAIN_MENU_MUSIC_PATH = r'../Assets/Music/1 - Adventure Begin.ogg'

# Font paths
NORMAL_FONT_PATH = r'../Assets/font/NormalFont.ttf'
FONT = pygame.font.Font(NORMAL_FONT_PATH, 36)  # Set the font for the menu text

screen_width = 800
screen_height = 600


class Menu:
    def __init__(self):
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        self.font = FONT
        self.title_font = pygame.font.Font(NORMAL_FONT_PATH, 48)  # Larger font for the title
        self.bg_image = pygame.image.load(MAIN_MENU_IMAGE_PATH)
        pygame.mixer.music.load(MAIN_MENU_MUSIC_PATH)
        pygame.mixer.music.play(-1)  # Play music indefinitely
        self.settings = {'sound': 'on', 'difficulty': 'easy'}
        self.current_menu = 'Main Menu'
        self.title = "Ninja Game"  # Default title for the main menu
        self.title_surface = self.font.render(self.title, True, (255, 255, 255))
        self.title_rect = self.title_surface.get_rect(center=(self.screen.get_width() // 2, 30))
        self.items = self.get_items(self.current_menu)
        self.texts = []
        self.rects = []
        self.update_menu_items()

    def run(self):
        running = True
        while running:
            self.screen.blit(self.bg_image, (0, 0))
            self.screen.blit(self.title_surface, self.title_rect)

            mouse_pos = pygame.mouse.get_pos()

            # Iterate over menu items and create text surfaces on the fly
            for index, item in enumerate(self.items):
                if self.rects[index].collidepoint(mouse_pos):
                    # Render highlighted text
                    text_surface = self.font.render(item, True, (255, 0, 0))
                else:
                    # Render normal text
                    text_surface = self.font.render(item, True, (255, 255, 255))
                self.screen.blit(text_surface, self.rects[index])

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse click
                        for i, rect in enumerate(self.rects):
                            if rect.collidepoint(event.pos):
                                running = self.handle_selection(i)
        pygame.mixer.music.stop()
        return self.settings

    def get_items(self, menu_type):
        if menu_type == 'Main Menu':
            return ['Start Game', 'Settings', 'Exit']
        elif menu_type == 'Settings':
            return [
                f"Sound: {'ON' if self.settings['sound'] == 'on' else 'OFF'}",
                f"Difficulty: {self.settings['difficulty']}",
                'Back to Main Menu'
            ]

    def update_menu_items(self):
        # Set the title based on the current menu context
        self.title = "Ninja Game" if self.current_menu == "Main Menu" else "Settings"
        self.title_surface = self.title_font.render(self.title, True, (255, 255, 255))
        self.title_rect = self.title_surface.get_rect(center=(self.screen.get_width() // 2, 30))

        # Refresh items based on the current menu
        self.items = self.get_items(self.current_menu)
        self.texts = []
        self.rects = []
        for item in self.items:
            text_surface = self.font.render(item, True, (255, 255, 255))
            self.texts.append(text_surface)
            # 300 is the going down factor
            text_rect = text_surface.get_rect(center=(self.screen.get_width() // 2, 300 + 50 * self.items.index(item)))
            self.rects.append(text_rect)

    def handle_selection(self, index):
        if self.current_menu == 'Main Menu':
            selection = self.items[index]
            if selection == 'Start Game':
                return False  # Exit menu when starting the game
            elif selection == 'Settings':
                self.current_menu = 'Settings'  # Switch to settings menu
                self.update_menu_items()
            elif selection == 'Exit':
                pygame.quit()
                sys.exit()
        elif self.current_menu == 'Settings':
            selection = self.items[index]
            if selection == 'Back to Main Menu':
                self.current_menu = 'Main Menu'  # Switch back to main menu
                self.update_menu_items()
            else:
                if ':' in selection:
                    key, _ = selection.split(': ')
                    if key == 'Sound':
                        self.settings['sound'] = 'off' if self.settings['sound'] == 'on' else 'on'
                    elif key == 'Difficulty':
                        self.settings['difficulty'] = 'hard' if self.settings['difficulty'] == 'easy' else 'easy'
                    self.update_menu_items()  # Reflect changes in the menu items
        return True  # Continue showing the menu
