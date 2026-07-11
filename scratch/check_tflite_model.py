import tensorflow as tf

def inspect_tflite(path):
    print(f"\nInspecting {path}...")
    try:
        interpreter = tf.lite.Interpreter(model_path=path)
        interpreter.allocate_tensors()
        
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        
        print(f"Input details: {input_details[0]['shape']}")
        print(f"Output details count: {len(output_details)}")
        for idx, details in enumerate(output_details):
            print(f"Output {idx} details: shape={details['shape']}, dtype={details['dtype']}")
    except Exception as e:
        print(f"Failed to inspect: {e}")

if __name__ == "__main__":
    inspect_tflite("server/models/yolo26n/object_detection.tflite")
    inspect_tflite("server/models/yolo26n/segmentation.tflite")
