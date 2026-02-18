from aria.config import get_required_env


class Server:
    host = get_required_env("SERVER_HOST")
    port = int(get_required_env("SERVER_PORT"))

    base_url = f"http://{host}:{port}/"
