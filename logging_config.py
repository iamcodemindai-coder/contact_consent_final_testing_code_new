import logging
import os
from logging.handlers import RotatingFileHandler


LOG_FOLDER = "logs"
LOG_FILE = os.path.join(LOG_FOLDER, "contact_consent.log")


def setup_logging():
    os.makedirs(LOG_FOLDER, exist_ok=True)

    root = logging.getLogger()

    if root.handlers:
        return

    root.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    logging.getLogger(__name__).info(
        "Logging initialized. Log file: %s",
        os.path.abspath(LOG_FILE)
    )
