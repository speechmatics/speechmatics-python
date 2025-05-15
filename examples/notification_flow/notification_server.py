"""
A server which receives the Speechmatics API Notification (Webhook)

This is a dev example - DO NOT USE IN PRODUCTION
"""

import json
import sqlite3

from flask import Flask, request  # noqa: F401
from flask_cors import CORS, cross_origin  # noqa: F401

from speechmatics.batch_client import BatchClient


app = Flask(__name__)

# In order to receive transcript JSON, allow CORS
# WARNING: ENSURE ROBUST CORS CHECKING IN PRODUCTION
cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"


@app.route("/webhook", methods=["POST"])
@cross_origin()
def process_request():
    """
    Processes the received webhook request
    """

    connection = sqlite3.connect("database.db")
    cur = connection.cursor()

    # Update DB with job status
    args = request.args.to_dict()
    if args["status"] == "success":
        cur.execute("UPDATE jobs SET status = ? WHERE id = ?", ("done", args["id"]))
        connection.commit()

        # Store transcript to file if job is successful
        # IN PRODUCTION, USE ROBUST BLOB / DOCUMENT STORAGE FOR TRANSCRIPTS
        with open(f"{args['id']}.json", "w", encoding="utf-8") as file:
            file.write(json.dumps(request.json))
    else:
        # In case of failure, get the job's specific failure state
        with BatchClient() as client:
            job_id = request.json.get("id")
            cur = connection.cursor()

            # Request job status from Speechmatics API
            res = client.check_job_status(job_id)

            status = res.get("job").get("status")

            # Update the status in the DB
            if "status" in res.get("job"):
                cur.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
                connection.commit()

    return "Successfully received webhook"


if __name__ == "__main__":
    # run app in debug mode on port 8080
    app.run(debug=True, port=8080)
