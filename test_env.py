from dotenv import load_dotenv, find_dotenv
import os

print('find_dotenv:', find_dotenv())
load_dotenv(find_dotenv())
print("DEBUG:", os.getenv("OPENAI_API_KEY"))

