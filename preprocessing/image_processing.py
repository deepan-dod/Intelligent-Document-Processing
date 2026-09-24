import cv2


def preprocess_image(input_path, output_path):
    image = cv2.imread(input_path)

    if image is None:
        raise ValueError("Could not read image")

    # Resize if image is too small
    height, width = image.shape[:2]

    if width < 1000:
        scale = 1000 / width
        image = cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC
        )

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    # Noise reduction
    gray = cv2.GaussianBlur(
        gray,
        (3, 3),
        0
    )

    # Improve contrast
    processed = cv2.equalizeHist(gray)

    cv2.imwrite(
        output_path,
        processed
    )

    return output_path