"""Entry point: `python -m agent_mail_mcp` or the `agent-mail-mcp` console script."""

from .server import run


def main() -> None:
    run()


if __name__ == "__main__":
    main()
