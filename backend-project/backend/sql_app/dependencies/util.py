import base64, cv2, PIL, io, re
import numpy as np
import logging, time, os, tracemalloc

def encode_image(image_file):
  return base64.b64encode(image_file.read()).decode('utf-8')

def decode_image(image_str: str):
    b = str.encode(image_str)
    imgdata = base64.b64decode(b)
    return imgdata

def base64_to_cv(img_str):
    if "base64," in img_str:
        # DARA URI の場合、data:[<mediatype>][;base64], を除く
        img_str = img_str.split(",")[1]
    img_raw = np.frombuffer(base64.b64decode(img_str), np.uint8)
    img = cv2.imdecode(img_raw, cv2.IMREAD_UNCHANGED)

    return img




logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

class computing_time_tracker:
    def __init__(self, message=None):
        self.filehandler = logging.FileHandler("logs/computing_time.log", mode="a", encoding=None, delay=False)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.filehandler)
        self.filehandler.setFormatter(formatter)
        self.message = message
        self.start_time = time.time()

    def stop_timer(self):
        duration = time.time() - self.start_time
        if self.message:
            message = f"{self.message} - Duration: {duration} - Start time: {self.start_time}"
        else:
            message = f"Duration: {duration} - Start time: {self.start_time}"
        self.logger.info(message)

class memory_tracker:
    def __init__(self, message=None):
        self.filehandler = logging.FileHandler("logs/memory_tracker.log", mode="a", encoding=None, delay=False)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.WARNING)
        self.logger.addHandler(self.filehandler)
        self.filehandler.setFormatter(formatter)
        self.logger.warning(f"{message} - Memory tracker started")
        tracemalloc.start()
        self.snapshot1 = tracemalloc.take_snapshot()

    def get_top_stats(self, message=None):
        snapshot2 = tracemalloc.take_snapshot()
        top_stats = snapshot2.compare_to(self.snapshot1, 'lineno')
        if message:
            self.logger.warning(message)
        self.logger.warning("[ Top 10 ]")
        for stat in top_stats[:10]:
            self.logger.warning(stat)
        return top_stats

log_filename = "logs/backend.log"

os.makedirs(os.path.dirname(log_filename), exist_ok=True)
file_handler = logging.FileHandler(log_filename, mode="a", encoding=None, delay=False)
file_handler.setFormatter(formatter)

logger1 = logging.getLogger(
    "info_logger"
)
logger1.setLevel(logging.INFO)
logger1.addHandler(file_handler)

def remove_special_chars(text):
    cleaned_text = re.sub(r'[^\w\s]', '', text)
    return cleaned_text