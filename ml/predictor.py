import os
import joblib


MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "models",
    "expense_model.pkl"
)


def predict_category(text):

    # Use trained model if available
    if os.path.exists(MODEL_PATH):

        try:
            model = joblib.load(
                MODEL_PATH
            )

            prediction = model.predict(
                [text]
            )

            return str(prediction[0])

        except Exception:
            pass

    # Temporary fallback
    text = text.lower()

    categories = {
        "Food": [
            "restaurant",
            "food",
            "pizza",
            "burger",
            "cafe",
            "coffee",
            "hotel",
            "swiggy",
            "zomato"
        ],

        "Shopping": [
            "amazon",
            "flipkart",
            "clothing",
            "shirt",
            "shoes",
            "mall",
            "shopping"
        ],

        "Travel": [
            "uber",
            "ola",
            "flight",
            "train",
            "bus",
            "fuel",
            "petrol",
            "diesel"
        ],

        "Bills": [
            "electricity",
            "water",
            "internet",
            "mobile",
            "recharge",
            "utility"
        ],

        "Medical": [
            "hospital",
            "pharmacy",
            "medicine",
            "medical",
            "doctor",
            "clinic"
        ]
    }

    for category, words in categories.items():

        for word in words:

            if word in text:
                return category

    return "Other"