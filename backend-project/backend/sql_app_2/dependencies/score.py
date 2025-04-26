import cv2
from util import base64_to_cv
from skimage.metrics import structural_similarity as ssim

def image_similarity(image1, image2):
    # Read images using OpenCV
    img1 = base64_to_cv(image1)
    img2 = base64_to_cv(image2)

    # Check if images were read successfully
    if img1 is None or img2 is None:
        raise ValueError("Could not read one or both images")

    # Get image dimensions
    height = min(img1.shape[0], img2.shape[0])
    width = min(img1.shape[1], img2.shape[1])

    # Resize images
    img1 = cv2.resize(img1, (width, height))
    img2 = cv2.resize(img2, (width, height))

    # Convert to grayscale
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # Calculate histograms
    hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
    hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])

    # Normalize histograms
    cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
    cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)

    # Compare histograms
    similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

    # Calculate SSIM
    ssim_score = ssim(gray1, gray2)

    return {
        "hist_similarity": similarity,
        "ssim_score": ssim_score
    }

def rank(total_score):
    max_score = 100
    if total_score>(max_score*0.9):
        return "A"
    elif total_score>(max_score*0.8):
        return "B"
    elif total_score>(max_score*0.7):
        return "C"
    elif total_score>(max_score*0.5):
        return "D"
    elif total_score>(max_score*0.4):
        return "E"
    else:
        return "F"



