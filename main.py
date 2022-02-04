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
# LOAD ENV FILE
env_file_switch={
                "DEV":'./dev.env.json',
                "PROD":'./prod.env.json',
                "REPO":'./repo.env.json',
}

env_file_path = env_file_switch[ENVIRONMENT]
logger.info(f'Loading "{env_file_path}" to populate "{ENVIRONMENT}" environment')
env_file = open(env_file_path)
data = json.load(env_file)

# CREATE API
api = GhApi(owner=GITHUB_REPO_OWNER, repo=GITHUB_REPO, token=GITHUB_ACCESS_TOKEN)

# logger.info(api.__dict__.values())
def encrypt(public_key: str, secret_value: str) -> str:
    """Encrypt a Unicode string using the public key."""
    public_key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")


if ENVIRONMENT != "REPO":
    env_exists = False
    logger.info(f'Fetching repository information for {GITHUB_REPO}')
    """
    Repository id is required for public key generation
    """
    repoId = api.repos.get().id
    environments_response = api.repos.get_all_environments()
    if(environments_response.total_count > 0):
        for env in environments_response.environments:
            if( env.name == ENVIRONMENT ):
                env_exists=True
        msg = "exists" if env_exists else "doesn't exist"
        logger.info(f'{ENVIRONMENT} {msg}.')
    else:
        logger.info(f'Creating new environment {ENVIRONMENT}')
        api.repos.create_or_update_environment(ENVIRONMENT)
        logger.info(f'Created environment {ENVIRONMENT}')
    
    logger.info(f'Fetching environment public key for {ENVIRONMENT}')
    public_key= api.actions.get_environment_public_key(repoId, ENVIRONMENT)
    #api.actions.create_or_update_environment_secret(repository_id, environment_name, secret_name, encrypted_value: str = None, key_id: str = None)
    for key in data.keys(): 
        encrypted_value=encrypt(public_key.key,data[key])
        api.actions.create_or_update_environment_secret(repoId, ENVIRONMENT, key, encrypted_value, public_key.key_id)
else:
    logger.info(f'Adding repository secrets')
    #api.actions.get_repo_public_key()
    #api.actions.create_or_update_repo_secret(secret_name, encrypted_value: str = None, key_id: str = None)
    
    
