"""
logging configuration
"""

import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs')

    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)

    # Prevent adding multiple handlers if function is called twice
    if logger.handlers:
        return

    handler = RotatingFileHandler(
        filename='logs/discord.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,  
        backupCount=5
    )

    # Format
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(formatter)

    # Attach
    logger.addHandler(handler)