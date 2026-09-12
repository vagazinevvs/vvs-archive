import os
from card_process import process_card_image
import sys

# 1. 指定輸入與輸出路徑（直接使用成國這張圖，或更名為 test_input.jpg）
input_path = sys.argv[1]
output_path = 'test_ouput.jpg'

if not os.path.exists(input_path):
    print(f"找不到測試圖片，請確認根目錄下存在 test_input")
    exit(1)

# 2. 執行處理管線
print(f"正在處理: {input_path} ...")
process_card_image(input_path, output_path)
print(f"處理完成！請檢視: {output_path}")