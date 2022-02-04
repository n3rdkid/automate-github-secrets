from mimetypes import init
import os
import json
from dotenv import load_dotenv
from ghapi.all import GhApi
from loguru import logger
from base64 import b64encode
from nacl import encoding, public

# Load GIT HUB CREDENTIALS
load_dotenv("./git.env")
GITHUB_ACCESS_TOKEN = os.getenv('GITHUB_ACCESS_TOKEN')
GITHUB_REPO_OWNER = os.getenv('GITHUB_REPO_OWNER')
GITHUB_REPO = os.getenv('GITHUB_REPO')
ENVIRONMENT = os.getenv('ENVIRONMENT')

def encrypt(public_key: str, secret_value: str) -> str:
    """Encrypt a Unicode string using the public key."""
    public_key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")


def get_env_data_as_dict(path: str) -> dict:
    logger.info(f'Loading "{env_file_path}" to populate "{ENVIRONMENT}" environment')

    with open(path, 'r') as f:
       return dict(tuple(line.replace('\n', '').split('=')) for line
                in f.readlines() if not line.startswith('#'))


# LOAD ENV FILE
env_file_switch={
                "DEV":'./dev.env',
                "PROD":'./prod.env',
                "REPO":'./repo.env',
}

env_file_path = env_file_switch[ENVIRONMENT]

env_data = get_env_data_as_dict(env_file_path)
# CREATE API
api = GhApi(owner=GITHUB_REPO_OWNER, repo=GITHUB_REPO, token=GITHUB_ACCESS_TOKEN)

if ENVIRONMENT != "REPO":
    logger.info(f'Fetching repository information for {GITHUB_REPO}')
    """
    Repository id is required for public key generation
    """
    repoId = api.repos.get().id
    # env_exists = False
    # environments_response = api.repos.get_all_environments()
    # if(environments_response.total_count > 0):
    #     for env in environments_response.environments:
    #         if( env.name == ENVIRONMENT ):
    #             env_exists=True
    #     msg = "exists" if env_exists else "doesn't exist"
    #     logger.info(f'{ENVIRONMENT} {msg}.')
    # else:
    logger.info(f'Creating/Updating new environment {ENVIRONMENT}')
    api.repos.create_or_update_environment(ENVIRONMENT)
    logger.info(f'Created/Updated environment {ENVIRONMENT}')

    logger.info(f'Fetching environment public key for {ENVIRONMENT}')
    public_key= api.actions.get_environment_public_key(repoId, ENVIRONMENT)
    for key,value in env_data.items(): 
        encrypted_value=encrypt(public_key.key,value)
        logger.info(f'Adding environment secret {key} for {ENVIRONMENT}')
        api.actions.create_or_update_environment_secret(repoId, ENVIRONMENT, key, encrypted_value, public_key.key_id)
        logger.info(f'Successfully added environment secret {key} for {ENVIRONMENT}')
else:
    logger.info(f'Adding repository secrets')
    public_key=api.actions.get_repo_public_key()
    for key,value in env_data.items(): 
        encrypted_value=encrypt(public_key.key,value)
        logger.info(f'Adding repository secret {key}')
        api.actions.create_or_update_repo_secret(key, encrypted_value, public_key.key_id)    
        logger.info(f'Successfully added repository secret {key}')

