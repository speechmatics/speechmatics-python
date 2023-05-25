# (c) 2022, Cantab Research Ltd.
"""
Wrapper library to interface with Speechmatics ASR batch v2 API.
"""

import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Tuple, Union

import httpx
from polling2 import poll

from speechmatics.exceptions import JobNotFoundException, TranscriptionError
from speechmatics.helpers import get_version
from speechmatics.models import BatchTranscriptionConfig, ConnectionSettings, UsageMode

LOGGER = logging.getLogger(__name__)

# If the logging level is set to DEBUG then websockets logs very verbosely,
# including a hex dump of every message being sent. Setting the websockets
# logger at INFO level specifically prevents this spam.
logging.getLogger("websockets.protocol").setLevel(logging.INFO)

POLLING_DURATION = 15


class _ForceMultipartDict(dict):
    """Creates a dictionary that evaluates to True, even if empty.
    Used in submit_job() to force proper multipart encoding when fetch_data is used.
    See https://github.com/encode/httpx/discussions/2399 (link to psf/requests#1081) for details.
    """

    def __bool__(self):
        return True


class HttpClient(httpx.Client):
    """Wrapper class around httpx.Client that adds the sm-sdk query parameter to request urls"""

    def __init__(self, *args, **kwargs):
        self._from_cli = False
        if "from_cli" in kwargs:
            self._from_cli = kwargs["from_cli"]
            kwargs.pop("from_cli")
        super().__init__(*args, **kwargs)

    def build_request(self, method: str, url, *args, **kwargs):
        cli = "-cli" if self._from_cli is True else ""
        version = get_version()
        url = httpx.URL(url)
        url = url.copy_merge_params({"sm-sdk": f"python{cli}-{version}"})
        return super().build_request(method, url, *args, **kwargs)


