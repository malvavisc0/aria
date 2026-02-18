from importlib.resources import as_file, files
from pathlib import Path
from shutil import copyfile


def main():
    env_file = Path().cwd() / ".env"
    if not env_file.exists():
        # Locate the bundled .env.example inside the installed package.
        # This works both when running from source and after pip/uv install.
        env_example_ref = files("aria").joinpath(".env.example")
        with as_file(env_example_ref) as env_example:
            copyfile(env_example, env_file)

    from aria.cli.main import app

    app()


if __name__ == "__main__":
    main()
