#!/usr/bin/env python3

import argparse
import os
import re
import sys

from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException


load_dotenv()


def required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        print(f"[!] Missing environment variable: {name}")
        sys.exit(1)

    return value


ACCOUNT_SID = required_env("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = required_env("TWILIO_AUTH_TOKEN")
FROM_NUMBER = required_env("TWILIO_FROM_NUMBER")


def validate_number(number: str) -> str:
    """
    Basic E.164 validation.

    Examples:
        +14165551234
        +923059347133
    """

    if not re.fullmatch(r"\+[1-9]\d{7,14}", number):
        raise ValueError(
            "Phone number must use E.164 format, "
            "for example +923059347133"
        )

    return number


def send_sms(number: str, message: str):
    number = validate_number(number)

    if not message.strip():
        raise ValueError("Message cannot be empty.")

    client = Client(
        ACCOUNT_SID,
        AUTH_TOKEN
    )

    print("[*] Sending SMS...")
    print(f"[*] Destination: {number}")

    try:
        result = client.messages.create(
            body=message,
            from_=FROM_NUMBER,
            to=number
        )

    except TwilioRestException as exc:
        print("[!] SMS provider rejected the request.")
        print(f"[!] {exc}")
        sys.exit(1)

    print()
    print("╔══════════════════════════════════════╗")
    print("║             SMS SENT                 ║")
    print("╚══════════════════════════════════════╝")
    print(f"Message SID : {result.sid}")
    print(f"Status      : {result.status}")
    print(f"To          : {result.to}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="sms",
        description="SMS command-line sender"
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True
    )

    send = sub.add_parser(
        "send",
        help="Send an SMS"
    )

    send.add_argument(
        "text",
        nargs="+",
        help="Message text"
    )

    send.add_argument(
        "-number",
        "--number",
        required=True,
        help="Destination phone number in E.164 format"
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "send":
        message = " ".join(args.text)

        try:
            send_sms(
                number=args.number,
                message=message
            )

        except ValueError as exc:
            print(f"[!] {exc}")
            sys.exit(1)


if __name__ == "__main__":
    main()
