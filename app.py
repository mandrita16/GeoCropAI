import io

import pickle

from pathlib import Path

from typing import Optional

import pandas as pd

import numpy as np

import requests

import torch

from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException

from fastapi.responses import HTMLResponse, RedirectResponse

from fastapi.staticfiles import StaticFiles

from fastapi.templating import Jinja2Templates

from PIL import Image


from sqlalchemy.orm import Session

from starlette.middleware.sessions import SessionMiddleware

from torchvision import transforms

import config

from database import Base, engine, get_db

from models_db import User, UserAdmin, ContactUs

from auth import hash_password, verify_password

from utils.model import ResNet9

from utils.disease import disease_dic

from utils.fertilizer import get_fertilizer_recommendation

BASE_DIR = Path(__file__).resolve().parent

TEMPLATES_DIR = BASE_DIR / "templates"

STATIC_DIR = BASE_DIR / "static"

MODELS_DIR = BASE_DIR / "models"

app = FastAPI(title="GeoCropAI API")

# Use a strong secret from an environment variable in production.

app.add_middleware(

    SessionMiddleware,

    secret_key=getattr(config, "SECRET_KEY", "CHANGE_THIS_SECRET_KEY"),

    same_site="lax",

    https_only=False,

)

if STATIC_DIR.exists():

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Create missing tables without deleting existing SQLite data.

Base.metadata.create_all(bind=engine)

def load_pickle(path: Path):

    with path.open("rb") as file:

        return pickle.load(file)

crop_model_path = MODELS_DIR / "RandomForest.pkl"

crop_recommendation_model = load_pickle(crop_model_path) if crop_model_path.exists() else None

fertilizer_model_path = MODELS_DIR / "Fertilizer.pkl"

fertilizer_recommendation_model = (

    load_pickle(fertilizer_model_path)

    if fertilizer_model_path.exists()

    else None

)

# The fertilizer model is loaded separately above and predicts fertilizer labels.

disease_classes = [

    "Apple___Apple_scab", "Apple___Black_rot", "Apple___Cedar_apple_rust",

    "Apple___healthy", "Blueberry___healthy",

    "Cherry_(including_sour)___Powdery_mildew",

    "Cherry_(including_sour)___healthy",

    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",

    "Corn_(maize)___Common_rust_", "Corn_(maize)___Northern_Leaf_Blight",

    "Corn_(maize)___healthy", "Grape___Black_rot",

    "Grape___Esca_(Black_Measles)",

    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)", "Grape___healthy",

    "Orange___Haunglongbing_(Citrus_greening)", "Peach___Bacterial_spot",

    "Peach___healthy", "Pepper,_bell___Bacterial_spot",

    "Pepper,_bell___healthy", "Potato___Early_blight", "Potato___Late_blight",

    "Potato___healthy", "Raspberry___healthy", "Soybean___healthy",

    "Squash___Powdery_mildew", "Strawberry___Leaf_scorch",

    "Strawberry___healthy", "Tomato___Bacterial_spot", "Tomato___Early_blight",

    "Tomato___Late_blight", "Tomato___Leaf_Mold",

    "Tomato___Septoria_leaf_spot",

    "Tomato___Spider_mites Two-spotted_spider_mite", "Tomato___Target_Spot",

    "Tomato___Tomato_Yellow_Leaf_Curl_Virus", "Tomato___Tomato_mosaic_virus",

    "Tomato___healthy",

]

disease_model_path = MODELS_DIR / "plant_disease_model.pth"

disease_model = None

if disease_model_path.exists():

    disease_model = ResNet9(3, len(disease_classes))

    disease_model.load_state_dict(

        torch.load(disease_model_path, map_location=torch.device("cpu"))

    )

    disease_model.eval()

def render(request: Request, template_name: str, **context):

    return templates.TemplateResponse(

        request=request, name=template_name, context=context

    )

def current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:

    user_id = request.session.get("user_id")

    if user_id is None:

        return None

    return db.query(User).filter(User.id == int(user_id)).first()

def require_user(request: Request, db: Session = Depends(get_db)) -> User:

    user = current_user(request, db)

    if user is None:

        raise HTTPException(status_code=303, headers={"Location": "/login"})

    return user

def weather_fetch(city_name: str):

    api_key = getattr(config, "weather_api_key", "")

    if not api_key or not city_name:

        return None

    try:

        response = requests.get(

            "https://api.openweathermap.org/data/2.5/weather",

            params={"appid": api_key, "q": city_name},

            timeout=8,

        )

        response.raise_for_status()

        weather = response.json()

        main = weather.get("main")

        if not main:

            return None

        return round(main["temp"] - 273.15, 2), main["humidity"]

    except (requests.RequestException, KeyError, TypeError, ValueError):

        return None

