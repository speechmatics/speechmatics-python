import hashlib
import json
import os
import sqlite3
from datetime import datetime
from io import SEEK_END
from pathlib import Path

from speechmatics.batch_client import BatchClient
from speechmatics.models import ConnectionSettings

DEFAULT_URL = "https://asr.api.speechmatics.com/v2"
FINGERPRINT_SIZE = 1 << 20

HIGHLIGHT_START_MARKER = "\2"
HIGHLIGHT_END_MARKER = "\3"


def connect_to_api(key: str) -> BatchClient:
    settings = ConnectionSettings(url=DEFAULT_URL, auth_token=key)
    return BatchClient(settings)


class Database:
    def __init__(self):
        path = Path.home() / ".config" / "speechmatics-sync" / "database"
        path.parent.mkdir(exist_ok=True, parents=True)
        self.conn = sqlite3.connect(path)
        self.upgrade()

    def upgrade(self):
        self.conn.executescript(
            """
            create table if not exists audio(
                path unique,
                checksum
            );

            create table if not exists transcription(
                config,
                checksum,
                json,
                unique(config, checksum)
            );

            create virtual table if not exists text using fts5(
                transcription_id unindexed,
                data
            );

            create temporary table batch(
                path unique
            );

            create table if not exists log(
                time,
                message
            );
            """
        )

    def start_new_batch(self, paths):
        self.conn.execute("delete from batch")
        for path in paths:
            self.conn.execute(
                "insert into batch(path) values (?)",
                (str(path),),
            )

    def get_unseen_paths(self):
        cursor = self.conn.execute(
            """
            select path from batch
            left join audio using (path)
            where checksum is null
            """
        )
        for (path,) in cursor:
            yield path

    def add_audio(self, path, checksum):
        self.conn.execute(
            "insert or ignore into audio(path) values (?)",
            (path,),
        )
        self.conn.execute(
            "update audio set checksum = ? where path = ?",
            (checksum, path),
        )

    def get_untranscribed_paths(self, transcription_config):
        cursor = self.conn.execute(
            """
            select path from audio
            join batch using (path)
            left join transcription using (checksum)
            where config is null or config <> ?
            """,
            (json.dumps(transcription_config),),
        )
        for (path,) in cursor:
            yield path

    def add_transcription(self, config, path, text_transcript, json_transcript):
        cursor = self.conn.execute(
            """
            insert into transcription(config, checksum, json)
            select ?, checksum, ? from audio where path = ?
            """,
            (json.dumps(config), json_transcript, path),
        )
        self.conn.execute(
            """
            insert into text(transcription_id, data) values (?, ?)
            """,
            (cursor.lastrowid, text_transcript),
        )
        self.conn.commit()

    def log(self, message):
        time = datetime.utcnow()
        self.conn.execute(
            "insert into log(time, message) values (?, ?)",
            (time, message),
        )


def calculate_checksum(path):
    checksum = hashlib.sha1()
    with open(path, "rb") as file:
        head = file.read(FINGERPRINT_SIZE)
        checksum.update(head)
        if os.stat(path).st_size > FINGERPRINT_SIZE:
            file.seek(-FINGERPRINT_SIZE, SEEK_END)
            tail = file.read(FINGERPRINT_SIZE)
            checksum.update(tail)
        return checksum.hexdigest()


def sync(
    root: Path,
    client: BatchClient,
    transcription_config: dict,
    database: Database,
):
    def log(message):
        database.log(message)
        print(message)

    paths = set(root.rglob("*"))
    database.start_new_batch(paths)

    unseen_paths = list(database.get_unseen_paths())
    if unseen_paths:
        log(f"{len(unseen_paths)} unseen path(s) to checksum...")
        for path in unseen_paths:
            log(f"  checksuming {path}")
            checksum = calculate_checksum(path)
            database.add_audio(path, checksum)
        database.conn.commit()

    untranscribed_paths = list(
        sorted(database.get_untranscribed_paths(transcription_config))
    )
    if untranscribed_paths:
        log(f"{len(untranscribed_paths)} unseen path(s) to transcribe...")
        with client as _:
            wrapper = {
                "type": "transcription",
                "transcription_config": transcription_config,
            }
            for path, job_id in client.submit_jobs(untranscribed_paths, wrapper):
                text_transcript = client.get_job_result(job_id, "txt")
                json_transcript = json.dumps(client.get_job_result(job_id, "json-v2"))
                database.add_transcription(
                    transcription_config, path, text_transcript, json_transcript
                )


def fetch_all(database, audio_root):
    yield from database.conn.execute(
        """
        select path, data from text
        join audio on text.transcription_id = transcription.rowid
        join transcription using (checksum)
        where path like ?
        """,
        (f"{audio_root}/%",),
    )


def search(database, audio_root, search_query):
    def match_timestamp(object_transcript, snippet):
        snippet_words = snippet.split()
        best_time, best_score = None, 0
        for start, result in enumerate(object_transcript["results"]):
            end = start + len(snippet_words)
            chunk = object_transcript["results"][start:end]
            chunk_words = [o["alternatives"][0]["content"] for o in chunk]
            score = sum(1 if a == b else 0 for a, b in zip(snippet_words, chunk_words))
            if score > best_score:
                time = result["start_time"]
                best_time, best_score = time, score
        return best_time

    cursor = database.conn.execute(
        """
        select
            path,
            json,
            data,
            snippet(text, 1, ?, ?, '...', 20)
        from text
        join audio on text.transcription_id = transcription.rowid
        join transcription using (checksum)
        where
            instr(path, ?) == 1 and
            text match ?
        order by bm25(text)
        """,
        (
            HIGHLIGHT_START_MARKER,
            HIGHLIGHT_END_MARKER,
            str(audio_root),
            search_query,
        ),
    )

    for row in cursor:
        raw_path, raw_json, text, snippet = row
        path = Path(raw_path)
        if not path.exists():
            continue
        timestamp = match_timestamp(json.loads(raw_json), snippet)
        yield path, timestamp, text, snippet
