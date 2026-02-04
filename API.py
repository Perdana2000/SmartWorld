from fastapi import FastAPI
import psycopg2
import os
from datetime import datetime

app = FastAPI()

# Haal de database URL op uit de Render instellingen
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@app.on_event("startup")
def setup_db():
    # Maakt de tabel aan als deze nog niet bestaat
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP,
            licht FLOAT,
            bodemvocht FLOAT,
            water_gegeven BOOLEAN
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()

@app.post("/log_data")
async def log_data(licht: float, bodemvocht: float, water_gegeven: bool):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sensor_data (timestamp, licht, bodemvocht, water_gegeven) VALUES (%s, %s, %s, %s)",
        (datetime.now(), licht, bodemvocht, water_gegeven)
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "success"}