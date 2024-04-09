# LUPIN

## A Streamlit-Powered Exploration Tool for Online Chess Games

### Overview:
Lupin offers an immersive experience for users looking to dive deep into the strategies and games of online chess enthusiasts across platforms such as Lichess and Immortal Game. Built entirely on Streamlit, Lupin leverages the extensive dataset available through Immortal Game's public BigQuery and taps into the rich features of Lichess's open API to bring a comprehensive analysis and exploration tool to your fingertips.

### Features:
- User exploration: Get aggregated data on users of Lichess and Immortal Game
- Game Exploration: Discover and analyze games from a wide range of players on Lichess and Immortal Game.

### Get Involved:
Lupin is a dynamic project open to contributions and extensions. Whether you're looking to improve functionality, add new features, or simply explore the code, we welcome forks and contributions from the community.
Dive into the world of online chess like never before. Explore, analyze, and contribute to Lupin today!
This version aims to be clear and inviting, highlighting the main features and encouraging community involvement.

---
## Getting Started
This repo uses **poetry** to manage packages.

Let's get poetry install following the official documentation : [poetry installation](https://python-poetry.org/docs/)

Once installed, at the root of the repo run:
```bash
poetry install
poetry shell
```
Those commands install and activate the environnement.

We get Immortal Game data from BigQuery public dataset, thus we need to provide a service account. 
Once cloned you can create a folder `.streamlit` at the root of the repository. Within this folder create a file `secrets.toml`.
Don't forget to add this file to your `.gitignore`. In this file you need to add the flatten service account json that has the authorization to query tables on BigQuery.
The file `secrets.toml` will look like this:

```toml
[gcp_service_account]
type = "service_account"
project_id = "immortal-data"
private_key_id = "xxxxxxxxxxxxxxxxx"
private_key = "xxxxxxxxxxxxxx"
client_email = "xxxxxxxxxxxxxxx"
client_id = "xxxxxxxxxxxxxx"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "xxxxxxxxxxxxxxxx"
universe_domain = "googleapis.com"
```

The entry point of the app is the file `Platform_Selection.py`, to launch the app run:
```bash
poetry run streamlit run Platform_Selection.py
```

You will be able to find the app on your localhost.

### How the repository is structured
The main page `Platform_Selection.py` allows the user to select the platform between Lichess and Immortal Game.

In Streamlit, when you want to create a multipage app, you need to create new files within the folder: `pages`

In our case, we are providing two pages:

- User report: Allows querying for aggregated user information
- Game Navigator: Allows going through a game and analyzing it

Two Streamlit concepts that we are using a lot in this app are:
- session state: a tool provided by Streamlit to store variables across the app
- cache_data: a wrapper that allows us to indicate whether a function needs to be rerun every time or stored in cache



