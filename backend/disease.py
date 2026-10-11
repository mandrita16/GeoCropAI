import os
import io

import torch
from PIL import Image
from torchvision import transforms

from fastapi import APIRouter, UploadFile, File, HTTPException

from utils.model import ResNet9
from utils.disease import disease_dic


router = APIRouter(
    prefix="/ml",
    tags=["Disease Detection"]
)


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "plant_disease_model.pth"
)


# Same class order used by the original project
disease_classes = [
    'Apple___Apple_scab',
    'Apple___Black_rot',
    'Apple___Cedar_apple_rust',
    'Apple___healthy',
    'Blueberry___healthy',
    'Cherry_(including_sour)___Powdery_mildew',
    'Cherry_(including_sour)___healthy',
    'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot',
    'Corn_(maize)___Common_rust_',
    'Corn_(maize)___Northern_Leaf_Blight',
    'Corn_(maize)___healthy',
    'Grape___Black_rot',
    'Grape___Esca_(Black_Measles)',
    'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)',
    'Grape___healthy',
    'Orange___Haunglongbing_(Citrus_greening)',
    'Peach___Bacterial_spot',
    'Peach___healthy',
    'Pepper,_bell___Bacterial_spot',
    'Pepper,_bell___healthy',
    'Potato___Early_blight',
    'Potato___Late_blight',
    'Potato___healthy',
    'Raspberry___healthy',
    'Soybean___healthy',
    'Squash___Powdery_mildew',
    'Strawberry___Leaf_scorch',
    'Strawberry___healthy',
    'Tomato___Bacterial_spot',
    'Tomato___Early_blight',
    'Tomato___Late_blight',
    'Tomato___Leaf_Mold',
    'Tomato___Septoria_leaf_spot',
    'Tomato___Spider_mites Two-spotted_spider_mite',
    'Tomato___Target_Spot',
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus',
    'Tomato___Tomato_mosaic_virus',
    'Tomato___healthy'
]


# Load model
try:
    disease_model = ResNet9(
        3,
        len(disease_classes)
    )

    disease_model.load_state_dict(
        torch.load(
            MODEL_PATH,
            map_location=torch.device("cpu")
        )
    )

    disease_model.eval()

except Exception as e:
    disease_model = None
    print(f"Disease model loading error: {e}")


# Same preprocessing as original project
transform = transforms.Compose([
    transforms.Resize(256),
    transforms.ToTensor()
])


@router.post("/disease-prediction")
async def disease_prediction(
    file: UploadFile = File(...)
):

    if disease_model is None:
        raise HTTPException(
            status_code=500,
            detail="Disease detection model could not be loaded"
        )

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a valid image file"
        )

    try:
        image_bytes = await file.read()

        image = Image.open(
            io.BytesIO(image_bytes)
        ).convert("RGB")

        image_tensor = transform(image)

        image_tensor = torch.unsqueeze(
            image_tensor,
            0
        )

        with torch.no_grad():
            output = disease_model(image_tensor)

        _, prediction_index = torch.max(
            output,
            dim=1
        )

        prediction = disease_classes[
            prediction_index[0].item()
        ]

        disease_info = disease_dic.get(
            prediction,
            ""
        )

        return {
            "success": True,
            "prediction": prediction,
            "disease_info": disease_info
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Disease prediction failed: {str(e)}"
        )