"""
Golf Range CV — Main entry point.
Starts the CV pipeline and the API server.
"""

import asyncio
import sys
import signal

import uvicorn
from loguru import logger

from src.api.server import app, set_pipeline
from src.pipeline import create_pipeline


def main():
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO",
               format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | {message}")
    logger.add("logs/pipeline.log", rotation="10 MB", level="DEBUG")

    logger.info("=" * 60)
    logger.info("  Golf Range CV — Revenue Protection System")
    logger.info("=" * 60)

    # Create and start the CV pipeline
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/default.yaml"
    pipeline = create_pipeline(config_path)

    # Inject pipeline into API server
    set_pipeline(pipeline)

    # Start CV processing
    pipeline.start()
    logger.info("CV pipeline running")

    # Start API server
    server_config = pipeline.config.get("server", {})
    host = server_config.get("host", "0.0.0.0")
    port = server_config.get("port", 8000)

    logger.info(f"Dashboard API at http://{host}:{port}")
    logger.info(f"WebSocket at ws://{host}:{port}/ws")
    logger.info(f"API docs at http://{host}:{port}/docs")

    try:
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()
