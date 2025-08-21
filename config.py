from os import getenv
from dotenv import load_dotenv

load_dotenv()

token = getenv('TOKEN')

administrators = [int(id) for id in getenv('ADMINISTRATORS')[1:-1].split(',')]


CHANNEL_URL = getenv('CHANNEL_URL')
CHANNEL_ID = getenv('CHANNEL_ID')