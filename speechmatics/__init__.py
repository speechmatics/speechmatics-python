import warnings

from speechmatics.client import *  # noqa
from speechmatics.exceptions import *  # noqa
from speechmatics.models import *  # noqa

warnings.warn(
    "speechmatics-python is deprecated. Migrate to 'speechmatics-rt' for real-time "
    "or 'speechmatics-batch' for batch transcription. "
    "For more information, please visit https://github.com/speechmatics/speechmatics-python-sdk",
    DeprecationWarning,
    stacklevel=2,
)
