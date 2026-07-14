import os
import json
import glob

dirs = [
    r'C:\dev_task\workspace\home_task\Object_Detection_Yolo\obstacle_data_miner\datasets\raw\New_sample',
    r'C:\dev_task\workspace\home_task\Object_Detection_Yolo\obstacle_data_miner\datasets\raw\New_sample_1',
    r'C:\dev_task\workspace\home_task\Object_Detection_Yolo\obstacle_data_miner\datasets\raw\Indo_sample'
]

for d in dirs:
    files = glob.glob(d + '/**/*.json', recursive=True)
    if files:
        print(f"=== {d} ===")
        print(f"File: {files[0]}")
        with open(files[0], 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                print(json.dumps(data, indent=2, ensure_ascii=False)[:1500])
                print("\n..." + "="*50 + "\n")
            except Exception as e:
                print('Error reading JSON:', e)
    else:
        print(f"No JSON files found in {d}")
