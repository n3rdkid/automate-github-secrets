import os
from dotenv import load_dotenv

load_dotenv("./git.env")

GITHUB_ACCESS_TOKEN = os.getenv('GITHUB_ACCESS_TOKEN')
