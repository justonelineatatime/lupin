import json
import logging
import os
from typing import List
import streamlit as st

from google.oauth2 import service_account

# Logging
logger = logging.getLogger('SOFT BAN')
logger.setLevel(logging.INFO)

_SCOPES = ['https://www.googleapis.com/auth/bigquery','https://www.googleapis.com/auth/devstorage.read_write']
_PROJECT = 'immortal-data'
config = None


def read_section_envvar(config:dict, envvar:str):
    fragments = list(map(lambda x: x.lower(),envvar.split('_')))
    if len(fragments) >= 2:
        section = fragments[0]
        parameter = '_'.join(fragments[1:])
        if envvar in os.environ:
            if section in config:
                config[section][parameter] = os.getenv(envvar)
            else:
                config[section] = dict()
                config[section][parameter] = os.getenv(envvar)
    return config


def read_section_envvars(config:dict, envvars: List[str]):
    for envvar in envvars:
        config = read_section_envvar(config,envvar)
    return config


def read_config():
    current_dir = os.path.dirname(__file__)
    global config
    if config is not None:
        return config
    else:
        config = dict()
        try:
            with open(os.path.join(current_dir, 'config.json')) as f:
                config = json.load(f)
        except Exception:
            logger.info('no main config found file')
        config = read_section_envvars(config,
                                     ['ENV', 
                                      'DB_CONNECTION_STRING',
                                      'BIGQUERY_CREDENTIALS_FILE',
                                      'MONGODB_CONNECTION_STRING'])

    return config


class GoogleAuthHelper:
    """Helper class for authentication to Google Cloud"""

    @staticmethod
    def get_project():
        return _PROJECT

    @staticmethod
    def get_credentials():
        credentials = credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
        return credentials
