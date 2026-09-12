"""
llm_client.py
-------------
Shared helper for talking to Groq's AI models.

Everyone on the team uses the SAME function from here, so we only have to
set up the API key in one place.

    from utils.llm_client import ask_ai
    answer = ask_ai("Explain why a ship going dark is suspicious.")

Why Groq: it runs open models (Llama) on very fast hardware and has a
generous free tier, so we get near-instant replies during the demo.
"""

import os

from dotenv import load_dotenv
from groq import Groq

# Read the .env file sitting in the project root and copy its values into
# the environment. Safe to call more than once.
load_dotenv()

# Which model we ask for on Groq.
# openai/gpt-oss-120b is highly capable and fast for our alert explanations.
MODEL_NAME = "openai/gpt-oss-120b"


def ask_ai(prompt: str) -> str:
    """
    Send a prompt to Groq and return its answer as plain text.

    Input:  prompt -> a string, e.g. "Summarise this in one sentence: ..."
    Output: a string, the model's reply.

    Raises ValueError if the API key is missing, so a misconfigured .env is
    impossible to miss. Callers that must never crash (like the dark-vessel
    agent) wrap this in a try/except and supply their own fallback wording.
    """

    # Step 1: get the API key out of the environment (.env file).
    api_key = os.getenv("GROQ_API_KEY")

    # Step 2: if there is no key, stop with a message that actually tells the
    # reader how to fix it.
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not set.\n"
            "Fix: open the .env file in the project root and add the line:\n"
            "    GROQ_API_KEY=your_key_here\n"
            "Get a free key at https://console.groq.com/keys"
        )

    # Step 3: create the Groq client using that key.
    client = Groq(api_key=api_key)

    # Step 4: send our question as a chat message and get the reply.
    # "messages" is a conversation; we only ever send one turn from the user.
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
    )

    # Step 5: dig the text out of the response and trim stray whitespace.
    return completion.choices[0].message.content.strip()
