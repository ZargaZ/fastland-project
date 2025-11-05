import os
from fastapi import FastAPI
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Загружаем .env локально (на хостинге Render переменные окружения уже заданы)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
PORT = int(os.environ.get("PORT", 8000))

app = FastAPI(title="FastLand Backend")

# Подключение к базе данных
def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require", cursor_factory=RealDictCursor)

# Корневой маршрут
@app.get("/")
def root():
    return {"server": "FastLand backend", "status": "running"}

# Маршрут для клиентов
@app.get("/clients")
def get_clients():
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, contact_person, phone FROM clients")
            clients = cur.fetchall()
        conn.close()
        return clients
    except Exception as e:
        return {"error": str(e)}

# Для запуска через python main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
