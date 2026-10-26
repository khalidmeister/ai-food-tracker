import subprocess
import json
import os
import pillow_heif
from PIL import Image
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI(title="Local AI Meal Tracker API", version="1.0.0")

# --- GOOGLE SHEETS SETUP ---
SHEET_NAME = os.getenv("GOOGLE_SHEETS_NAME", "Food Tracking Assistant")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")

def get_sheets_client():
    if os.path.exists(CREDENTIALS_FILE):
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).sheet1
    return None

# --- PYDANTIC MODELS ---
class Ingredient(BaseModel):
    ingredient: str
    amount_grams: int
    is_fried: bool
    contains_santan: bool

class AnalysisResponse(BaseModel):
    menu_name: str
    preparation_tags: List[str]
    ingredients: List[Ingredient]
    has_fried: bool
    has_santan: bool
    warning_message: Optional[str] = None

# --- HELPER FUNCTIONS ---
def run_apple_fm_vision(image_path: str) -> dict:
    prompt = (
        "You are a strict nutritional data extractor. Analyze the food image and output ONLY a valid raw JSON object with no markdown formatting, no backticks, and no introductory text. "
        "The JSON structure must be: "
        "{\"menu_name\": \"[Name]\", \"preparation_tags\": [\"[tag]\"], \"ingredients\": [{\"ingredient\": \"[Name]\", \"amount_grams\": 100, \"is_fried\": false, \"contains_santan\": false}]}"
    )
    
    cmd = ["fm", "respond", "--image", image_path, "--text", prompt]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        raw_output = res.stdout.strip()
        
        # Clean potential markdown backticks
        if "```json" in raw_output:
            raw_output = raw_output.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_output:
            raw_output = raw_output.split("```")[1].split("```")[0].strip()
            
        return json.loads(raw_output)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process image with fm CLI: {str(e)}")

# --- ENDPOINTS ---
@app.get("/")
def health_check():
    return {"status": "ok", "engine": "Apple Foundation Model (afm) Local API"}

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_meal(file: UploadFile = File(...)):
    # Save temporary uploaded file
    temp_filename = f"temp_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        buffer.write(await file.read())
        
    try:
        # 1. Run local Apple Foundation Model CLI
        raw_data = run_apple_fm_vision(temp_filename)
        
        menu_name = raw_data.get("menu_name", "Unknown Dish")
        prep_tags = raw_data.get("preparation_tags", [])
        ingredients_raw = raw_data.get("ingredients", [])
        
        ingredients = []
        has_fried = False
        has_santan = False
        
        for item in ingredients_raw:
            # Handle array or primitive boolean values safely
            is_f = item.get("is_fried")
            if isinstance(is_f, list): is_f = is_f[0] if is_f else False
            
            has_s = item.get("contains_santan")
            if isinstance(has_s, list): has_s = has_s[0] if has_s else False
            
            amount = item.get("amount_grams")
            if isinstance(amount, list): amount = amount[0] if amount else 0
            
            if is_f: has_fried = True
            if has_s: has_santan = True
            
            ingredients.append(Ingredient(
                ingredient=item.get("ingredient", "Unknown"),
                amount_grams=int(amount),
                is_fried=bool(is_f),
                contains_santan=bool(has_s)
            ))
            
        # 2. Rule Engine Warning
        warnings = []
        if has_fried:
            warnings.append("🚨 **GORENGAN DETECTED:** Minyak jenuh tinggi!")
        if has_santan:
            warnings.append("🚨 **SANTAN DETECTED:** Hati-hati kolesterol jenuh!")
            
        warning_msg = "\n".join(warnings) if warnings else "✅ Safe meal!"
        
        # 3. Log to Google Sheets
        try:
            sheet = get_sheets_client()
            if sheet:
                row = [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    menu_name,
                    ", ".join(prep_tags),
                    has_fried,
                    has_santan,
                    json.dumps([ing.dict() for ing in ingredients])
                ]
                sheet.append_row(row)
        except Exception as sheet_err:
            print(f"Google Sheets Log Warning: {sheet_err}")

        return AnalysisResponse(
            menu_name=menu_name,
            preparation_tags=prep_tags,
            ingredients=ingredients,
            has_fried=has_fried,
            has_santan=has_santan,
            warning_message=warning_msg
        )
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)