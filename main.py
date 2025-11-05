import os
from fastapi import FastAPI
import psycopg2

DATABASE_URL = "postgresql://postgres.wenkfujkfqfuatgtqsmo:Wasd3knopkI@aws-1-eu-west-1.pooler.supabase.com:6543/postgres"

app = FastAPI()

try:
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
except Exception as e:
    print("❌ Database connection error:", e)
    conn = None

@app.get("/")
def root():
    if conn:
        with conn.cursor() as cur:
            cur.execute("SELECT NOW()")
            return {"server": "FastLand backend", "time": cur.fetchone()[0]}
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
        return {"error": "DB not connected"}



