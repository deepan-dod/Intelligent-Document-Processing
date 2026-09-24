import os
import time

os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"

from paddleocr import PaddleOCR

ocr = PaddleOCR(
    lang="en",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    enable_mkldnn=False
)


def extract_text(image_path):
    print("\n===== OCR START =====")
    start = time.time()

    results = ocr.predict(image_path)

    print(f"OCR prediction time: {time.time() - start:.2f} seconds")

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

    print(f"Total OCR time: {time.time() - start:.2f} seconds")
    print("===== OCR END =====\n")

    return "\n".join(all_text)