# sms-tool

A clean CLI for sending SMS via Twilio. No hidden bullshit — just a terminal command that hits a legitimate SMS API and shows you the delivery result.

## Setup

```bash
mkdir sms-tool
cd sms-tool

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your Twilio credentials:

```bash
cp .env.example .env
```

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_FROM_NUMBER=+1XXXXXXXXXX
```

**Never commit `.env` to version control.**

Make the script executable:

```bash
chmod +x sms.py
```

## Usage

```bash
./sms.py send -number +923059347133 "Hello from the terminal"

./sms.py send --number +14165551234 "Fuck yeah, message sent."

./sms.py send \
  -number +923059347133 \
  "Longer message goes here."
```

## Notes

- Phone numbers must be in E.164 format (e.g. `+923059347133`)
- Twilio may require destination number verification depending on your account tier/region
- Get a Twilio account and sender number at https://twilio.com
