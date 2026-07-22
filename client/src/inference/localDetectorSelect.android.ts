import { LocalDetector } from "./localDetector";
import { TFLiteDetector } from "./tfliteDetector";

export function createLocalDetector(): LocalDetector {
  return new TFLiteDetector();
}
