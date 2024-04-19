import pygame
import sys
import os
import random
import threading

pygame.init()
pygame.mixer.init()
MAIN_MENU_IMAGE_PATH = r'../Assets/Map/detailedMap.png'

# Music paths
music_path = "../Assets/Music/Menu"
stop_music = False

# Sound effects
accept_sound_path = '../Assets/SoundEffects/Menu/Accept.wav'
accept2_sound_path = '../Assets/SoundEffects/Menu/Accept2.wav'
cancel_sound_path = '../Assets/SoundEffects/Menu/Cancel.wav'
accept_sound = pygame.mixer.Sound(accept_sound_path)
accept2_sound = pygame.mixer.Sound(accept2_sound_path)
cancel_sound = pygame.mixer.Sound(cancel_sound_path)

# Font paths
NORMAL_FONT_PATH = r'../Assets/font/NormalFont.ttf'
FONT = pygame.font.Font(NORMAL_FONT_PATH, 36)  # Set the font for the menu text

screen_width = 800
screen_height = 600


class Menu:
    def __init__(self):
        """
        Initialize the main menu with screen settings, fonts, background image, and music settings.
        :return: None
        """
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        self.font = FONT
        self.title_font = pygame.font.Font(NORMAL_FONT_PATH, 48)  # Larger font for the title
        self.bg_image = pygame.image.load(MAIN_MENU_IMAGE_PATH)
        thread = threading.Thread(target=play_random_music)
        thread.start()
        # pygame.mixer.music.play(-1)  # Play music indefinitely
        self.settings = {'sound': 'on', 'difficulty': 'easy'}
        self.character = "Shadow"  # defualt character
        self.current_menu = 'Main Menu'
        self.title = "Ninja Game"  # Default title for the main menu
        self.title_surface = self.font.render(self.title, True, (255, 255, 255))
        self.title_rect = self.title_surface.get_rect(center=(self.screen.get_width() // 2, 30))
        self.items = self.get_items(self.current_menu)
        self.texts = []
        self.rects = []
        self.update_menu_items()

    def run(self):
        """
        Run the main loop of the menu, handling user interactions and updating the display.
        :return: Tuple containing the final settings and the selected character when the menu closes
        """
        global stop_music
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
        # pygame.mixer.music.stop()
        stop_music = True
        return self.settings, self.character

    def get_items(self, menu_type):
        """
        Retrieve a list of menu items based on the current menu context.
        :param menu_type: The current type of menu to generate items for (e.g., 'Main Menu', 'Settings')
        :return: List of strings representing menu items
        """
        if menu_type == 'Main Menu':
            return ['Start Game', 'Settings', 'Exit']
        elif menu_type == 'Settings':
            return [
                f"Sound: {'ON' if self.settings['sound'] == 'on' else 'OFF'}",
                f"Difficulty: {self.settings['difficulty']}",
                'Back to Main Menu'
            ]

    def update_menu_items(self):
        """
        Update menu items and their corresponding rendering properties based on the current menu context.
        :return: None
        """
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
        """
        Handle user selections in the menu based on the item selected.
        :param index: The index of the selected item in the menu list
        :return: Boolean indicating if the menu should continue running (True to continue, False to close)
        """
        if self.current_menu == 'Main Menu':
            selection = self.items[index]
            if selection == 'Start Game':
                # create character select and then return
                accept2_sound.play()
                character_select = CharacterSelectMenu(self.screen)
                self.character = character_select.run()
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
                        if self.settings['sound'] == 'off':
                            pygame.mixer.music.set_volume(1)
                            self.settings['sound'] = 'on'
                        else:
                            pygame.mixer.music.set_volume(0)
                            self.settings['sound'] = 'off'
                    elif key == 'Difficulty':
                        self.settings['difficulty'] = 'hard' if self.settings['difficulty'] == 'easy' else 'easy'
                    self.update_menu_items()  # Reflect changes in the menu items
        return True  # Continue showing the menu


class CharacterSelectMenu:
    def __init__(self, screen):
        """
        Initialize the character selection menu with screen, fonts, background, and character grid settings.
        :param screen: The Pygame display surface to draw the menu on
        :return: None
        """
        self.screen = screen
        self.font = pygame.font.Font(NORMAL_FONT_PATH, 24)  # Smaller font for character names
        self.title_font = pygame.font.Font(NORMAL_FONT_PATH, 48)
        self.bg_image = pygame.image.load(MAIN_MENU_IMAGE_PATH)
        self.title = "Select Character"
        self.title_surface = self.title_font.render(self.title, True, (255, 255, 255))
        self.title_rect = self.title_surface.get_rect(center=(screen_width // 2, 30))

        # Setup character grid
        self.characters = self.get_characters()  # This function needs to be defined to load character info
        self.card_size = (130, 170)  # width, height
        self.grid_origin = (50, 100)  # x, y starting point of the grid
        self.grid_spacing = (10, 10)  # horizontal, vertical spacing
        self.card_background_color = (100, 100, 100)
        self.card_hover_color = (255, 0, 0)
        self.cards = []
        self.setup_cards()

    def setup_cards(self):
        """
        Set up the character cards on the menu grid, including positions and dimensions.
        :return: None
        """
        for i in range(10):  # Assuming 10 characters, arranged in 5x2 grid
            row = i % 2
            col = i // 2
            x = self.grid_origin[0] + col * (self.card_size[0] + self.grid_spacing[0])
            y = self.grid_origin[1] + row * (self.card_size[1] + self.grid_spacing[1])
            card_rect = pygame.Rect(x, y, *self.card_size)
            self.cards.append((self.characters[i], card_rect))

    def get_characters(self):
        """
        Load character information from the assets directory, including names and images.
        :return: List of dictionaries, each containing a character's name, image path, and scaled image
        """
        characters_path = '../Assets/Characters'
        characters = []
        # List directories in the characters path
        for character_name in os.listdir(characters_path):
            character_folder = os.path.join(characters_path, character_name)
            if os.path.isdir(character_folder):
                image_path = os.path.join(character_folder, 'Faceset.png')
                # Check if the image file exists
                if os.path.isfile(image_path):
                    characters.append({
                        'name': character_name,
                        'image_path': image_path,
                        'scaled_image': self.scale_image(image_path, 3)
                    })
        return characters

    def scale_image(self, image_path, scale_factor):
        """
        Scale an image from a given path by a specified factor.
        :param image_path: Path to the image file
        :param scale_factor: The factor by which to scale the image
        :return: A Pygame surface object of the scaled image
        """
        # Load the image
        image = pygame.image.load(image_path)
        # Scale the image by the given factor
        original_size = image.get_rect().size
        scaled_size = (original_size[0] * scale_factor, original_size[1] * scale_factor)
        scaled_image = pygame.transform.scale(image, scaled_size)
        return scaled_image

    def run(self):
        """
        Run the main loop of the character selection menu, handling user interactions and updating the display.
        :return: The name of the selected character, or None if no selection is made
        """
        running = True
        while running:
            self.screen.blit(self.bg_image, (0, 0))
            self.screen.blit(self.title_surface, self.title_rect)
            mouse_pos = pygame.mouse.get_pos()

            for character, card_rect in self.cards:
                if card_rect.collidepoint(mouse_pos):
                    color = self.card_hover_color
                else:
                    color = self.card_background_color
                pygame.draw.rect(self.screen, color, card_rect)

                # Use the pre-scaled image
                character_image = character['scaled_image']
                image_rect = character_image.get_rect(
                    center=(card_rect.centerx, card_rect.top + character_image.get_height() // 2 + 10))
                self.screen.blit(character_image, image_rect)
                # Render character name
                text_surface = self.font.render(character['name'], True, (255, 255, 255))
                text_rect = text_surface.get_rect(center=(card_rect.centerx, card_rect.bottom - 20))
                self.screen.blit(text_surface, text_rect)

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse click
                        for character, card_rect in self.cards:
                            if card_rect.collidepoint(event.pos):
                                accept_sound.play()
                                return character['name']  # Return selected character name and exit

        return None


def play_random_music():
    """
    Continuously play random music tracks from a specified directory, handling track selection and looping.
    :return: None
    """
    # Fetch all .wav files from the specified directory
    music_files = [file for file in os.listdir(music_path) if file.endswith('.ogg')]
    if not music_files:
        print("No music files found in the directory.")
        return

    # Function to play a selected music file
    def play_music():
        # Randomly select a music file
        selected_file = random.choice(music_files)
        full_path = os.path.join(music_path, selected_file)

        # Load and play the selected music file
        pygame.mixer.music.load(full_path)
        pygame.mixer.music.play()
        print(f"Now playing: {selected_file}")

    # Play the first song
    play_music()

    # Continue playing music
    while not stop_music:
        # Check if music is still playing
        if not pygame.mixer.music.get_busy():
            # If the song has ended, play the next song
            play_music()
        pygame.time.wait(1000)  # Check every second
    pygame.mixer.music.stop()


if __name__ == "__main__":
    pygame.init()
    menu = Menu()
    settings, character_name = menu.run()
    print(character_name)
    print(settings)  # Print settings to verify
