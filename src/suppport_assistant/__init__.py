import sys


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "create-admin":
        from suppport_assistant.cli import create_admin

        create_admin()
        return

    from suppport_assistant.main import run

    run()