def predict_image(image_bytes: bytes) -> str:

    if disease_model is None:

        raise RuntimeError("Disease model file is missing.")

    transform = transforms.Compose([transforms.Resize(256), transforms.ToTensor()])

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    image_tensor = transform(image).unsqueeze(0)

    with torch.no_grad():

        output = disease_model(image_tensor)

        index = torch.max(output, dim=1).indices.item()

    return disease_classes[index]

@app.get("/", response_class=HTMLResponse, name="hello_world")

def hello_world(request: Request):

    return render(request, "index.html")

@app.get("/aboutus", response_class=HTMLResponse)

def aboutus(request: Request):

    return render(request, "aboutus.html")

@app.get("/contact", response_class=HTMLResponse, name="contact")

def contact_page(request: Request):

    return render(request, "contact.html")

@app.post("/contact", response_class=HTMLResponse, name="contact_submit")

def contact_submit(

    request: Request,

    name: str = Form(...),

    email: str = Form(...),

    text: str = Form(...),

    db: Session = Depends(get_db),

):

    db.add(ContactUs(name=name, email=email, text=text))

    db.commit()

    return render(request, "contact.html", message="Message submitted successfully.")

@app.get("/signup", response_class=HTMLResponse, name="signup")

def signup_page(request: Request):

    return render(request, "signup.html", error=None)

@app.post("/signup", name="signup_submit")

def signup_submit(

    request: Request,

    username: str = Form(...),

    password: str = Form(...),

    db: Session = Depends(get_db),

):

    if len(username) < 5 or len(username) > 20 or len(password) < 5 or len(password) > 20:

        return render(request, "signup.html", error="Username and password must be 5–20 characters.")

    if db.query(User).filter(User.username == username).first():

        return render(request, "signup.html", error="Username already exists.")

    user = User(username=username, password=hash_password(password))

    db.add(user)

    db.commit()

    return RedirectResponse("/login", status_code=303)

@app.get("/login", response_class=HTMLResponse, name="login")

def login_page(request: Request):

    return render(request, "login.html", error=None)

@app.post("/login", name="login_submit")

def login_submit(

    request: Request,

    username: str = Form(...),

    password: str = Form(...),

    db: Session = Depends(get_db),

):

    user = db.query(User).filter(User.username == username).first()

    if user and verify_password(password, user.password):

        request.session["user_id"] = user.id

        request.session["role"] = "user"

        return RedirectResponse("/dashboard", status_code=303)

    return render(request, "login.html", error="Invalid username or password.")

@app.get("/logout", name="logout")

def logout(request: Request):

    request.session.clear()

    return RedirectResponse("/", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse, name="dashboard")

def dashboard(request: Request, user: User = Depends(require_user)):

    return render(request, "dashboard.html", title="dashboard", user=user)

@app.get("/crop-recommend", response_class=HTMLResponse, name="crop_recommend")

def crop_recommend(request: Request, user: User = Depends(require_user)):

    return render(request, "crop.html", title="crop-recommend - Crop Recommendation")

@app.get("/fertilizer", response_class=HTMLResponse, name="fertilizer_recommendation")

def fertilizer_recommendation(request: Request, user: User = Depends(require_user)):

    return render(request, "fertilizer.html", title="- Fertilizer Suggestion")

@app.get("/disease-predict", response_class=HTMLResponse, name="disease_prediction")

def disease_prediction(request: Request, user: User = Depends(require_user)):

    return render(request, "disease.html", title="- Disease Detection")

@app.post("/crop-predict", response_class=HTMLResponse, name="crop_prediction")

def crop_prediction(

    request: Request,

    nitrogen: int = Form(...),

    phosphorous: int = Form(...),

    pottasium: int = Form(...),

    ph: float = Form(...),

    rainfall: float = Form(...),

    city: str = Form(""),

    user: User = Depends(require_user),

):

    if crop_recommendation_model is None:

        raise HTTPException(status_code=503, detail="Crop model file is missing.")

    weather = weather_fetch(city)

    if weather is None:

        return render(request, "try_again.html", title="- Crop Recommendation")

    temperature, humidity = weather

    features = pd.DataFrame([{

        "N": nitrogen, "P": phosphorous, "K": pottasium,

        "temperature": temperature, "humidity": humidity,

        "ph": ph, "rainfall": rainfall

    }])

    prediction = crop_recommendation_model.predict(features)[0]

    return render(request, "crop-result.html", prediction=prediction, title="- Crop Recommendation")

