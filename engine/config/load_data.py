import os
import pygame
from engine.config.initialize import TEXT_COLOR

class Ui_imgs:
    album = pygame.Surface
    button = pygame.Surface
    camera = pygame.Surface
    idle_button = pygame.Surface
    input_ui = pygame.Surface
    next = pygame.Surface
    prev = pygame.Surface
    share = pygame.Surface
    magnifying_glass = pygame.Surface

class Dirs:
    data = str
    ui = str
    origin = str
    ai = str
    learner = str

import cv2
import numpy as np

def extract_black(image_path):
    image = cv2.imread(image_path)
    lower_bound = np.array([0, 0, 0])  # Lower bound of the color range
    upper_bound = np.array([51, 51, 51])  # Upper bound of the color range

    # Create a mask using inRange function
    mask = cv2.inRange(image, lower_bound, upper_bound)

    # Invert the mask (optional)
    mask = cv2.bitwise_not(mask)

    # Apply the mask to the original image
    masked_image = cv2.bitwise_and(image, image, mask=mask)

    from_color = [52,52,52]  # Define the color you want to change

    # Define the color range for the color you want to change
    lower_bound = np.array(from_color, dtype=np.uint8)
    upper_bound = np.array(from_color, dtype=np.uint8)

    # Create a mask for the color you want to change
    mask = cv2.inRange(masked_image, lower_bound, upper_bound)

    # Change the color of the masked area
    masked_image[mask != 0] = TEXT_COLOR

    return masked_image

def load_data(main_dir:str):
    data_dir = os.path.join(main_dir, "data")
    ui_dir = os.path.join(data_dir, "ui")
    origin_dir = os.path.join(data_dir, "original")
    ai_dir = os.path.join(data_dir, "ai_gen")
    learner_dir = os.path.join(data_dir, "learner_gen")

    album_img=pygame.image.load(os.path.join(ui_dir, "album.png")).convert()
    album_img.set_colorkey((0,0,0))
    button_img=pygame.image.load(os.path.join(ui_dir, "button.png")).convert()
    button_img.set_colorkey((0,0,0))
    camera_img=pygame.image.load(os.path.join(ui_dir, "camera.png")).convert()
    camera_img.set_colorkey((0,0,0))
    idle_button_img=pygame.image.load(os.path.join(ui_dir, "idle_button.png")).convert()
    idle_button_img.set_colorkey((0,0,0))
    input_ui_img=pygame.image.load(os.path.join(ui_dir, "input_ui.png")).convert()
    input_ui_img.set_colorkey((0,0,0))
    next_img=pygame.image.load(os.path.join(ui_dir, "next.png")).convert()
    next_img.set_colorkey((0,0,0))
    prev_img=pygame.transform.flip(next_img, True, False)
    share_img=pygame.image.load(os.path.join(ui_dir, "share.png")).convert()
    share_img.set_colorkey((0,0,0))
    magnifying_glass_img=pygame.image.load(os.path.join(ui_dir, "magnifying_glass.svg")).convert()

    #player_img = pygame.image.load(os.path.join("img", "player.png")).convert()
    #player_mini_img = pygame.transform.scale(player_img, (25, 19))
    #player_mini_img.set_colorkey(BLACK)
    #pygame.display.set_icon(player_mini_img)

    ui_imgs=Ui_imgs()
    ui_imgs.album = album_img
    ui_imgs.button = button_img
    ui_imgs.camera = camera_img
    ui_imgs.idle_button = idle_button_img
    ui_imgs.input_ui = input_ui_img
    ui_imgs.next = next_img
    ui_imgs.prev = prev_img
    ui_imgs.share = share_img
    ui_imgs.magnifying_glass = magnifying_glass_img

    dirs=Dirs()
    dirs.data = data_dir
    dirs.ui = ui_dir
    dirs.origin = origin_dir
    dirs.ai = ai_dir
    dirs.learner = learner_dir

    font_name = os.path.join(data_dir,"font","Arial.ttf")
    return ui_imgs,dirs,font_name