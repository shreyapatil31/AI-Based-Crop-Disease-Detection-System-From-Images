import os
import base64
import sqlite3
import re
from io import BytesIO
from datetime import datetime
import cv2
import numpy as np
import tensorflow as tf
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, session


app = Flask(__name__)
app.secret_key = "cropcare_secret_key"

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

model = tf.keras.models.load_model("model.h5", compile=False)

classes = [
    "Healthy",
    "Mosaic",
    "NotSugarcane",
    "RedRot",
    "Rust",
    "Yellow"
]

disease_info = {

    "Healthy": {
        "en": {
            "crop": "Sugarcane",
            "disease": "Healthy",
            "treatment": "No treatment required. Crop is healthy.",
            "medicine": "Not required"
        },
        "mr": {
            "crop": "ऊस",
            "disease": "निरोगी",
            "treatment": "उपचार आवश्यक नाही. पीक निरोगी आहे.",
            "medicine": "आवश्यक नाही"
        },
        "hi": {
            "crop": "गन्ना",
            "disease": "स्वस्थ",
            "treatment": "उपचार आवश्यक नहीं। फसल स्वस्थ है।",
            "medicine": "आवश्यक नहीं"
        }
    },

    "Mosaic": {
        "en": {
            "crop": "Sugarcane",
            "disease": "Mosaic",
            "treatment": "Use healthy seed, remove infected plants and control aphids.",
            "medicine": "Imidacloprid 17.8 SL or Thiamethoxam 25 WG"
        },
        "mr": {
            "crop": "ऊस",
            "disease": "मोजॅक रोग",
            "treatment": "निरोगी बेणे वापरा, संक्रमित झाडे काढा आणि मावा नियंत्रण करा.",
            "medicine": "Imidacloprid किंवा Thiamethoxam"
        },
        "hi": {
            "crop": "गन्ना",
            "disease": "मोज़ेक रोग",
            "treatment": "स्वस्थ बीज उपयोग करें, संक्रमित पौधे हटाएँ और माहू नियंत्रण करें।",
            "medicine": "Imidacloprid या Thiamethoxam"
        }
    },

    "RedRot": {
        "en": {
            "crop": "Sugarcane",
            "disease": "Red Rot",
            "treatment": "Remove infected canes, avoid waterlogging and use healthy setts.",
            "medicine": "Carbendazim treatment"
        },
        "mr": {
            "crop": "ऊस",
            "disease": "लाल कुज रोग",
            "treatment": "संक्रमित ऊस काढून टाका, पाणी साचू देऊ नका.",
            "medicine": "कार्बेन्डाझिम"
        },
        "hi": {
            "crop": "गन्ना",
            "disease": "लाल सड़न रोग",
            "treatment": "संक्रमित गन्ने हटाएं और जलभराव से बचें।",
            "medicine": "कार्बेन्डाजिम"
        }
    },

    "Rust": {
        "en": {
            "crop": "Sugarcane",
            "disease": "Rust",
            "treatment": "Remove infected leaves and spray fungicide.",
            "medicine": "Mancozeb or Propiconazole"
        },
        "mr": {
            "crop": "ऊस",
            "disease": "तांबेरा रोग",
            "treatment": "संक्रमित पाने काढा आणि बुरशीनाशक फवारणी करा.",
            "medicine": "मॅन्कोझेब"
        },
        "hi": {
            "crop": "गन्ना",
            "disease": "रस्ट रोग",
            "treatment": "संक्रमित पत्ते हटाएं और फफूंदनाशक छिड़कें।",
            "medicine": "मैनकोज़ेब"
        }
    },

    "Yellow": {
        "en": {
            "crop": "Sugarcane",
            "disease": "Yellow Leaf",
            "treatment": "Use disease-free seed and control aphids.",
            "medicine": "Imidacloprid"
        },
        "mr": {
            "crop": "ऊस",
            "disease": "पिवळेपणा रोग",
            "treatment": "रोगमुक्त बेणे वापरा आणि मावा नियंत्रण करा.",
            "medicine": "Imidacloprid"
        },
        "hi": {
            "crop": "गन्ना",
            "disease": "पीला पत्ता रोग",
            "treatment": "रोगमुक्त बीज उपयोग करें।",
            "medicine": "Imidacloprid"
        }
    },

    "BandedChlorosis": {
        "en": {
            "crop": "Sugarcane",
            "disease": "Banded Chlorosis",
            "treatment": "Apply balanced fertilizer and remove affected leaves.",
            "medicine": "Zinc sulphate spray"
        },
        "mr": {
            "crop": "ऊस",
            "disease": "पट्टेदार हरितलोप रोग",
            "treatment": "संतुलित खत वापरा आणि संक्रमित पाने काढा.",
            "medicine": "झिंक सल्फेट"
        },
        "hi": {
            "crop": "गन्ना",
            "disease": "बैंडेड क्लोरोसिस",
            "treatment": "संतुलित उर्वरक दें और संक्रमित पत्तियां हटाएं।",
            "medicine": "जिंक सल्फेट"
        }
    },

    "BrownSpot": {
        "en": {
            "crop": "Sugarcane",
            "disease": "Brown Spot",
            "treatment": "Remove infected leaves.",
            "medicine": "Mancozeb"
        },
        "mr": {
            "crop": "ऊस",
            "disease": "तपकिरी डाग",
            "treatment": "संक्रमित पाने काढा.",
            "medicine": "मॅन्कोझेब"
        },
        "hi": {
            "crop": "गन्ना",
            "disease": "ब्राउन स्पॉट",
            "treatment": "संक्रमित पत्ते हटाएं।",
            "medicine": "मैनकोज़ेब"
        }
    },

}


