"""
Client module which calls the Speechmatics API
"""
import sqlite3

from speechmatics.batch_client import BatchClient

PATH_TO_FILE = "./example.wav"
LANGUAGE = "en"
WEBHOOK_URL = "YOUR_WEBHOOK_URL"

# Define transcription parameters
conf = {
    "type": "transcription",
    "transcription_config": {"language": LANGUAGE},
    "notification_config": [
        {
            "url": WEBHOOK_URL,
            # Causes the webhook to send transcript in the request body if the job is successful
            "contents": ["transcript.txt"],
        }
    ],
}

# Start a sqlite3 DB server - not production-grade!
connection = sqlite3.connect("database.db")

# Create the DB schema for storing job info
with open("schema.sql", "r", encoding="utf-8") as f:
    connection.executescript(f.read())

# Open the client using a context manager
with BatchClient() as client:
    # Sumbit the job to the API
    job_id = client.submit_job(
        audio=PATH_TO_FILE,
        transcription_config=conf,
    )
    print(f"job {job_id} submitted successfully. Storing in DB.")

    cur = connection.cursor()

    # Insert the new job into the DB
    cur.execute("INSERT INTO jobs (id, status) VALUES (?, ?)", (job_id, "running"))
    connection.commit()
