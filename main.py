from fastapi import FastAPI
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
print("DATABASE_URL =", DATABASE_URL)

app = FastAPI()
conn = psycopg2.connect(DATABASE_URL, sslmode="require")  # SSL для Supabase

@app.get("/")
def root():
    with conn.cursor() as cur:
        cur.execute("SELECT NOW()")
        return {"server": "FastLand backend", "time": cur.fetchone()[0]}

@app.get("/clients")
def get_clients():
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, contact_person, phone FROM clients")
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "contact": r[2], "phone": r[3]} for r in rows]
