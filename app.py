import os
import shutil
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from ultralytics import YOLO
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

model = YOLO("best.pt")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SCORE_RULES = {
    'Correct': 10,
    'Incorrect': -5
}

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "smart_city_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD")
    )
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'citizen',
            trust_score NUMERIC(4,1) DEFAULT 50.0
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            latitude VARCHAR(100) NOT NULL,
            longitude VARCHAR(100) NOT NULL,
            description TEXT,
            image_path VARCHAR(255) NOT NULL,
            status VARCHAR(50) DEFAULT 'En attente',
            ai_evaluation VARCHAR(50) DEFAULT 'Non évalué',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trust_history (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            report_id INT,
            old_score NUMERIC(4,1),
            new_score NUMERIC(4,1),
            action VARCHAR(50),
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    conn.commit()
    cursor.close()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
    user = cursor.fetchone()
    
    if user:
        if user['role'] == 'admin':
            cursor.close()
            conn.close()
            return RedirectResponse(url="/admin", status_code=303)
        
        trust_score = user['trust_score']
        
        cursor.execute("SELECT COUNT(*) AS total FROM reports WHERE email = %s", (email,))
        total_reports = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) AS pending FROM reports WHERE email = %s AND status = 'En attente'", (email,))
        pending_reports = cursor.fetchone()['pending']
        
        cursor.execute("SELECT COUNT(*) AS resolved FROM reports WHERE email = %s AND status = 'Résolu'", (email,))
        resolved_reports = cursor.fetchone()['resolved']
        
        cursor.execute("SELECT latitude, longitude, description, status, created_at FROM reports WHERE email = %s ORDER BY created_at DESC", (email,))
        user_reports = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return templates.TemplateResponse(
            request=request, 
            name="index.html", 
            context={
                "email": email,
                "trust_score": trust_score,
                "total": total_reports, 
                "pending": pending_reports, 
                "resolved": resolved_reports,
                "user_reports": user_reports
            }
        )
    else:
        cursor.close()
        conn.close()
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Email ou mot de passe incorrect ou compte supprimé"})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")

