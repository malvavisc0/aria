__version__ = "0.1.2"


def main():
    from aria.initializer import is_initialized, run_initialization

    if not is_initialized():
        run_initialization()

    from aria.cli.main import app

    app()


if __name__ == "__main__":
    main()