@app.post("/fertilizer-predict", response_class=HTMLResponse, name="fert_recommend")
def fert_recommend(
    request: Request,
    nitrogen: float = Form(...),
    phosphorous: float = Form(...),
    pottasium: float = Form(...),
    temperature: float = Form(...),
    humidity: float = Form(...),
    moisture: float = Form(...),
    soil_type: str = Form(...),
    cropname: str = Form(...),
    user: User = Depends(require_user),
):
    """Predict a fertilizer using the trained Fertilizer.pkl pipeline."""
    title = "- Fertilizer Suggestion"

    if fertilizer_recommendation_model is None:
        raise HTTPException(status_code=503, detail="Fertilizer model file is missing.")

    # Validate categorical values against the labels used during training.
    allowed_soils = {"Black", "Clayey", "Loamy", "Red", "Sandy"}
    allowed_crops = {
        "Barley", "Cotton", "Ground Nuts", "Maize", "Millets",
        "Oil seeds", "Paddy", "Pulses", "Sugarcane", "Tobacco", "Wheat",
    }
    if soil_type not in allowed_soils or cropname not in allowed_crops:
        return render(
            request,
            "fertilizer.html",
            title=title,
            error="Please select a valid soil type and crop type.",
        )

    features = pd.DataFrame([{
        "Temperature": temperature,
        "Humidity": humidity,
        "Moisture": moisture,
        "N": nitrogen,
        "P": phosphorous,
        "K": pottasium,
        "Soil_Type": soil_type,
        "Crop_Type": cropname,
    }])

    try:
        predicted_fertilizer = str(fertilizer_recommendation_model.predict(features)[0])
        recommendation = get_fertilizer_recommendation(predicted_fertilizer)
    except Exception as exc:
        # Log the detail in the server console while returning a generic page error.
        print(f"Fertilizer prediction failed: {exc}")
        return render(
            request,
            "fertilizer.html",
            title=title,
            error="Sorry, the fertilizer prediction could not be completed. Please check your inputs and try again.",
        )

    return render(
        request,
        "fertilizer-result.html",
        recommendation=recommendation,
        predicted_fertilizer=predicted_fertilizer,
        title=title,
    )


@app.post("/disease-predict", response_class=HTMLResponse)

async def disease_prediction_submit(

    request: Request,

    file: UploadFile = File(...),

    user: User = Depends(require_user),

):

    if not file.filename:

        return render(request, "disease.html", title="- Disease Detection", error="Please select an image.")

    try:

        image_bytes = await file.read()

        prediction = predict_image(image_bytes)

        # Render the label as text, not untrusted HTML.

        description = disease_dic.get(prediction, prediction)

        return render(request, "disease-result.html", prediction=description, title="- Disease Detection")

    except Exception:

        return render(request, "disease.html", title="- Disease Detection", error="Could not process that image.")

@app.get("/display", response_class=HTMLResponse, name="querydisplay")

def display_contacts(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):

    contacts = db.query(ContactUs).all()

    return render(request, "display.html", alltodo=contacts)

@app.get("/AdminLogin", response_class=HTMLResponse, name="AdminLogin")

def admin_login_page(request: Request):

    return render(request, "adminlogin.html", error=None)

@app.post("/AdminLogin", name="AdminLogin_submit")

def admin_login_submit(

    request: Request,

    username: str = Form(...),

    password: str = Form(...),

    db: Session = Depends(get_db),

):

    admin = db.query(UserAdmin).filter(UserAdmin.username == username).first()

    if admin and verify_password(password, admin.password):

        request.session["admin_id"] = admin.id

        request.session["role"] = "admin"

        return RedirectResponse("/admindashboard", status_code=303)

    return render(request, "adminlogin.html", error="Invalid admin credentials.")

def require_admin(request: Request, db: Session = Depends(get_db)) -> UserAdmin:

    admin_id = request.session.get("admin_id")

    if admin_id is None or request.session.get("role") != "admin":

        raise HTTPException(status_code=303, headers={"Location": "/AdminLogin"})

    admin = db.query(UserAdmin).filter(UserAdmin.id == int(admin_id)).first()

    if admin is None:

        request.session.clear()

        raise HTTPException(status_code=303, headers={"Location": "/AdminLogin"})

    return admin

@app.get("/admindashboard", response_class=HTMLResponse, name="admindashboard")

def admin_dashboard(request: Request, admin: UserAdmin = Depends(require_admin), db: Session = Depends(get_db)):

    return render(request, "admindashboard.html", alltodo=db.query(ContactUs).all(), alluser=db.query(User).all())

@app.get("/reg", response_class=HTMLResponse, name="reg")

def admin_register_page(request: Request):

    return render(request, "reg.html", error=None)

@app.post("/reg", name="reg_submit")

def admin_register_submit(

    request: Request,

    username: str = Form(...),

    password: str = Form(...),

    db: Session = Depends(get_db),

):

    if len(username) < 5 or len(username) > 20 or len(password) < 5 or len(password) > 20:

        return render(request, "reg.html", error="Username and password must be 5–20 characters.")

    if db.query(UserAdmin).filter(UserAdmin.username == username).first():

        return render(request, "reg.html", error="Username already exists.")

    admin = UserAdmin(username=username, password=hash_password(password))

    db.add(admin)

    db.commit()

    return RedirectResponse("/AdminLogin", status_code=303)

if __name__ == "__main__":

    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
