from aria.config import get_optional_env, get_required_env


class Server:
    host = get_optional_env("SERVER_HOST", "0.0.0.0")
    port = int(get_required_env("SERVER_PORT"))

    @classmethod
    def get_base_url(cls):
        from aria.helpers.network import resolve_display_host

        display_host = resolve_display_host(cls.host)
        return f"http://{display_host}:{cls.port}/"
