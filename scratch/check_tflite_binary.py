def check_keyword(path, keyword):
    try:
        with open(path, "rb") as f:
            content = f.read()
        exists = keyword.encode("utf-8") in content
        print(f"File: {path} | Keyword '{keyword}' exists: {exists}")
    except Exception as e:
        print(f"Failed to check {path}: {e}")

if __name__ == "__main__":
    # Server/Client YOLO tflite files
    check_keyword("server/models/yolo26n/object_detection.tflite", "scooter")
    check_keyword("client/assets/models/yolo26n/object_detection.tflite", "scooter")
    check_keyword("server/models/yolo26n/object_detection.tflite", "dog")
    check_keyword("client/assets/models/yolo26n/object_detection.tflite", "dog")
