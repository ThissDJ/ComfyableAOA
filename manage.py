#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import subprocess  # Uncomment this line


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "comfyableAOA.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    # Check if the flag is set before running subprocess
    # if "RUN_ONCE_FLAG" not in os.environ:
    #     print("Running preflight scripts...")
    #     os.environ[
    #         "RUN_ONCE_FLAG"
    #     ] = "1"  # Set the flag to indicate that the subprocess has been called
    #     subprocess.Popen(["python3", "./cron.py"])

    main()