def init_db():
    conn = sqlite3.connect("cropcare.db")

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file TEXT,
            crop TEXT,
            disease TEXT,
            accuracy TEXT,
            time TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            mobile TEXT,
            dob TEXT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    try:
        cursor.execute("ALTER TABLE history ADD COLUMN username TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

init_db()

def is_leaf_image(image_path):
    img = cv2.imread(image_path)

    if img is None:
        return False

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    lower_green = np.array([25, 40, 40])
    upper_green = np.array([90, 255, 255])

    mask = cv2.inRange(hsv, lower_green, upper_green)

    green_ratio = np.sum(mask > 0) / (img.shape[0] * img.shape[1])

    return green_ratio > 0.02

def estimate_severity(image_path):
    img = cv2.imread(image_path)

    if img is None:
        return "Unknown", 0

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    lower_infected = np.array([10, 40, 40])
    upper_infected = np.array([40, 255, 255])

    mask = cv2.inRange(hsv, lower_infected, upper_infected)

    infected_pixels = np.sum(mask > 0)
    total_pixels = img.shape[0] * img.shape[1]

    infected_percent = round((infected_pixels / total_pixels) * 100, 2)

    if infected_percent < 20:
        level = "Mild"
    elif infected_percent < 50:
        level = "Moderate"
    else:
        level = "Severe"

    return level, infected_percent

def climate_risk_prediction(humidity, temperature, rainfall):
    if humidity >= 80 and rainfall >= 5:
        return "High disease risk due to high humidity and rainfall."
    elif humidity >= 70 and temperature >= 25:
        return "Moderate disease risk. Monitor crop regularly."
    else:
        return "Low disease risk based on current climate."

def predict_image(image_path):
    try:
        img = Image.open(image_path).convert("RGB")
    except:
        return None, 0, None, None, None, None, None

    img = img.resize((128, 128))
    img = np.array(img) / 255.0
    img = np.expand_dims(img, axis=0)

    prediction = model.predict(img)

    index = np.argmax(prediction[0])
    confidence = round(float(np.max(prediction[0]) * 100), 2)

    disease = classes[index]

    print("All probabilities:", prediction[0])
    print("Predicted index:", index)
    print("Predicted disease:", disease)
    print("Confidence:", confidence)

    if disease == "NotSugarcane":
        return None, confidence, None, None, None, None, None

    if disease == "RedRot":
        climate_alert = {
            "en": "High humidity and waterlogging increase Red Rot risk.",
            "mr": "जास्त आर्द्रता आणि पाणी साचल्यामुळे लाल कुज रोगाचा धोका वाढतो.",
            "hi": "अधिक नमी और जलभराव से लाल सड़न रोग का खतरा बढ़ता है।"
        }

    elif disease == "Rust":
        climate_alert = {
            "en": "Warm humid weather increases Rust infection risk.",
            "mr": "उबदार आणि दमट हवामानामुळे तांबेरा रोगाचा धोका वाढतो.",
            "hi": "गर्म और नम मौसम से रस्ट रोग का खतरा बढ़ता है।"
        }

    elif disease == "Yellow":
        climate_alert = {
            "en": "High temperature and aphid activity increase Yellow Leaf disease risk.",
            "mr": "जास्त तापमान आणि मावा किडीमुळे पिवळी पाने रोगाचा धोका वाढतो.",
            "hi": "अधिक तापमान और माहू कीट से पीली पत्ती रोग का खतरा बढ़ता है।"
        }

    elif disease == "Mosaic":
        climate_alert = {
            "en": "Hot weather and aphid vectors increase Mosaic disease spread.",
            "mr": "उष्ण हवामान आणि मावा किडीमुळे मोजॅक रोगाचा प्रसार वाढतो.",
            "hi": "गर्म मौसम और माहू कीट से मोज़ेक रोग का प्रसार बढ़ता है।"
        }

    else:
        climate_alert = {
            "en": "Current weather risk is low.",
            "mr": "सध्याच्या हवामानानुसार रोगाचा धोका कमी आहे.",
            "hi": "वर्तमान मौसम के अनुसार रोग का खतरा कम है।"
        }

    info = disease_info[disease]

    growth_stage = "Vegetative Stage"

    severity, severity_percent = estimate_severity(image_path)

    weather_alert = climate_alert

    return info, confidence, growth_stage, severity, severity_percent, climate_alert, weather_alert

def add_history(info, confidence, filename):
    username = session.get("user")
    time_now = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    conn = sqlite3.connect("cropcare.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO history (username, file, crop, disease, accuracy, time)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        username,
        filename,
        info["en"]["crop"],
        info["en"]["disease"],
        confidence,
        time_now
    ))

    conn.commit()
    conn.close()