class BatchClient:
    """Client class for Speechmatics Batch ASR REST API.

    This client may be used directly but must be closed afterwards, e.g.::

        client = BatchClient(auth_token)
        client.connect()
        list_of_jobs = client.list_jobs()
        client.close()

    It may also be used as a context manager, which handles opening and
    closing the connection for you, e.g.::

        with BatchClient(settings) as client:
            list_of_jobs = client.list_jobs()

    """

    def __init__(
        self,
        connection_settings_or_auth_token: Union[str, ConnectionSettings, None] = None,
        from_cli=False,
    ):
        """
        Args:
            connection_settings_or_auth_token (Union[str, ConnectionSettings, None], optional)
                If `str`,, assumes auth_token passed and default URL being used
                If `None`, attempts using auth_token from config.
                Defaults to `None`
            from_clie (bool)
        """
        if not isinstance(connection_settings_or_auth_token, ConnectionSettings):
            self.connection_settings = ConnectionSettings.create(
                UsageMode.Batch, connection_settings_or_auth_token
            )
        else:
            self.connection_settings = connection_settings_or_auth_token
            self.connection_settings.set_missing_values_from_config(UsageMode.Batch)
        if self.connection_settings.url[-1] == "/":
            self.connection_settings.url = self.connection_settings.url[:-1]
        if not self.connection_settings.url.endswith("/v2"):
            self.connection_settings.url = "/".join(
                [self.connection_settings.url, "v2"]
            )

        self.connection_settings = self.connection_settings
        self.transcription_config = None

        self.default_headers = {
            "Authorization": f"Bearer {self.connection_settings.auth_token}",
            "Accept-Charset": "utf-8",
        }
        self.api_client = None
        self._from_cli = from_cli

    def connect(self):
        """Create a connection to a Speechmatics Transcription REST endpoint"""
        self.api_client = HttpClient(
            base_url=self.connection_settings.url,
            timeout=None,
            headers=self.default_headers,
            http2=True,
            verify=self.connection_settings.ssl_context,
            from_cli=self._from_cli,
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

        :raises httpx.HTTPError: When a request fails, raises an HTTPError
        """
        # pylint: disable=no-member
        with self.api_client.stream(method, path, **kwargs) as response:
            response.read()
            response.raise_for_status()
            return response

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
        audio: Union[Tuple[str, bytes], str, os.PathLike, None],
        transcription_config: Union[
            Dict[str, Any], BatchTranscriptionConfig, str, os.PathLike
        ],
    ) -> str:
        """
        Submits audio and config for transcription.

        :param audio: Audio file path or tuple of filename and bytes, or None if using fetch_url
            NOTE: You must expliticly pass audio=None if providing a fetch_url in the config
        :type audio: os.Pathlike | str | Tuple[str, bytes] | None

        :param transcription_config: Configuration for the transcription.
        :type transcription_config:
            Dict[str, Any] | speechmatics.models.BatchTranscriptionConfig | str

        :returns: Job ID
        :rtype: str

        :raises httpx.HTTPError: For any request errors, httpx exceptions are raised.
        """

        # Handle getting config into a dict
        if isinstance(transcription_config, (str or os.PathLike)):
            with Path(transcription_config).expanduser().open(
                mode="rt", encoding="utf-8"
            ) as file:
                config_dict = json.load(file)
        elif isinstance(transcription_config, BatchTranscriptionConfig):
            config_dict = json.loads(transcription_config.as_config())
        elif isinstance(transcription_config, dict):
            config_dict = transcription_config
        else:
            raise ValueError(
                """Job configuration must be a BatchTranscriptionConfig object,
                a filepath as a string or Path object, or a dict"""
            )

        # If audio=None, fetch_data must be specified
        if audio and "fetch_data" in config_dict:
            raise ValueError("Only one of audio or fetch_data can be set at a time")
        if not audio and "fetch_data" in config_dict:
            audio_data = None
        elif isinstance(audio, (str, os.PathLike)):
            with Path(audio).expanduser().open("rb") as file:
                audio_data = os.path.basename(file.name), file.read()
        elif isinstance(audio, tuple) and "fetch_data" not in config_dict:
            audio_data = audio
        else:
            raise ValueError("Audio must be a filepath or a tuple of (filename, bytes)")

        # httpx seems to expect an un-nested json, throws a type error otherwise.
        config_data = {"config": json.dumps(config_dict, ensure_ascii=False)}

        if audio_data:
            audio_file = {"data_file": audio_data}
        else:
            audio_file = _ForceMultipartDict()

        response = self.send_request("POST", "jobs", data=config_data, files=audio_file)
        return response.json()["id"]

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

        :raises JobNotFoundException : When a job_id is not found.
        :raises httpx.HTTPError: For any request other than 404, httpx exceptions are raised.
        :raises TranscriptionError: When the transcription format is invalid.
        """
        transcription_format = transcription_format.lower()
        if transcription_format not in ["json-v2", "json_v2", "json", "txt", "srt"]:
            raise TranscriptionError(
                'Invalid transcription format. Valid formats are : "json-v2",'
                '"json_v2", "json", "txt", "srt "'
            )

        if transcription_format in ["json-v2", "json", "json_v2"]:
            transcription_format = "json-v2"
        try:
            response = self.send_request(
                "GET",
                "/".join(["jobs", job_id, "transcript"]),
                params={"format": transcription_format},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise JobNotFoundException(f"Could not find job {job_id}") from exc
            raise exc

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

        try:
            response = self.send_request(
                "DELETE",
                "/".join(["jobs", job_id]),
                params={"force": str(force).lower()},
            )
            return (
                f"Job {job_id} deleted"
                if (response.json())["job"]["status"] == "deleted"
                else f"Job {job_id} was not deleted. Error {response.json()}"
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise JobNotFoundException(f"Could not find job {job_id}") from exc
            raise exc
        except KeyError:
            return False

    def check_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check the status of a job.

        :param job_id: ID of previously submitted job.
        :type job_id: str

        :return: Job status
        :rtype: Dict[str, Any]

        :raises JobNotFoundException: When a job_id is not found.
        :raises httpx.HTTPError: For any request other than 404, httpx exceptions are raised.
        """
        try:
            response = self.send_request("GET", "/".join(["jobs", job_id]))
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise JobNotFoundException(f"Job {job_id} not found") from error
            raise error
        return response.json()

    def wait_for_completion(
        self, job_id: str, transcription_format: str = "txt"
    ) -> Union[str, Dict[str, Any]]:
        """
        Blocks until job is complete, returning a transcript in
        the requested format.

        :param job_id: ID of previously submitted job.
        :type job_id: str

        :param transcription_format: Format of transcript. Defaults to txt.
            Valid options are json-v2, txt, srt. json is accepted as an
            alias for json-v2.
        :type format: str

        :return: Transcription in requested format
        :rtype: Union[str, Dict[str, Any]]

        :raises JobNotFoundException : When a job_id is not found.
        :raises httpx.HTTPError: For any request other than 404, httpx exceptions are raised.
        """

        def _poll_for_status() -> bool:
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

        min_rtf = 0.10
        duration = status["job"]["duration"]
        LOGGER.info(
            "Waiting %i sec to begin polling for completion.", round(duration * min_rtf)
        )
        # Wait until the min. processing time has passed before polling.
        time.sleep(duration * min_rtf)

        LOGGER.info("Starting poll.")
        poll(_poll_for_status, step=POLLING_DURATION, timeout=3600)
        return self.get_job_result(job_id, transcription_format)
