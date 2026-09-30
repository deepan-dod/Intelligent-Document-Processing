import os
import time

# Avoid the CPU oneDNN/PIR issue we already encountered
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"

from paddleocr import PaddleOCR

print("Loading lightweight OCR model...")

ocr = PaddleOCR(
    lang="en",

    # Lightweight mobile models
    text_detection_model_name="PP-OCRv5_mobile_det",
    text_recognition_model_name="PP-OCRv5_mobile_rec",

    # Disable unnecessary document processing
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,

    # CPU
    device="cpu",
    enable_mkldnn=False
)

print("Lightweight OCR model loaded!")


def extract_text(image_path):

    print("\n===== OCR START =====")

    start = time.time()

    print("Starting OCR prediction...")

    results = ocr.predict(image_path)

    print(
        f"OCR prediction time: "
        f"{time.time() - start:.2f} seconds"
    )

    all_text = []

    for result in results:

        try:
            data = result.json

            if callable(data):
                data = data()

            if isinstance(data, dict):

                data = data.get("res", data)

                texts = data.get("rec_texts", [])

                for text in texts:

                    if text and text.strip():
                        all_text.append(text.strip())

        except Exception as e:

            print("OCR RESULT ERROR:", e)

    print(
        f"Total OCR time: "
        f"{time.time() - start:.2f} seconds"
    )

    print("===== OCR END =====\n")

    return "\n".join(all_text)