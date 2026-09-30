import cv2


def preprocess_image(input_path, output_path):
    image = cv2.imread(input_path)

    if image is None:
        raise ValueError("Could not read image")

    height, width = image.shape[:2]

    # Do not enlarge small images.
    # Only reduce very large images.
    max_width = 1600

    if width > max_width:
        scale = max_width / width
        image = cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_AREA
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    gray = cv2.GaussianBlur(
        gray,
        (3, 3),
        0
    )

    processed = cv2.equalizeHist(gray)

    cv2.imwrite(
        output_path,
        processed
    )

    return output_path