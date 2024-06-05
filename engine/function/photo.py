import cv2
from urllib.request import urlopen,urlretrieve
from tkinter import Tk     # from tkinter import Tk for Python 3.x
from tkinter.filedialog import askopenfilename
import shutil
import os
from ..game.round import Round

def takePicture(origin_dir:str,round:Round)->str:
    cam = cv2.VideoCapture(0)
    
    cv2.namedWindow("Take a funny picture!")
    while True:
        ret, frame = cam.read()
        if not ret:
            print("failed to grab frame")
            break
        cv2.imshow("Take a funny picture!", frame)

        k = cv2.waitKey(1)
        if k%256 == 32:
            # SPACE pressed
            img_name = os.path.join(origin_dir,f"{round.id}_0.png")
            cv2.imwrite(img_name, frame)
            print("{} written!".format(img_name))
            break
    cam.release()
    cv2.destroyAllWindows()
    return img_name

def choosePicture(origin_dir:str,round:Round)->str:
    Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
    filename = askopenfilename() # show an "Open" dialog box and return the path to the selected file
    newpath=storeImage(filename, origin_dir, f"{round.id}_0.png")
    return newpath

def storeImage(fm_location, to_location,new_filename):
    new_file_path = os.path.join(to_location, new_filename)
    # Copy the image to the new location
    shutil.copy2(fm_location, new_file_path)
    return new_file_path

def saveImage(im_url,im_name):
    urlretrieve(im_url, im_name)
    img=urlopen(im_url).read()
    return img