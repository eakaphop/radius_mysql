"""Send RFC 5176 Disconnect / CoA requests to a NAS through `radclient`.

- Runs via asyncio.create_subprocess_exec (never a shell).
- The shared secret is passed with `-S <file>` (a 0600 temp file, removed right
  after) rather than on the command line, where any local user could read it
  from the process list — see docs/decisions.md.
- Attribute values are always double-quoted and escaped; values containing
  line breaks are rejected so they can't inject extra attributes.
"""

import asyncio
import ipaddress
import os
import re
import tempfile
from dataclasses import dataclass
from typing import Literal

DynAuthCommand = Literal["disconnect", "coa"]

_RECEIVED = re.compile(r"Received (Disconnect-ACK|Disconnect-NAK|CoA-ACK|CoA-NAK)")
_ERROR_CAUSE = re.compile(r"Error-Cause\s*=\s*(.+)")


class InvalidAttributeValueError(ValueError):
    pass


@dataclass(frozen=True)
class DynAuthResult:
    success: bool
    response: str | None
    error_cause: str | None
    detail: str


def quote_value(value: str) -> str:
    if any(char in value for char in ("\r", "\n", "\0")):
        raise InvalidAttributeValueError("attribute values must not contain line breaks")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_request_body(attributes: list[tuple[str, str]]) -> str:
    return "".join(f"{name} = {quote_value(value)}\n" for name, value in attributes)


def parse_radclient_output(output: str) -> DynAuthResult:
    received = _RECEIVED.search(output)
    if received is None:
        return DynAuthResult(
            success=False, response=None, error_cause=None, detail="No response from NAS"
        )
    response = received.group(1)
    cause_match = _ERROR_CAUSE.search(output)
    error_cause = cause_match.group(1).strip() if cause_match else None
    success = response.endswith("-ACK")
    detail = response if success or error_cause is None else f"{response}: {error_cause}"
    return DynAuthResult(
        success=success, response=response, error_cause=error_cause, detail=detail
    )


async def send_dynauth(
    *,
    radclient_path: str,
    nas_ip: str,
    port: int,
    secret: str,
    command: DynAuthCommand,
    attributes: list[tuple[str, str]],
    timeout_sec: int,
) -> DynAuthResult:
    # Validating the address also guarantees it can't be parsed as an option.
    ipaddress.ip_address(nas_ip)
    body = build_request_body(attributes)

    fd, secret_path = tempfile.mkstemp(prefix="radclient-")
    try:
        with os.fdopen(fd, "w") as secret_file:
            secret_file.write(secret)

        try:
            process = await asyncio.create_subprocess_exec(
                radclient_path,
                "-x",
                "-r",
                "1",
                "-t",
                str(timeout_sec),
                "-S",
                secret_path,
                f"{nas_ip}:{port}",
                command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except FileNotFoundError:
            return DynAuthResult(
                success=False,
                response=None,
                error_cause=None,
                detail=f"radclient not found at {radclient_path}",
            )

        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(body.encode("utf-8")), timeout=timeout_sec + 2
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            return DynAuthResult(
                success=False, response=None, error_cause=None, detail="Timed out waiting for NAS"
            )
    finally:
        os.unlink(secret_path)

    return parse_radclient_output(stdout.decode("utf-8", errors="replace"))
