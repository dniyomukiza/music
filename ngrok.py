from dotenv import load_dotenv
import os
from langchain_xai import ChatXAI

# Load environment variables from a .env file
load_dotenv()

# Retrieve the GROK_API key
grok_api_key = os.getenv("GROK_API")
if not grok_api_key:
    raise ValueError("GROK_API environment variable is not set in the .env file.")

# Initialize the ChatXAI client
chat = ChatXAI(
    xai_api_key=grok_api_key,
    model="grok-beta",
)

# Stream the response back from the model
for m in chat.stream("Tell me fun things to do in NYC"):
    print(m.content, end="", flush=True)
