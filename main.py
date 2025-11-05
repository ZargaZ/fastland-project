import os
from fastapi import FastAPI
import psycopg2
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Настройка порта Render
port_str = os.environ.get("PORT")
try:
    PORT = int(port_str) if port_str else 8000
except ValueError:
    PORT = 8000

# Инициализация приложения FastAPI
app = FastAPI(title="FastLand Backend")

# Подключение к базе данных Supabase
try:
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    print("✅ Connected to database successfully")
except Exception as e:
    print("❌ Database connection error:", e)
    conn = None

@app.get("/")
def root():
    if conn:
        with conn.cursor() as cur:
            cur.execute("SELECT NOW()")
            server_time = cur.fetchone()[0]
        return {"server": "FastLand backend", "time": server_time}
    else:
        return {"server": "FastLand backend", "time": "DB not connected"}

@app.get("/clients")
def get_clients():
    if conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, contact_person, phone FROM clients")
            rows = cur.fetchall()
            return [{"id": r[0], "name": r[1], "contact": r[2], "phone": r[3]} for r in rows]
    else:
        return {"error": "Database not connected"}

# Точка входа для запуска через python main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