@app.post("/register")
async def register(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (email, password, role, trust_score) VALUES (%s, %s, 'citizen', 50.0)", (email, password))
        conn.commit()
        cursor.close()
        conn.close()
        return RedirectResponse(url="/login", status_code=303)
    except psycopg2.errors.UniqueViolation:
        return templates.TemplateResponse(request=request, name="register.html", context={"error": "Cet email est déjà utilisé"})

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM reports ORDER BY created_at DESC")
    reports = cursor.fetchall()
    cursor.close()
    conn.close()
    return templates.TemplateResponse(request=request, name="admin.html", context={"reports": reports})

@app.post("/update-status/{report_id}")
async def update_status(report_id: int, status: str = Form(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE reports SET status = %s WHERE id = %s", (status, report_id))
    conn.commit()
    cursor.close()
    conn.close()
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/evaluate-ai/{report_id}")
async def evaluate_ai(report_id: int, evaluation: str = Form(...)):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("UPDATE reports SET ai_evaluation = %s WHERE id = %s RETURNING image_path, email", (evaluation, report_id))
    report = cursor.fetchone()
    
    if report:
        user_email = report['email']
        
        if evaluation == "Incorrect":
            os.makedirs("static/failed_dataset", exist_ok=True)
            src_path = report['image_path']
            if os.path.exists(src_path):
                filename = os.path.basename(src_path)
                shutil.copy(src_path, f"static/failed_dataset/{filename}")
        
        cursor.execute("SELECT trust_score FROM users WHERE email = %s", (user_email,))
        user_data = cursor.fetchone()
        
        if user_data:
            old_score = float(user_data['trust_score'])
            score_change = SCORE_RULES.get(evaluation, 0)
            
            new_score = min(100.0, max(0.0, old_score + score_change))
            
            cursor.execute("UPDATE users SET trust_score = %s WHERE email = %s", (new_score, user_email))
            
            cursor.execute("""
                INSERT INTO trust_history (email, report_id, old_score, new_score, action)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_email, report_id, old_score, new_score, f"ia_{evaluation.lower()}"))
            
            if new_score < 10.0:
                cursor.execute("DELETE FROM users WHERE email = %s", (user_email,))
                
        conn.commit()
        
    cursor.close()
    conn.close()
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/upload-report")
async def upload_report(request: Request, email: str = Form(...), latitude: str = Form(...), longitude: str = Form(...), description: str = Form(...), image: UploadFile = File(...)):
    
    filename_lower = image.filename.lower()
    if "screenshot" in filename_lower or "capture" in filename_lower or "screen" in filename_lower:
        return HTMLResponse(content="<h1>Erreur : Les captures d'écran (Screenshots) sont strictement interdites. Veuillez utiliser une photo réelle prise par l'appareil photo.</h1>", status_code=400)
        
    os.makedirs("static/uploads", exist_ok=True)
    image_path = f"static/uploads/{image.filename}"
    
    with open(image_path, "wb") as buffer:
        buffer.write(await image.read())
    
    results = model(image_path, conf=0.60)
    
    danger_detected = False
    for result in results:
        if len(result.boxes) > 0:
            danger_detected = True
            result.save(filename=image_path)
            break
            
    if danger_detected:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reports (email, latitude, longitude, description, image_path, status) VALUES (%s, %s, %s, %s, %s, 'En attente')",
            (email, latitude, longitude, description, image_path)
        )
        conn.commit()
        cursor.close()
        conn.close()

        google_maps_url = f"https://www.google.com/maps?q={latitude},{longitude}"
        message = (
            " **ALERTE : Danger Détecté !** \n\n"
            f"Signalé par : {email}\n"
            f"Description : {description}\n"
            f"Type : Incendie / Danger identifié par l'IA\n"
            f"Localisation : {latitude}, {longitude}\n"
            f"Lien Maps : {google_maps_url}"
        )
        
        url_text = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url_text, data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})
        
        url_photo = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open(image_path, "rb") as photo_file:
            requests.post(url_photo, data={"chat_id": TELEGRAM_CHAT_ID}, files={"photo": photo_file})
            
        response_message = """
        <html>
        <head>
            <link href="https://cdn.jsdelivr.net/npm/remixicon@4.2.0/fonts/remixicon.css" rel="stylesheet" />
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700&display=swap" rel="stylesheet">
            <style>
                body { font-family: 'Inter', sans-serif; background: #F4EEE2; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; color: #13242C; }
                .card { background: #FFFFFF; padding: 40px; border-radius: 12px; border: 1px solid #DCD2BA; text-align: center; max-width: 500px; box-shadow: 0 4px 12px rgba(19,36,44,0.05); }
                .icon { font-size: 48px; color: #5C7A4C; margin-bottom: 16px; }
                h1 { font-size: 20px; font-weight: 700; margin: 0 0 12px 0; }
                p { font-size: 14px; color: #5C6670; margin: 0 0 24px 0; line-height: 1.5; }
                .btn { display: inline-block; padding: 12px 24px; background: #A8392F; color: #FFFFFF; text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: 600; }
                .btn:hover { background: #8A2E25; }
            </style>
        </head>
        <body>
            <div class="card">
                <div class="icon"><i class="ri-checkbox-circle-fill"></i></div>
                <h1>Signalement Transmis</h1>
                <p>Votre signalement a été transmis avec succès aux autorités et enregistré. Merci pour votre civisme !</p>
                <a href="/" class="btn">Retour au portail</a>
            </div>
        </body>
        </html>
        """
    else:
        response_message = """
        <html>
        <head>
            <link href="https://cdn.jsdelivr.net/npm/remixicon@4.2.0/fonts/remixicon.css" rel="stylesheet" />
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700&display=swap" rel="stylesheet">
            <style>
                body { font-family: 'Inter', sans-serif; background: #F4EEE2; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; color: #13242C; }
                .card { background: #FFFFFF; padding: 40px; border-radius: 12px; border: 1px solid #DCD2BA; text-align: center; max-width: 500px; box-shadow: 0 4px 12px rgba(19,36,44,0.05); }
                .icon { font-size: 48px; color: #C0852A; margin-bottom: 16px; }
                h1 { font-size: 20px; font-weight: 700; margin: 0 0 12px 0; }
                p { font-size: 14px; color: #5C6670; margin: 0 0 24px 0; line-height: 1.5; }
                .btn { display: inline-block; padding: 12px 24px; background: #1B3640; color: #FFFFFF; text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: 600; }
            </style>
        </head>
        <body>
            <div class="card">
                <div class="icon"><i class="ri-shield-check-fill"></i></div>
                <h1>Analyse Terminée</h1>
                <p>Aucun danger ou anomalie n'a été détecté par l'intelligence artificielle sur cette image.</p>
                <a href="/" class="btn">Retour au portail</a>
            </div>
        </body>
        </html>
        """
        if os.path.exists(image_path):
            os.remove(image_path)
        
    return HTMLResponse(content=response_message, status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)