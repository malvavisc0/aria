from pathlib import Path
from shutil import copyfile


def main():
    env_file = Path().cwd() / ".env"
    if not env_file.exists():
        copyfile(Path().cwd() / ".env.example", env_file)

    from aria.cli.main import app

    app()


if __name__ == "__main__":
    main()
