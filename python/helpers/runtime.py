import argparse
import inspect
import secrets
import socket
from pathlib import Path
from typing import TypeVar, Callable, Awaitable, Union, overload, cast
from python.helpers import dotenv, rfc, settings, files
import asyncio
import threading
import queue
import sys

T = TypeVar("T")
R = TypeVar("R")

parser = argparse.ArgumentParser()
args = {}
dockerman = None
runtime_id = None


def initialize():
    global args
    if args:
        return
    parser.add_argument("--port", type=int, default=None, help="Web UI port")
    parser.add_argument("--host", type=str, default=None, help="Web UI host")
    parser.add_argument(
        "--cloudflare_tunnel",
        type=bool,
        default=False,
        help="Use cloudflare tunnel for public URL",
    )
    parser.add_argument(
        "--development", type=bool, default=False, help="Development mode"
    )

    known, unknown = parser.parse_known_args()
    args = vars(known)
    for arg in unknown:
        if "=" in arg:
            key, value = arg.split("=", 1)
            key = key.lstrip("-")
            args[key] = value


def get_arg(name: str):
    global args
    return args.get(name, None)


def has_arg(name: str):
    global args
    return name in args


def is_dockerized() -> bool:
    return bool(get_arg("dockerized"))


def is_development() -> bool:
    return not is_dockerized()


def get_local_url():
    if is_dockerized():
        return "host.docker.internal"
    return "127.0.0.1"


def get_runtime_id() -> str:
    global runtime_id
    if not runtime_id:
        runtime_id = secrets.token_hex(8)
    return runtime_id


def get_persistent_id() -> str:
    id = dotenv.get_dotenv_value("A0_PERSISTENT_RUNTIME_ID")
    if not id:
        id = secrets.token_hex(16)
        dotenv.save_dotenv_value("A0_PERSISTENT_RUNTIME_ID", id)
    return id


@overload
async def call_development_function(
    func: Callable[..., Awaitable[T]], *args, **kwargs
) -> T: ...


@overload
async def call_development_function(func: Callable[..., T], *args, **kwargs) -> T: ...


async def call_development_function(
    func: Union[Callable[..., T], Callable[..., Awaitable[T]]], *args, **kwargs
) -> T:
    if is_development():
        url = _get_rfc_url()
        password = _get_rfc_password()
        # Normalize path components to build a valid Python module path across OSes
        module_path = Path(
            files.deabsolute_path(func.__code__.co_filename)
        ).with_suffix("")
        module = ".".join(module_path.parts)  # __module__ is not reliable
        result = await rfc.call_rfc(
            url=url,
            password=password,
            module=module,
            function_name=func.__name__,
            args=list(args),
            kwargs=kwargs,
        )
        return cast(T, result)
    else:
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)  # type: ignore


async def handle_rfc(rfc_call: rfc.RFCCall):
    return await rfc.handle_rfc(rfc_call=rfc_call, password=_get_rfc_password())


def _get_rfc_password() -> str:
    password = dotenv.get_dotenv_value(dotenv.KEY_RFC_PASSWORD)
    if not password:
        raise Exception("No RFC password, cannot handle RFC calls.")
    return password


def _get_rfc_url() -> str:
    set = settings.get_settings()
    url = set["rfc_url"]
    if not "://" in url:
        url = "http://" + url
    if url.endswith("/"):
        url = url[:-1]
    url = url + ":" + str(set["rfc_port_http"])
    url += "/rfc"
    return url


def call_development_function_sync(
    func: Union[Callable[..., T], Callable[..., Awaitable[T]]], *args, **kwargs
) -> T:
    # run async function in sync manner
    result_queue = queue.Queue()

    def run_in_thread():
        result = asyncio.run(call_development_function(func, *args, **kwargs))
        result_queue.put(result)

    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join(timeout=30)  # wait for thread with timeout

    if thread.is_alive():
        raise TimeoutError("Function call timed out after 30 seconds")

    result = result_queue.get_nowait()
    return cast(T, result)


def get_web_ui_port():
    web_ui_port = (
        get_arg("port") or int(dotenv.get_dotenv_value("WEB_UI_PORT", 0)) or 5000
    )
    return web_ui_port


def get_tunnel_api_port():
    tunnel_api_port = (
        get_arg("tunnel_api_port")
        or int(dotenv.get_dotenv_value("TUNNEL_API_PORT", 0))
        or 55520
    )
    return tunnel_api_port


def get_platform():
    return sys.platform


def is_windows():
    return get_platform() == "win32"


def get_terminal_executable():
    if is_windows():
        return "powershell.exe"
    else:
        return "/bin/bash"


def find_available_port(start_port: int = 5000, max_attempts: int = 100) -> int:
    """
    Find an available port starting from start_port.
    Implements port conflict resolution with automatic fallback.

    Args:
        start_port: Starting port to check (default: 5000)
        max_attempts: Maximum number of ports to try (default: 100)

    Returns:
        Available port number

    Raises:
        RuntimeError: If no available port is found after max_attempts
    """
    for port in range(start_port, start_port + max_attempts):
        if is_port_available(port):
            return port
    raise RuntimeError(
        f"No available port found in range {start_port}-{start_port + max_attempts}"
    )


def is_port_available(port: int) -> bool:
    """
    Check if a port is available for binding.

    Args:
        port: Port number to check

    Returns:
        True if port is available, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", port))
            return True
    except OSError:
        return False


def get_web_ui_port_with_fallback() -> int:
    """
    Get web UI port with automatic conflict resolution.
    Falls back to next available port if default is in use.

    Returns:
        Available port number
    """
    preferred_port = get_web_ui_port()

    # If preferred port is available, use it
    if is_port_available(preferred_port):
        return preferred_port

    # Try to find an available port starting from preferred
    from python.helpers.print_style import PrintStyle

    PrintStyle(font_color="yellow").print(
        f"Port {preferred_port} is in use, searching for available port..."
    )

    available_port = find_available_port(preferred_port)
    PrintStyle(font_color="green").print(f"Using available port: {available_port}")

    return available_port


def get_tunnel_api_port_with_fallback() -> int:
    """
    Get tunnel API port with automatic conflict resolution.
    Falls back to next available port if default is in use.

    Returns:
        Available port number
    """
    preferred_port = get_tunnel_api_port()

    if is_port_available(preferred_port):
        return preferred_port

    from python.helpers.print_style import PrintStyle

    PrintStyle(font_color="yellow").print(
        f"Tunnel API port {preferred_port} is in use, searching for available port..."
    )

    available_port = find_available_port(preferred_port)
    PrintStyle(font_color="green").print(
        f"Using available tunnel API port: {available_port}"
    )

    return available_port
