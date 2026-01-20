"""
Setup script for LinkedIn Post Generator.

Initializes the project by:
- Creating necessary directories
- Copying .env.example to .env if needed
- Initializing the database
- Verifying configuration
"""

import sys
from pathlib import Path
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import get_db
from config.settings import get_settings
from src.logger import logger


def create_directories():
    """Create necessary project directories"""
    logger.info("Creating project directories...")

    directories = [
        "data",
        "data/posts",
        "data/cache",
        "logs",
    ]

    for dir_name in directories:
        dir_path = Path(dir_name)
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"  ✓ {dir_name}/")


def setup_env_file():
    """Copy .env.example to .env if it doesn't exist"""
    logger.info("Setting up environment file...")

    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        logger.info("  ✓ .env file already exists")
    else:
        if env_example.exists():
            shutil.copy(env_example, env_file)
            logger.info("  ✓ Created .env from .env.example")
            logger.warning(
                "  ⚠ Please edit .env file with your actual configuration values"
            )
        else:
            logger.error("  ✗ .env.example not found!")
            return False

    return True


def initialize_database():
    """Initialize the database"""
    logger.info("Initializing database...")

    try:
        db = get_db()
        stats = db.get_stats()
        logger.info(f"  ✓ Database initialized at {db.db_path}")
        logger.info(f"  ✓ Database stats: {stats}")
        return True
    except Exception as e:
        logger.error(f"  ✗ Failed to initialize database: {e}")
        return False


def verify_configuration():
    """Verify configuration is loaded correctly"""
    logger.info("Verifying configuration...")

    try:
        settings = get_settings()
        logger.info(f"  ✓ Environment: {settings.environment}")
        logger.info(f"  ✓ LLM Provider: {settings.llm.provider}")
        logger.info(f"  ✓ LLM Model: {settings.llm.model}")
        logger.info(f"  ✓ Database Path: {settings.storage.database_path}")
        logger.info(f"  ✓ Log Level: {settings.logging.level}")
        return True
    except Exception as e:
        logger.error(f"  ✗ Configuration error: {e}")
        return False


def main():
    """Run the setup process"""
    logger.info("=" * 60)
    logger.info("LinkedIn Post Generator - Setup")
    logger.info("=" * 60)

    steps = [
        ("Creating directories", create_directories),
        ("Setting up environment file", setup_env_file),
        ("Initializing database", initialize_database),
        ("Verifying configuration", verify_configuration),
    ]

    failed = False
    for step_name, step_func in steps:
        try:
            if callable(step_func):
                result = step_func()
                if result is False:
                    failed = True
            else:
                step_func
        except Exception as e:
            logger.error(f"Failed during '{step_name}': {e}")
            failed = True

    logger.info("=" * 60)
    if not failed:
        logger.info("✓ Setup completed successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Edit .env file with your configuration")
        logger.info("2. Install Ollama and pull a model (or configure OpenAI)")
        logger.info("3. Run tests: pytest tests/")
        logger.info("4. Start the application: python src/main.py")
    else:
        logger.error("✗ Setup completed with errors")
        logger.error("Please fix the errors above and run setup again")

    logger.info("=" * 60)


if __name__ == "__main__":
    main()
