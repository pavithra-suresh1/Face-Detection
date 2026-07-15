import cv2
import os

print("OpenCV Version:", cv2.__version__)
print("cv2.data.haarcascades:", cv2.data.haarcascades)

print("Directory exists:", os.path.exists(cv2.data.haarcascades))

if os.path.exists(cv2.data.haarcascades):
    print("\nFiles:")
    print(os.listdir(cv2.data.haarcascades))