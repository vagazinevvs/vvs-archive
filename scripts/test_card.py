import os
import cv2
from process_cards import process_image

# 1. 放置測試圖
input_path = "test_input.jpg"
output_path = "test_output.webp"

if not os.path.exists(input_path):
    print(f"請先將測試圖片放入根目錄並命名為 {input_path}")
    exit(1)

# 2. 讀取並執行管線
img = cv2.imread(input_path)
process_image(img, output_path)
print(f"處理完成！請檢視: {output_path}")