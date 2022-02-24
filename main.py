import os
from dotenv import load_dotenv
from ghapi.all import GhApi
from loguru import logger
from base64 import b64encode
from nacl import encoding, public
from argparse import ArgumentParser
import base64
# Load GIT HUB CREDENTIALS
load_dotenv("./git.env")
GITHUB_ACCESS_TOKEN = os.getenv('GITHUB_ACCESS_TOKEN')
GITHUB_REPO_OWNER = os.getenv('GITHUB_REPO_OWNER')
GITHUB_REPO = os.getenv('GITHUB_REPO')
ENVIRONMENT = os.getenv('ENVIRONMENT')

# Parse command line arguments
parser = ArgumentParser()

parser.add_argument("--base64", nargs='+',
                    help="Base64 encode secrets", metavar="key")

args = parser.parse_args()
base64_keys = args.base64 if args.base64 is not None else []

api = GhApi(owner=GITHUB_REPO_OWNER, repo=GITHUB_REPO, token=GITHUB_ACCESS_TOKEN)

# Function to encrypt our secret
def encrypt(public_key: str, secret_value: str) -> str:
    """Encrypt a Unicode string using the public key."""
    public_key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")

# Parse env file and convert data to dict
def get_env_data_as_dict(path: str) -> dict:
    logger.info(f'Loading "{env_file_path}" to populate "{ENVIRONMENT}" environment')
    with open(path, 'r') as f:
       return dict(tuple(line.replace('\n', '').split('=')) for line
                in f.readlines() if not line.startswith('#'))

# Function to Base64 encode string
def base64_encode(value:str)-> str:
    value_bytes = value.encode('ascii')
    base64_bytes = base64.b64encode(value_bytes)
    return base64_bytes.decode('ascii')

# LOAD ENV FILE
env_file_switch={
                "DEV":'./dev.env',
                "PROD":'./prod.env',
                "REPO":'./repo.env',
}

env_file_path = env_file_switch[ENVIRONMENT]

env_data = get_env_data_as_dict(env_file_path)
# Get a set of keys present in the env file
env_keys_set = set(env_data.keys())

if ENVIRONMENT != "REPO":
    logger.info(f'Fetching repository information for :: {GITHUB_REPO}')
    repoId = api.repos.get().id
    #(repository_id, environment_name, per_page, page)
    github_env_secrets = api.actions.list_environment_secrets(repoId,ENVIRONMENT,1000,0)
    github_env_secrets_keys_set = set([x.name for x in github_env_secrets.secrets])
    #Getting asymmetric difference ignoring order
    secrets_diff = github_env_secrets_keys_set - env_keys_set
    logger.info(f'Performing secrets cleanup for environment :: {ENVIRONMENT}')
    for key in secrets_diff:
        logger.info(f'Removing secret `{key}` from `{ENVIRONMENT}` in GitHub')
        api.actions.delete_environment_secret(repoId, ENVIRONMENT, key)
    logger.info(f'Creating/Updating new environment :: {ENVIRONMENT}')
    api.repos.create_or_update_environment(ENVIRONMENT)
    logger.info(f'Created/Updated environment :: {ENVIRONMENT}')

    logger.info(f'Fetching environment public key for :: {ENVIRONMENT}')
    public_key= api.actions.get_environment_public_key(repoId, ENVIRONMENT)
    for key,value in env_data.items(): 
        if key in base64_keys:
            logger.info(f'Base64 encoding secret :: {key}')
            value=base64_encode(value)
        encrypted_value=encrypt(public_key.key,value)
        logger.info(f'Adding environment secret `{key}` for :: {ENVIRONMENT}')
        api.actions.create_or_update_environment_secret(repoId, ENVIRONMENT, key, encrypted_value, public_key.key_id)
        logger.info(f'Successfully added environment secret `{key}` for {ENVIRONMENT}')
else:
    logger.info(f'Performing secrets cleanup for repository :: {GITHUB_REPO}')
    repo_secrets= api.actions.list_repo_secrets(1000,0)
    repo_secrets_keys_set = set([x.name for x in repo_secrets.secrets])
    #Getting asymmetric difference ignoring order
    secrets_diff = repo_secrets_keys_set - env_keys_set

    for key in secrets_diff:
        logger.info(f'Removing secret `{key}` from `{GITHUB_REPO}` repository in GitHub')
        api.actions.delete_repo_secret(key)
    logger.info(f'Adding repository secrets')
    public_key=api.actions.get_repo_public_key()

    for key,value in env_data.items(): 
        if key in base64_keys:
            logger.info(f'Base64 encoding secret :: {key}')
            value=base64_encode(value)
        encrypted_value=encrypt(public_key.key,value)
        logger.info(f'Adding repository secret :: {key}')
        api.actions.create_or_update_repo_secret(key, encrypted_value, public_key.key_id)    
        logger.info(f'Successfully added repository secret :: {key}')