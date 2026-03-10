from pathlib import Path

from aria.helpers.dotenv import parse_dotenv, write_dotenv


def test_parse_dotenv_preserves_values_and_raw_lines(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# Header\n" "DEBUG = true  # comment\n" "SERVER_PORT = 9876\n" "\n",
        encoding="utf-8",
    )

    values, raw_lines = parse_dotenv(env_path)

    assert values == {"DEBUG": "true", "SERVER_PORT": "9876"}
    assert raw_lines == [
        "# Header",
        "DEBUG = true  # comment",
        "SERVER_PORT = 9876",
        "",
    ]


def test_write_dotenv_updates_existing_and_keeps_comments(
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "DEBUG = true  # verbose\n" "SERVER_PORT = 9876\n" "# keep me\n",
        encoding="utf-8",
    )

    _, raw_lines = parse_dotenv(env_path)
    write_dotenv(
        env_path,
        values={"DEBUG": "false", "SERVER_PORT": "9999"},
        raw_lines=raw_lines,
    )

    assert env_path.read_text(encoding="utf-8") == (
        "DEBUG = false  # verbose\n" "SERVER_PORT = 9999\n" "# keep me\n"
    )


def test_write_dotenv_appends_missing_keys(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("DEBUG = true\n", encoding="utf-8")

    _, raw_lines = parse_dotenv(env_path)
    write_dotenv(
        env_path,
        values={"DEBUG": "false", "SERVER_HOST": "0.0.0.0"},
        raw_lines=raw_lines,
    )

    assert env_path.read_text(encoding="utf-8") == (
        "DEBUG = false\n" "\n" "SERVER_HOST = 0.0.0.0\n"
    )


def test_parse_dotenv_missing_file_returns_empty(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    values, raw_lines = parse_dotenv(env_path)

    assert values == {}
    assert raw_lines == []
