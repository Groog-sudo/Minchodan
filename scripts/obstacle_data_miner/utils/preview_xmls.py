import glob
import xml.etree.ElementTree as ET

for dir_type in ['bbox', 'polygon']:
    files = glob.glob(f'C:\\dev_task\\workspace\\home_task\\Object_Detection_Yolo\\obstacle_data_miner\\datasets\\raw\\Indo_sample\\{dir_type}\\*.xml')
    if files:
        print(f"=== {dir_type} XML ===")
        with open(files[0], 'r', encoding='utf-8') as f:
            print(f.read()[:1000])
        print("\n..." + "="*50 + "\n")
