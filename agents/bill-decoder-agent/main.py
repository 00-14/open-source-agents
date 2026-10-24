"""
bill-decoder-agent
Explains any Indian utility bill (electricity, water, mobile, broadband)
in simple language and flags charges that look unusual.

Usage:
    python main.py path/to/bill.jpg
    python main.py path/to/bill.pdf --lang kannada
"""

import argparse
import mimetypes
import os
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from guardrails import INJECTION_RULE, check_file

PROMPT = """You are a friendly assistant that explains Indian utility bills
(electricity, water, gas, mobile, broadband) to ordinary people.

Look at the attached bill and reply in {language}, using simple words.
Use exactly these sections:

1. BILL SUMMARY
   - Type of bill and provider
   - Billing period
   - Total amount to pay and the due date

2. CHARGES EXPLAINED
   - List every charge on the bill with its amount and a one-line,
     plain-language explanation of what it is for.

3. RED FLAGS
   - Point out anything unusual: late fees, arrears from earlier bills,
     sudden jump in usage compared with previous months (if shown),
     estimated (not actual) meter readings, unknown or extra charges,
     or calculation mistakes.
   - If nothing looks wrong, say "No red flags found."

4. MONEY-SAVING TIPS
   - Give 2 or 3 practical tips specific to this type of bill.

Rules:
- Only use information that is actually printed on the bill.
- If something is unclear or unreadable, say so instead of guessing.
- If the file is not a bill, say so and stop.
""" + INJECTION_RULE


def decode_bill(file_path: str, language: str) -> str:
    """Send the bill to Gemini and return the explanation text."""
    mime_type, _ = mimetypes.guess_type(file_path)
    problem = check_file(mime_type, os.path.getsize(file_path))
    if problem:
        raise ValueError(problem)

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    return decode_bill_bytes(file_bytes, mime_type, language)


def decode_bill_bytes(file_bytes: bytes, mime_type: str, language: str) -> str:
    """Send raw bill bytes (e.g. from a web upload) to Gemini."""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=os.getenv("MODEL_NAME", "gemini-3.5-flash"),
        contents=[
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            PROMPT.format(language=language),
        ],
    )
    return response.text


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Explain an Indian utility bill in simple language."
    )
    parser.add_argument("bill", help="Path to the bill photo or PDF")
    parser.add_argument(
        "--lang",
        default="English",
        help="Language for the explanation, e.g. English, Kannada, Hindi (default: English)",
    )
    args = parser.parse_args()

    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        sys.exit("Error: GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")

    if not os.path.isfile(args.bill):
        sys.exit(f"Error: file not found: {args.bill}")

    print(f"Decoding {args.bill} ...\n")
    try:
        print(decode_bill(args.bill, args.lang))
    except ValueError as e:
        sys.exit(f"Error: {e}")
    except errors.APIError as e:
        if e.code == 503:
            sys.exit("Error: the Gemini model is busy right now. Wait a minute and try again.")
        sys.exit(f"Error from Gemini API ({e.code}): {e.message}")


if __name__ == "__main__":
    main()
