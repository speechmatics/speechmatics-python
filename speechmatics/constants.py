# (c) 2020, Cantab Research Ltd.
"""
Constants available for use by the library.
"""


#: The self-service batch URL for non-enterprise customers.
BATCH_SELF_SERVICE_URL = "https://asr.api.speechmatics.com/v2"


#: The self-service realtime URL for non-enterprise customers.
#: Note that it doesn't have the language added on the end.
RT_SELF_SERVICE_URL = "wss://eu2.rt.speechmatics.com/v2"


CONN_CLOSE_ERR_TYPES = ["protocol_error",
                        "not_authorised",
                        "invalid_model",
                        "quota_exceeded",
                        "timelimit_exceeded",
                        "job_error",
                        "internal_error"]
