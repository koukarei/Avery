import sys, time
import pygame
import VideoCapture

WAIT_TIME = 5
FONT_SIZE = 64
SMALL_FONT_SIZE = 20

def buffer2surface(buffer, width, height):
  bgr = pygame.image.fromstring(buffer, (width, height), 'RGB', True)
  r, g, b, a = bgr.get_shifts()
  rm, gm, bm, am = bgr.get_masks()
  bgr.set_shifts((b, g, r, a))
  bgr.set_masks((bm, gm, rm, am))
  return bgr

class Camera:
  PREVIEW_WIDTH = 800
  PREVIEW_HEIGHT = 600

  def __init__(self):
    self.preview_size = Camera.PREVIEW_WIDTH, Camera.PREVIEW_HEIGHT

    pygame.fastevent.init()
    pygame.font.init()

    self.ORIGIN = (0, 0)

    self.update_time = time.time()
    self.fps = 0.0

    self.camera = VideoCapture.Device()
    #self.camera.displayCaptureFilterProperties()
    self.camera.displayCapturePinProperties()

    fontname = pygame.font.get_default_font()
    self.font = pygame.font.Font(fontname, FONT_SIZE)
    self.smallfont = pygame.font.Font(fontname, SMALL_FONT_SIZE)
    buffer, width, height = self.camera.getBuffer()

    self.screen = pygame.display.set_mode((width, height), pygame.HWSURFACE|pygame.DOUBLEBUF)

  def retrieve(self):
    buffer, width, height = self.camera.getBuffer()
    if buffer:
      return buffer2surface(buffer, width, height)

  def event(self):
    return pygame.fastevent.poll()

  def update(self, str=None):
    if hasattr(self, "screen"):
      surface = self.retrieve()
      
      self.screen.blit(surface, self.ORIGIN)
      if str:
        self.write(str, True)
      pygame.display.flip()

      now = time.time()
      self.fps = 1 / (now - self.update_time)
      self.update_time = now

  def shutter(self, path):
    start = time.time()
    while True:
      pygame.event.clear()
      t = time.time()
      diff = t - start
      if diff > WAIT_TIME:
        break
      self.update(str(int(0.99 + WAIT_TIME - diff)))

    self.update()
    self.camera.saveSnapshot(path)
    print("saved: %s" % path)

  def fill(self, color = (0, 0, 0)):
    if hasattr(self, "screen"):
      self.screen.fill(color)

  def write(self, str, big=False):
    if hasattr(self, "screen"):
      if big:
        text = self.font.render(str, False, (255, 255, 255))
      else:
        text = self.smallfont.render(str, False, (255, 255, 255))
      x = (Camera.PREVIEW_WIDTH - text.get_width()) / 2
      y = (Camera.PREVIEW_HEIGHT - text.get_height()) / 2
      self.screen.blit(text, (x, y))
      pygame.display.flip()

if __name__ == "__main__":
  camera = Camera()
  while True:
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        sys.exit()
      elif event.type == pygame.KEYDOWN:
        if (event.key == pygame.K_p):
          camera.shutter("photo.jpg")
        elif (event.key == pygame.K_q):
          sys.exit()
    camera.update()
    print("fps: %.2f" % camera.fps)

# vim: sw=2 ts=2 et: