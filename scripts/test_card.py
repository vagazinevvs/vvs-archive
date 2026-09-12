import os
from card_process import process_card_image
import sys
import traceback
import cv2
from card_process import crop_card, apply_white_balance


# 1. 指定輸入與輸出路徑（直接使用成國這張圖，或更名為 test_input.jpg）
input_path = sys.argv[1]
output_path = 'test_ouput.webp'

if not os.path.exists(input_path):
    print(f"找不到測試圖片，請確認根目錄下存在 test_input")
    exit(1)

# 2. 執行處理管線
print(f"正在處理: {input_path} ...")
process_card_image(input_path, output_path)
print(f"處理完成！請檢視: {output_path}")


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "test.webp"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "output.webp"
    
    try:
        print(f"Processing: {input_path}")
        cropped = crop_card(input_path)
        print(f"Crop success, shape: {cropped.shape}")
        
        balanced = apply_white_balance(cropped)
        cv2.imwrite(output_path, balanced)
        print(f"Saved to: {output_path}")
    except Exception as e:
        print("Error encountered:")
        traceback.print_exc()