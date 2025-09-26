import base64, cv2, PIL, io, re, csv, os
import numpy as np
import logging, time, os, tracemalloc, datetime

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
    def __init__(self, message=None, id=None):
        self.starttime = time.time()
        self.start_date = datetime.datetime.now()
        self.message = message
        self.id = id
        tracemalloc.start()
        self.snapshot1 = tracemalloc.take_snapshot()

    def get_top_stats(self):
        snapshot2 = tracemalloc.take_snapshot()
        duration = time.time() - self.starttime
        stop_time = datetime.datetime.now()
        
        top_stats = snapshot2.compare_to(self.snapshot1, 'lineno')
        #top_stats = snapshot2.statistics('lineno')
        tracemalloc.clear_traces()
        
        if not os.path.exists('logs/memory_tracker.csv'):
            with open('logs/memory_tracker.csv','w') as f:
                writer = csv.writer(f)
                writer.writerow(["message", "id", "startdate", "stopdate", "duration", "traceback", "size", "count"])

        with open('logs/memory_tracker.csv','a') as f:
            writer = csv.writer(f)
            for stat in top_stats[:10]:
                writer.writerow(
                    [self.message, self.id, self.start_date, stop_time, duration, stat.traceback, stat.size, stat.count]
                )
        return

log_filename = "logs/backend.log"

os.makedirs(os.path.dirname(log_filename), exist_ok=True)
file_handler = logging.FileHandler(log_filename, mode="a", encoding=None, delay=False)
file_handler.setFormatter(formatter)

logger1 = logging.getLogger(
    "info_logger"
)
logger1.setLevel(logging.INFO)
logger1.addHandler(file_handler)

logger_image = logging.getLogger(
    "image_logger"
)

image_handler = logging.FileHandler("logs/image_generation.log", mode="a", encoding=None, delay=False)
image_handler.setFormatter(formatter)
logger_image.setLevel(logging.INFO)
logger_image.addHandler(image_handler)

def remove_special_chars(text):
    cleaned_text = re.sub(r'[^\w\s]', '', text)
    return cleaned_text