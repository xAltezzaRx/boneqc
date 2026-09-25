from __future__ import annotations

import asyncio
import os


LISTEN_HOST = os.environ.get(
    "BONEQC_C7_BRIDGE_LISTEN_HOST",
    "127.0.0.1",
)

LISTEN_PORT = int(
    os.environ.get(
        "BONEQC_C7_BRIDGE_LISTEN_PORT",
        "19081",
    )
)

TARGET_HOST = os.environ.get(
    "BONEQC_C7_BRIDGE_TARGET_HOST",
    "127.0.0.1",
)

TARGET_PORT = int(
    os.environ.get(
        "BONEQC_C7_BRIDGE_TARGET_PORT",
        "19080",
    )
)


async def copy_stream(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    try:
        while True:
            data = await reader.read(65536)

            if not data:
                break

            writer.write(data)
            await writer.drain()

    except (
        ConnectionError,
        asyncio.CancelledError,
    ):
        pass


async def handle_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
) -> None:
    try:
        target_reader, target_writer = (
            await asyncio.open_connection(
                TARGET_HOST,
                TARGET_PORT,
            )
        )

    except Exception:
        client_writer.close()
        await client_writer.wait_closed()
        return

    try:
        await asyncio.gather(
            copy_stream(
                client_reader,
                target_writer,
            ),
            copy_stream(
                target_reader,
                client_writer,
            ),
        )

    finally:
        target_writer.close()
        client_writer.close()

        await asyncio.gather(
            target_writer.wait_closed(),
            client_writer.wait_closed(),
            return_exceptions=True,
        )


async def main() -> None:
    server = await asyncio.start_server(
        handle_client,
        LISTEN_HOST,
        LISTEN_PORT,
    )

    addresses = ", ".join(
        str(sock.getsockname())
        for sock in server.sockets or []
    )

    print(
        f"BONEQC_C7_BRIDGE_LISTEN={addresses}",
        flush=True,
    )

    print(
        "BONEQC_C7_BRIDGE_TARGET="
        f"{TARGET_HOST}:{TARGET_PORT}",
        flush=True,
    )

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
