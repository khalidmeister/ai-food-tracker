# 🥗 AI Meal Tracker (Food Police)

An AI-powered food tracker that runs **locally**. Upload a photo of your meal and the AI identifies the dish, its ingredients, and estimated weights, then raises an **alert** if the meal contains **fried food** or **santan** (coconut milk). Every result is automatically logged to Google Sheets and summarized in a weekly analytics dashboard.

## ✨ Features

- 📷 **Meal photo upload and analysis** (JPG, PNG, HEIC)
- 🧠 **Food component detection** (dish name, preparation tags, ingredients, estimated grams) using Apple Foundation Model
- 🚨 **"Food Police" rule engine**: automatic alerts for fried food (high saturated oil) and santan (saturated cholesterol)
- 📝 **Auto-logging to Google Sheets** as the meal history database
- 📊 **Weekly analytics**: 7-day summary metrics, a daily fried vs. santan chart, and a clean history table

## 🏗️ Architecture

![Architecture](architecture.png)

| Component | Role |
|---|---|
| **Streamlit** | User interface (photo upload, results, analytics dashboard) |
| **FastAPI** | Local backend API that orchestrates analysis, the rule engine, and logging |
| **Apple Foundation Model** | LLM (via the `fm` CLI) that reads the image and generates the JSON output |
| **Google Sheets** | Database for the food log produced from the LLM output |

### Workflow

1. The user uploads a photo in Streamlit.
2. Streamlit sends the file to `POST /analyze` on FastAPI.
3. FastAPI saves the file temporarily and runs `fm respond --image ... --text <prompt>`.
4. The model's JSON output is cleaned and validated (Pydantic), then checked by the rule engine (fried / santan).
5. The result is appended to Google Sheets and returned to Streamlit.
6. The **Weekly Analytics** tab reads directly from Google Sheets to build the charts and metrics.

## 🛠️ Tech Stack

- **Frontend:** Streamlit, Plotly, Pandas
- **Backend:** FastAPI, Uvicorn, Pydantic
- **AI:** Apple Foundation Model (`fm` CLI)
- **Storage:** Google Sheets (`gspread`, `oauth2client`)
- **Images:** Pillow, `pillow-heif` (HEIC support for iPhone photos)

## 📋 Prerequisites

- A Mac with **Apple Intelligence** enabled and the **`fm` CLI** installed (make sure `fm respond` runs in your terminal)
- Python 3.10+
- A Google account with a **Service Account** (`credentials.json`)

## 🚀 Installation

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd <your-project-folder>

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### `requirements.txt`

```txt
fastapi
uvicorn
pydantic
gspread
oauth2client
python-multipart
streamlit
requests
pandas
plotly
pillow-heif
```

## 🔑 Google Sheets Setup

1. Open the [Google Cloud Console](https://console.cloud.google.com/), create a project, and enable the **Google Sheets API** and **Google Drive API**.
2. Create a **Service Account**, download its JSON key, and save it as `credentials.json` in the project root.
3. Create a Google Spreadsheet titled **`Food Tracking Assistant`** with a worksheet named **`Sheet1`**.
4. **Share** the spreadsheet with the service account email (`...@...iam.gserviceaccount.com`) with **Editor** access.
5. Fill the first row (header) with these columns, in this order:

| A | B | C | D | E | F |
|---|---|---|---|---|---|
| `Timestamp` | `menu_name` | `preparation_tag` | `Has Fried` | `Has Santan` | `raw_json` |

### Environment variables (optional)

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_CREDENTIALS_PATH` | `credentials.json` | Path to the service account credentials file |
| `GOOGLE_SHEETS_NAME` | `Food Tracking Assistant` | Spreadsheet name used by the backend |

> ⚠️ **Never commit `credentials.json` to Git.** Add it to `.gitignore`.

## ▶️ Running the App

Run the backend and frontend in two separate terminals.

**Terminal 1: FastAPI backend**

```bash
uvicorn main:app --reload --port 8000
```

**Terminal 2: Streamlit frontend**

```bash
streamlit run app.py
```

Then open `http://localhost:8501`. If the backend runs on a different address, change the **API Base URL** in the sidebar (default: `http://localhost:8000`).

> Adjust `main.py` and `app.py` to match your actual file names.

## 🔌 API Reference

### `GET /`
Health check.

```json
{ "status": "ok", "engine": "Apple Foundation Model (afm) Local API" }
```

### `POST /analyze`
Analyzes a meal photo.

- **Body:** `multipart/form-data` with a `file` field (image)
- **Example:**

```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@nasi_padang.jpg"
```

- **Response:**

```json
{
  "menu_name": "Nasi Padang",
  "preparation_tags": ["fried", "coconut-milk"],
  "ingredients": [
    {
      "ingredient": "Rendang",
      "amount_grams": 100,
      "is_fried": false,
      "contains_santan": true
    }
  ],
  "has_fried": false,
  "has_santan": true,
  "warning_message": "🚨 **SANTAN DETECTED:** Hati-hati kolesterol jenuh!"
}
```

## 📁 Project Structure

```
.
├── app.py              # Streamlit UI (upload & weekly analytics)
├── main.py             # FastAPI backend (analysis, rule engine, logging)
├── credentials.json    # Google service account (DO NOT commit)
├── architecture.png    # Architecture diagram
├── requirements.txt
└── README.md
```

## 🧪 Rule Engine

| Condition | Warning |
|---|---|
| Any ingredient has `is_fried = true` | 🚨 **GORENGAN DETECTED:** Minyak jenuh tinggi! *(high saturated oil)* |
| Any ingredient has `contains_santan = true` | 🚨 **SANTAN DETECTED:** Hati-hati kolesterol jenuh! *(watch out for saturated cholesterol)* |
| Neither | ✅ Safe meal! |

## 🩹 Troubleshooting

- **`Failed to process image with fm CLI`**: make sure `fm` is installed, Apple Intelligence is enabled, and `fm respond` works manually in the terminal.
- **Connection error to the API**: check that FastAPI is running and the **API Base URL** in the sidebar is correct.
- **Data not appearing in Sheets**: confirm the spreadsheet is shared with the service account email and the `credentials.json` path is correct. Sheets logging errors only show up as warnings in the backend log.
- **`Error parse sheet`** in the analytics tab: make sure the sheet header matches the 6 columns above.

## ⚠️ Disclaimer

Ingredient and weight estimates come from an AI model's output and are **not a substitute for advice from a nutritionist or doctor**.

## 📄 License

Add a license of your choice (e.g. MIT).
