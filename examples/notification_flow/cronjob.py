"""
Cronjob data sync script which should be run on a regular basis using e.g. k8s cronjobs

Async fallback checking in case of webhook failure is a common pattern in production systems
"""
import sqlite3

from speechmatics.batch_client import BatchClient


# Open the sqlite3 connection
connection = sqlite3.connect("database.db")

# Open the client using a context manager
with BatchClient() as client:
    cur = connection.cursor()

    # Get all jobs still in the running state in the client DB
    cur.execute("SELECT * FROM jobs WHERE status = 'running'")

    rows = cur.fetchall()

    for item in rows:
        # Request job status from Speechmatics API
        res = client.check_job_status(item[0])
        status = res.get("job").get("status")

        # If the job status is no longer running, update the DB
        if "status" in res.get("job") and status != "running":
            cur.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, item[0]))
            connection.commit()
