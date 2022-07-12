# (c) 2022, Cantab Research Ltd.
"""
Wrapper library to interface with Speechmatics ASR batch v2 API.
"""

import json
import logging
import os
import time
from typing import Any, Dict, Tuple, Union, List

import httpx
from polling2 import poll

from speechmatics.exceptions import TranscriptionError, JobNotFoundException
from speechmatics.models import ConnectionSettings, BatchTranscriptionConfig

LOGGER = logging.getLogger(__name__)

# If the logging level is set to DEBUG then websockets logs very verbosely,
# including a hex dump of every message being sent. Setting the websockets
# logger at INFO level specifically prevents this spam.
logging.getLogger("websockets.protocol").setLevel(logging.INFO)

POLLING_DURATION = 15


class BatchClient:
    """Client class for Speechmatics Batch ASR REST API.

    This client may be used directly but must be closed afterwards, e.g.::

        settings = ConnectionSettings(url="https://{api}/v2",
        auth_token="{token}")
        client = BatchClient(settings)
        client.connect()
        list_of_jobs = client.list_jobs()
        client.close()

    It may also be used as a context manager, which handles opening and
    closing the connection for you, e.g.::

        with BatchClient(settings) as client:
            list_of_jobs = client.list_jobs()

    """

    def __init__(self, connection_settings: ConnectionSettings):
        """Constructor method.

        :param connection_settings: Connection settings for API
        :type connection_settings: speechmatics.models.ConnectionSettings.
        """
        if not connection_settings.url.endswith("/v2"):
            if connection_settings.url[-1] == "/":
                connection_settings.url = connection_settings.url[:-1]
            connection_settings.url = "/".join([connection_settings.url, "v2"])

        self.connection_settings = connection_settings
        self.transcription_config = None

        self.default_headers = {
            "Authorization": f"Bearer {self.connection_settings.auth_token}",
            "Accept-Charset": "utf-8",
        }
        self.api_client = None

    def connect(self):
        """Create a connection to a Speechmatics Transcription REST endpoint"""
        self.api_client = httpx.Client(
            base_url=self.connection_settings.url,
            timeout=None,
            headers=self.default_headers,
            http2=True,
            verify=self.connection_settings.ssl_context,
        )
        return self

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_value, traceback):
        # pylint: disable=redefined-outer-name
        self.close()

    def close(self) -> None:
        """
        Clean up/close client connection pool.

        This is required when using the client directly, but not required when
        using the client as a context manager.

        :rtype: None
        """
        self.api_client.close()

    def send_request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """
        Send a request using httpx.Client()

        :param method: HTTP request method
        :type method: str

        :param path: Configuration for the transcription.
        :type path: str

        :param **kwargs: Any valid kwarg of httpx.Client

        :returns: httpx Response object
        :rtype: httpx.Response
        """
        # pylint: disable=no-member
        try:
            with self.api_client.stream(method, path, **kwargs) as response:
                response.read()
                if response.status_code in [404, 423]:
                    # The API returns 404 when:
                    #  - checking status of a non-existent job id
                    #  - attempting to retrieve the transcript of an incomplete job
                    #  - attempting to delete a non-existent job
                    # The API returns 423 when:
                    #  - attempting to delete a running job without force=true
                    # parameter.
                    # These cases are handled in their corresponding functions.
                    return response

                response.raise_for_status()
                return response

        except httpx.HTTPError as exc:
            LOGGER.error(
                "Error response %s while requesting %s . Details: %s",
                exc.response.status_code,
                exc.request.url,
                exc.response.text,  # response.json()['detail'] Which would be nicer, crashes on 401.
            )
            raise httpx.RequestError(exc)

    def list_jobs(self) -> List[Dict[str, Any]]:
        """
        Lists last 100 jobs within 7 days associated with auth_token for the SaaS
        or all of the jobs for the batch appliance.

        :returns: List of jobs
        :rtype: List[Dict[str, Any]]
        """
        return self.send_request("GET", "jobs").json()["jobs"]

    def submit_job(
        self,
        audio: Union[Tuple[str, bytes], str, os.PathLike],
        transcription_config: Union[
            Dict[str, Any], BatchTranscriptionConfig, str, os.PathLike
        ],
    ) -> str:
        """
        Submits audio and config for transcription.

        :param audio: Audio file path or tuple of filename and bytes
        :type audio: os.Pathlike | str | Tuple[str, bytes]

        :param transcription_config: Configuration for the transcription.
        :type transcription_config:
            Dict[str, Any] | speechmatics.models.BatchTranscriptionConfig | str

        :returns: Job ID
        :rtype: str
        """
        if isinstance(transcription_config, (str or os.PathLike)):
            config_json = json.dumps(self._from_file(transcription_config, "json"))
        elif isinstance(transcription_config, BatchTranscriptionConfig):
            config_json = transcription_config.as_config()
        elif isinstance(transcription_config, dict):
            config_json = json.dumps(transcription_config)
        else:
            raise ValueError(
                """Job configuration must be a BatchTranscriptionConfig object,
                a filepath as a string or Path object, or a dict"""
            )
        config_data = {"config": config_json.encode("utf-8")}

        if isinstance(audio, (str, os.PathLike)):
            audio_data = self._from_file(audio, "binary")
        elif isinstance(audio, tuple):
            audio_data = audio
        else:
            raise ValueError(
                "Audio must be a filepath or a tuple of" "(filename, bytes)"
            )
        audio_file = {"data_file": audio_data}

        request = self.send_request(
            "POST", "jobs", data=config_data, files=audio_file
        ).json()
        return request["id"]

    def get_job_result(
        self,
        job_id: str,
        transcription_format: str = "json-v2",
    ) -> Union[bool, str, Dict[str, Any]]:
        """
        Request results of a transcription job.

        :param job_id: ID of previously submitted job.
        :type job_id: str

        :param transcription_format: Format of transcript. Defaults to json.
            Valid options are json-v2, txt, srt. json is accepted as an
            alias for json-v2.
        :type format: str

        :returns: False if job is still running or does not exist, or
            transcription in requested format
        :rtype: bool | str | Dict[str, Any]
        """
        transcription_format = transcription_format.lower()
        if transcription_format not in ["json-v2", "json_v2", "json", "txt", "srt"]:
            raise TranscriptionError(
                'Invalid transcription format. Valid formats are : "json-v2",'
                '"json_v2", "json", "txt", "srt "'
            )

        if transcription_format in ["json-v2", "json", "json_v2"]:
            transcription_format = "json-v2"

        response = self.send_request(
            "GET",
            "/".join(["jobs", job_id, "transcript"]),
            params={"format": transcription_format},
        )
        if response.status_code == 404:
            return f"Job {job_id} not found"
        if transcription_format == "json-v2":
            return response.json()
        return response.text

    def delete_job(self, job_id: str, force: bool = False) -> str:
        """
        Delete a job. Must pass force=True to cancel a running job.

        :param job_id: ID of previously submitted job.
        :type job_id: str

        :param force: When set, a running job will be force terminated. When
            unset (default), a running job will not be terminated and we will
            return False.
        :type format: bool

        :return: Deletion status
        :rtype: str
        """
        response = self.send_request(
            "DELETE",
            "/".join(["jobs", job_id]),
            params={"force": str(force).lower()},
        )

        try:
            # If we got a 404, we can assume the job doesn't exist
            # or was previously deleted.
            if response.status_code == 404:
                return f"Job {job_id} not found"

            return (
                f"Job {job_id} deleted"
                if (response.json())["job"]["status"] == "deleted"
                else f"Job {job_id} was not deleted. Error {response.json()}"
            )

        except KeyError:
            return False

    def check_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check the status of a job.

        :param job_id: ID of previously submitted job.
        :type job_id: str

        :return: Job status
        :rtype: Dict[str, Any]
        """
        return self.send_request("GET", "/".join(["jobs", job_id])).json()

    def wait_for_completion(
        self, job_id: str, transcription_format: str = "txt"
    ) -> Union[str, Dict[str, Any]]:
        """
        Blocks until job is complete, returning a transcript in
        the requested format.

        :param job_id: ID of previously submitted job.
        :type job_id: str

        :param transcription_format: Format of transcript. Defaults to json.
            Valid options are json-v2, txt, srt. json is accepted as an
            alias for json-v2.
        :type format: str

        :return: Transcription in requested format
        :rtype: Union[str, Dict[str, Any]]

        :raises JobNotFoundException : When a job_id is not found.
        """

        def _poll_for_status() -> bool:
            if self.check_job_status(job_id).get("job") is None:
                raise JobNotFoundException(
                    f"Job ID {job_id} is not found and might have been"
                    "deleted externally."
                )

            job_status = self.check_job_status(job_id)["job"]["status"]
            if job_status == "done":
                return True
            if job_status == "running":
                LOGGER.info(
                    "Job ID %s still running, polling again in %s seconds.",
                    job_id,
                    POLLING_DURATION,
                )
                return False
            raise TranscriptionError(f"{job_id} status {job_status}")

        status = self.check_job_status(job_id)

        if status["job"]["status"] == "done":
            return self.get_job_result(job_id, transcription_format)

        min_rtf = 0.25
        duration = status["job"]["duration"]
        LOGGER.info(
            "Waiting %i sec to begin polling for completion.", round(duration * min_rtf)
        )
        # Wait until the min. processing time has passed before polling.
        time.sleep(duration * min_rtf)

        LOGGER.info("Starting poll.")
        poll(_poll_for_status, step=POLLING_DURATION, timeout=3600)
        return self.get_job_result(job_id, transcription_format)

    # pylint:disable=no-self-use
    # pylint:disable=inconsistent-return-statements
    def _from_file(
        self, path: Union[str, os.PathLike], filetype: str
    ) -> Union[Dict[Any, Any], Tuple[str, bytes]]:
        """Retreive data from a file.
        For filetype=="json", returns a dict
        For filetype=="binary", returns a tuple of (filename, data)
        """
        if filetype == "json":
            with open(path, mode="rt", encoding="utf-8") as file:
                return json.load(file)
        elif filetype == "binary":
            with open(path, mode="rb") as file:
                return os.path.basename(file.name), file.read()