def get_history():
    username = session.get("user")

    conn = sqlite3.connect("cropcare.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT file, disease, time
        FROM history
        WHERE username = ?
        ORDER BY id DESC
    """, (username,))

    rows = cursor.fetchall()
    conn.close()

    disease_key_map = {
        "Healthy": "Healthy",
        "Mosaic": "Mosaic",
        "Red Rot": "RedRot",
        "Rust": "Rust",
        "Yellow Leaf": "Yellow",
        "Banded Chlorosis": "BandedChlorosis",
        "Brown Rust": "BrownRust",
        "Brown Spot": "BrownSpot",
        "Grassy Shoot": "GrassyShoot",
}

    history = []

    for row in rows:
        file = row[0]
        disease = row[1]
        time = row[2]

        key = disease_key_map.get(disease)

        if key and key in disease_info:
            info = disease_info[key]

            history.append({
                "file": file,

                "disease_en": info["en"]["disease"],
                "disease_mr": info["mr"]["disease"],
                "disease_hi": info["hi"]["disease"],

                "medicine_en": info["en"]["medicine"],
                "medicine_mr": info["mr"]["medicine"],
                "medicine_hi": info["hi"]["medicine"],

                "summary_en": f'{info["en"]["disease"]} detected on {time}.',
                "summary_mr": f'{info["mr"]["disease"]} {time} रोजी आढळला.',
                "summary_hi": f'{info["hi"]["disease"]} {time} को पाया गया.'
            })

    return history

def get_disease_counts(history):
    counts = {
        "Banded Chlorosis": 0,
        "Brown Rust": 0,
        "Brown Spot": 0,
        "Grassy Shoot": 0,
        "Healthy": 0,
        "Mosaic": 0,
        "Red Rot": 0,
        "Rust": 0,
        "Yellow Leaf": 0
    }

    for item in history:
        disease = item["disease_en"]
        if disease in counts:
            counts[disease] += 1

    return counts


def render_page(
    image_path=None,
    info=None,
    confidence=None,
    uploaded_filename=None,
    growth_stage=None,
    severity=None,
    severity_percent=None,
    climate_alert=None,
    weather_alert=None,
    error_message=None
):
    history = get_history()

    healthy_count = sum(1 for item in history if item["disease_en"] == "Healthy")
    total = len(history)
    diseased_count = total - healthy_count

    disease_counts = get_disease_counts(history)

    return render_template(
        "index.html",
        image_path=image_path,
        info=info,
        confidence=confidence,
        uploaded_filename=uploaded_filename,
        total_predictions=total,
        detection_history=history,
        healthy_count=healthy_count,
        diseased_count=diseased_count,
        disease_counts=disease_counts,
        chart_labels=list(disease_counts.keys()),
        chart_values=list(disease_counts.values()),
        growth_stage=growth_stage,
        severity=severity,
        severity_percent=severity_percent,
        weather_alert=weather_alert,
        climate_alert=climate_alert,
        error_message=error_message
    )


@app.route("/camera", methods=["POST"])
def camera():
    if "user" not in session:
        return redirect(url_for("login"))

    data = request.form["camera_image"]
    image_data = data.split(",")[1]

    image_bytes = base64.b64decode(image_data)
    image = Image.open(BytesIO(image_bytes)).convert("RGB")

    filename = "camera_capture.jpg"
    image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    image.save(image_path)

    info, confidence, growth_stage, severity, severity_percent, climate_alert, weather_alert = predict_image(image_path)    
    if info is None:
        return render_page(
            image_path=image_path,
            uploaded_filename=filename,
            confidence=confidence,
            error_message="Please upload only sugarcane leaf image"
        )

    add_history(info, confidence, filename)

    return render_page(
    image_path=image_path,
    info=info,
    confidence=confidence,
    uploaded_filename=filename,
    growth_stage=growth_stage,
    severity=severity,
    severity_percent=severity_percent,
    climate_alert=climate_alert,
    weather_alert=weather_alert
)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("cropcare.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect(url_for("home"))
        else:
            error = "Invalid username or password"

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        name = request.form["name"]
        country_code = request.form["country_code"]
        mobile = request.form["mobile"]
        full_mobile = country_code + mobile
        dob = request.form["dob"]
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            error = "Password and Confirm Password do not match"
            return render_template("register.html", error=error)
        if not re.match(r'^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&.#_]).{6,}$', password):
           error = "Password must contain one capital letter, one digit and one special character"
           return render_template("register.html", error=error)

        try:
            conn = sqlite3.connect("cropcare.db")
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO users (name, mobile, dob, username, password)
                VALUES (?, ?, ?, ?, ?)
            """, (name, full_mobile, dob, username, password))

            conn.commit()
            conn.close()

            return """
            <script>
                alert("Account created successfully!");
                window.location.href = "/login";
            </script>
            """

        except sqlite3.IntegrityError:
            error = "Username already exists"

    return render_template("register.html", error=error)

@app.route("/", methods=["GET", "POST"])
def home():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        file = request.files.get("image")

        if file and file.filename:
            allowed = {"png", "jpg", "jpeg", "webp"}
            filename = file.filename

            if "." not in filename:
                return "Please upload only image files"

            ext = filename.rsplit(".", 1)[1].lower()

            if ext not in allowed:
                return "Please upload only image files"

            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(image_path)

            info, confidence, growth_stage, severity, severity_percent, climate_alert, weather_alert = predict_image(image_path)

            if info is None:
                return render_page(
                    image_path=image_path,
                    uploaded_filename=filename,
                    confidence=confidence,
                    error_message="Please upload only sugarcane leaf image"
                )

            add_history(info, confidence, filename)

            return render_page(
                image_path=image_path,
                info=info,
                confidence=confidence,
                uploaded_filename=filename,
                growth_stage=growth_stage,
                severity=severity,
                severity_percent=severity_percent,
                climate_alert=climate_alert,
                weather_alert=weather_alert
            )
    return render_page()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)