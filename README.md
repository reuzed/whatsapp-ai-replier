## WhatsApp Controls — Auto‑signup For Tennis Groupchats

Automate sign‑ups in Lypta Tennis WhatsApp groupchats by watching a numbered list and inserting your name automatically.
To use this, do the setup in advance, then leave the auto signup program running while waiting for the signups to open.
This is intended for Linux.

## Requirements
- Python 3.9+
- Google Chrome and a matching ChromeDriver

You will need to log onto WhatsappWeb on the first use, and may need to (rather quickly) click 'continue'. Just retry if you encounter issues on first use, and if that doesn't work, you can let me know.

## Install
```bash
git clone https://github.com/MJ141592/WhatsappControls.git
cd WhatsappControls
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run auto‑signup
```bash
python auto_signup.py "Group Chat Name" --my-name "Your Name"
```
- The script polls the group. When it sees a numbered list like:
  1) Bob\n2) Alice\n3) \n...
  it inserts your name into the first empty slot, preserves any header/footer text, and sends the updated list.

## Notes
- The script uses a local `./whatsapp_profile` directory by default and will create it if missing. Log in to WhatsApp Web when Chrome opens the first time.
- ChromeDriver must be installed and compatible with your Chrome version (the code expects it at `/usr/bin/chromedriver`).

## Whatsapp Controls - Automated LLM answers (optional, not required for tennis signups)

Make a .env file in the WhatsappControls directory. See .env.example for an example. Add these variables:
```bash
# The display name to insert into signup lists, and as context for LLM generated messages
SIGNUP_MY_NAME=Your Name

# For LLM-powered replies in the scripts below
ANTHROPIC_API_KEY=...
```

- Live auto‑reply to new messages in a chat:
```bash
python live_reply.py "Chat Name"
```
- Reply to recent unanswered messages since your last message in a chat:
```bash
python reply_unanswered.py "Chat Name"
```