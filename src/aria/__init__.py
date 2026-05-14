__version__ = "0.1.5"


def main():
    from dotenv import load_dotenv

    # Pre-load .env from CWD so ARIA_HOME and other vars are available
    # before initialization checks (supports Docker mounts at /app/.env).
    load_dotenv()

    from aria.initializer import (
        is_initialized,
        run_initialization,
        setup_chainlit_config,
        setup_public_assets,
    )

    if not is_initialized():
        run_initialization()

    # Idempotent — ensures assets exist even for already-initialized setups
    # (e.g. after upgrade or first run with new asset extraction logic).
    setup_public_assets()
    setup_chainlit_config()

    from aria.cli.main import app

    app()


if __name__ == "__main__":
    main()
