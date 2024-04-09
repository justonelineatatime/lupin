import random

import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import streamlit as st
import requests as rq
import json
from io_utils import BQHelper
from datetime import datetime, timedelta


@st.cache_data
def get_historical_games_stats_per_activity_for_a_user_immortal(user_id):
    bq_client = BQHelper.init_client()

    historical_game_df = bq_client.query(
        f"""
        SELECT
            day,
            activity_category,
            nb_games,
            nb_significant_games
        FROM `immortal-data.dbt_immortal_public_data.game_users_stats_x_day`
        where day > date_sub(current_date(), interval 4 week)
            and activity_category != "All"
            and speed = "All"
            and variant = "All"
            and game_mode = "All"
            and user_id = "{user_id}"

        """
    ).to_dataframe()

    return historical_game_df


@st.cache_data(ttl=300)
def get_user_data_immortal(username):
    bq_client = BQHelper.init_client()

    df_user = bq_client.query(
        f"""
            SELECT
              users_view.username,
              users_view.user_id,
              users_view.created_at,
              users_view.is_deleted,
              users_view.is_permanent_ban,
              users_view.country_code,
              users_view.fide_title,
              users_view.rating_standard_blitz rating_blitz,
              users_view.rating_standard_bullet rating_bullet,
              users_view.rating_standard_rapid rating_rapid,
              users_view.is_stable_elo_standard_blitz,
              users_view.is_stable_elo_standard_bullet,
              users_view.is_stable_elo_standard_rapid,
            FROM `immortal-data.dbt_immortal_public_data.users_public` users_view
            WHERE LOWER(username) = LOWER("{username}")
        """
    ).to_dataframe()

    return df_user


def search_user_info_trigger(username):
    st.session_state["username_search"] = username
    st.session_state["user_retreived"] = True


def create_graph_historical_game_user(historical_game_df):
    historical_game_df = historical_game_df.sort_values(by=["day", "activity_category"])
    fig = px.area(
        historical_game_df,
        x="day",
        y="nb_games",
        color="activity_category",
        markers=True,
        title="Evolution of the Number of Games per Day per Activity Category during the last 4 weeks",
        labels={
            "Date": "Date",
            "NumberOfGames": "Number of Games",
            "activity_category": "Activity Category",
        },
    )
    st.plotly_chart(fig, use_container_width=True)


@st.cache_data(ttl=300)
def get_user_games_immortal(user_id):
    bq_client = BQHelper.init_client()

    df_user_games_info = bq_client.query(
        f"""
        with competition_info as (
          select
            competition_edition_id,
            competition_name
          from `immortal-data.dbt_immortal_public_data.competition_details_public`
        ),
        
        user_info as (
          select
            user_id,
            username
          from `immortal-data.dbt_immortal_public_data.users_public`
        )

        select
          cgu.user_id,
          username,
          cgu.game_id,
          cgu.created_at,
          cgu.status,
          cgu.speed,
          competition_info.competition_name,
          cgu.result,
        from `immortal-data.dbt_immortal_public_data.competition_game_user_public` cgu
        left join competition_info
          using(competition_edition_id)
        left join user_info
          using(user_id)
        where date(cgu.created_at) >= date_sub(current_date(), interval 4 week)
          and cgu.user_id = "{user_id}"
          and cgu.plies_count > 0
    """
    ).to_dataframe()

    if df_user_games_info.empty:
        return df_user_games_info

    df_user_games_info["created_at"] = pd.to_datetime(df_user_games_info["created_at"])
    df_user_games_info["created_at"] = df_user_games_info["created_at"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    return df_user_games_info


def get_row_and_clear_selection_user_report():
    key = st.session_state["editor_key"]
    selected_rows = st.session_state[key]["edited_rows"]
    selected_rows = [
        int(row) for row in selected_rows if selected_rows[row]["Game deep dive"]
    ]
    try:
        last_row = selected_rows[-1]
    except IndexError:
        return
    st.session_state.pop("editor_key")
    st.session_state["editor_key"] = random.randint(0, 100000)
    df = st.session_state.get("df_user_games")
    last_selected_row = df.iloc[last_row]
    st.session_state["username_game_search"] = last_selected_row["username"]
    st.session_state["game_id_game_search"] = last_selected_row["game_id"]
    st.session_state["game_deep_dive_ready_for_redirect"] = True


def content_immortal_game_user_report():
    if not st.session_state.get("username_search"):
        st.session_state["username_search"] = None

    col_expand_1, col_expand_2, col_expand_3 = st.columns([3, 3, 1])
    with col_expand_1:
        form_user = st.form(key="user_info_form")
        with form_user:
            col_username, col_button_search = st.columns([3, 1])
            with col_username:
                username_search = st.text_input("Username", value=st.session_state.get("username_search"))
            with col_button_search:
                st.write("")
                search_button = st.form_submit_button(
                    "Search",
                    use_container_width=True,
                    on_click=search_user_info_trigger,
                    kwargs=dict(username=username_search),
                )
    with col_expand_3:
        st.image(image="images/IGE-logo.png")

    if not st.session_state.get("username_search"):
        st.caption("Please enter a username")
        st.stop()

    user_data = get_user_data_immortal(st.session_state.get("username_search"))
    if user_data.empty:
        st.write("No user found")
        st.stop()

    container_first_row = st.container(border=True)
    with container_first_row:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.metric(label="Username", value=user_data["username"].iloc[0])
        with col2:
            st.metric(label="Country code", value=user_data["country_code"].iloc[0])
        with col3:
            st.metric(label="Fide Title", value=user_data["fide_title"].iloc[0])

        col9, col10, col11 = st.columns([1, 1, 1])
        with col9:
            st.metric(
                label="Rating Blitz", value=str(round(user_data["rating_blitz"].iloc[0]))
            )
        with col10:
            st.metric(
                label="Rating Bullet", value=str(round(user_data["rating_bullet"].iloc[0]))
            )
        with col11:
            st.metric(
                label="Rating Rapid", value=str(round(user_data["rating_rapid"].iloc[0]))
            )

        col12, col13, col14 = st.columns([1, 1, 1])
        with col12:
            st.metric(
                label="Elo Blitz Is Stable",
                value=user_data["is_stable_elo_standard_blitz"].iloc[0],
            )
        with col13:
            st.metric(
                label="Elo Bullet Is Stable",
                value=user_data["is_stable_elo_standard_bullet"].iloc[0],
            )
        with col14:
            st.metric(
                label="Elo Rapid Is Stable",
                value=user_data["is_stable_elo_standard_rapid"].iloc[0],
            )

    # create historical game activity
    historical_games = get_historical_games_stats_per_activity_for_a_user_immortal(user_data["user_id"].iloc[0])
    create_graph_historical_game_user(historical_games)

    # to do elo evolution

    # list games
    user_games = get_user_games_immortal(user_data["user_id"].iloc[0])
    if user_games.empty:
        st.write("No games found")
        st.stop()

    user_games["Game deep dive"] = False
    user_games = user_games.sort_values(by=["created_at", "competition_name"], ascending=[False, True])
    st.session_state["df_user_games"] = user_games
    user_games_cleaned = user_games[["Game deep dive", "created_at", "speed", "competition_name", "result"]]
    user_games_cleaned.reset_index(drop=True, inplace=True)
    st.data_editor(user_games_cleaned,
                   use_container_width=True,
                   column_config={"Game deep dive": st.column_config.CheckboxColumn(
                       "Game deep dive",
                       help="Related game, on click send you to a deep dive")},
                   disabled=["created_at", "speed", "competition_name", "result"],
                   key=st.session_state["editor_key"],
                   on_change=get_row_and_clear_selection_user_report)

    if st.session_state.get("game_deep_dive_ready_for_redirect"):
        st.session_state["game_deep_dive_ready_for_redirect"] = False
        st.switch_page("pages/2_Game_Navigator.py")


@st.cache_data(ttl=300)
def get_user_data_lichess(username):
    lichess_user_payload = rq.get(f"https://lichess.org/api/user/{username}")
    user_data_json = json.loads(lichess_user_payload.text)
    if user_data_json.get("error"):
        return {}

    return user_data_json


@st.cache_data(ttl=300)
def get_user_rating_history_lichess(username):
    lichess_user_payload = rq.get(f"https://lichess.org/api/user/{username}/rating-history")
    user_data_json = json.loads(lichess_user_payload.text)
    if not user_data_json:
        return {}

    def transform_rating_to_understandable_two_columns(rating_list):
        year = rating_list[0]
        month = rating_list[1]
        day = rating_list[2]
        rating = rating_list[3]
        date_format = f"{year}-{month}-{day}"
        try:
            date_object = datetime.strptime(date_format, "%Y-%m-%d")
        except ValueError:
            return {}
        return {"date": date_object, "rating": rating}

    dict_df_ratings = {}
    for game_mode_payload in user_data_json:
        if game_mode_payload.get("name") in ["Bullet", "Blitz", "Rapid"]:
            list_rating_points = game_mode_payload.get("points")
            df_rating_history = pd.DataFrame([transform_rating_to_understandable_two_columns(rating) for rating in list_rating_points])
            if df_rating_history.empty:
                df_rating_history = pd.DataFrame(columns=['date', 'rating'])
            dict_df_ratings[game_mode_payload.get("name")] = df_rating_history
    return dict_df_ratings


@st.cache_data(ttl=300)
def get_user_historical_graph_lichess(dict_rating_history):
    traces = []
    for key in dict_rating_history:
        traces.append(go.Scatter(x=dict_rating_history[key]['date'], y=dict_rating_history[key]['rating'], mode='lines+markers', name=key))

    # Layout configuration (optional)
    layout = go.Layout(
        title='Chess Rating Over Time',
        xaxis=dict(title='Date'),
        yaxis=dict(title='Rating'),
    )

    # Combine traces into a single plot
    fig = go.Figure(data=traces, layout=layout)

    st.plotly_chart(fig, use_container_width=True)


@st.cache_data(ttl=300)
def get_user_perf_stats_lichess(username, game_mode):
    lichess_user_payload = rq.get(f"https://lichess.org/api/user/{username}/perf/{game_mode}")
    user_data_json = json.loads(lichess_user_payload.text)
    if user_data_json.get("error"):
        return {}

    return user_data_json


@st.cache_data(ttl=300)
def get_historical_games_user_lichess(username):
    now = datetime.now()
    four_weeks_ago = now - timedelta(weeks=4)
    params = {
        'since': round(four_weeks_ago.timestamp() * 1000),
        'rated': True,
        'evals': True,
        'pgnInJson': True,
        'accuracy': True,
        'division': True,
        'literate': True,
        "perfType": "bullet,blitz,rapid"
    }
    lichess_user_payload = rq.get(f"https://lichess.org/api/games/user/{username}", params=params,
                                  headers={'Accept': 'application/x-ndjson'})
    games = lichess_user_payload.content.decode('utf-8').strip().split('\n')
    games_cleaned = [json.loads(game) for game in games]

    futur_df = []
    for game in games_cleaned:
        try:
            if not game.get("players"):
                continue

            if game.get("players").get("white").get("user").get("name").lower() == st.session_state.get("username_search").lower():
                color_opponent = "black"
            else:
                color_opponent = "white"

            if game.get("winner"):
                if game.get("players").get(game.get("winner")).get("user").get("name").lower() == st.session_state.get("username_search").lower():
                    won = "win"
                else:
                    won = "lose"
            else:
                won = game.get("status")

            futur_df.append({
                "game_id": game.get("id"),
                "username": st.session_state.get("username_search"),
                "created_at": datetime.utcfromtimestamp(int(game.get("createdAt")) / 1000).strftime('%Y-%m-%d %H:%M'),
                "rated": game.get("rated"),
                "speed": game.get("speed"),
                "result": won,
                "status": game.get("status"),
                "opponent_name": game.get("players").get(color_opponent).get("user").get("name"),
                "opponent_rating": game.get("players").get(color_opponent).get("rating")
            })
        except Exception as e:
            st.write(game)
            continue

    df_games = pd.DataFrame(futur_df)
    return df_games


@st.cache_data(ttl=300)
def get_historical_game_stats_lichess(username):
    return


@st.cache_data(ttl=300)
def get_graph_user_winrate_lichess(game_df):
    game_df["date"] = pd.to_datetime(game_df["created_at"]).dt.date
    game_df['result_numeric'] = game_df['result'].map({'win': 1, 'lose': 0})
    win_rate_df = game_df.groupby(['speed', 'date'])['result_numeric'].mean().reset_index()
    fig = px.line(win_rate_df, x='date', y='result_numeric', color='speed', markers=True,
                  title='Win Rate Evolution per Speed per Day',
                  labels={'result_numeric': 'Win Rate'})

    st.plotly_chart(fig, use_container_width=True)


def content_lichess_user_report():
    if not st.session_state.get("username_search"):
        st.session_state["username_search"] = None

    col_expand_1, col_expand_2, col_expand_3 = st.columns([3, 3, 1])
    with col_expand_1:
        form_user = st.form(key="user_info_form")
        with form_user:
            col_username, col_button_search = st.columns([3, 1])
            with col_username:
                username_search = st.text_input("Username", value=st.session_state.get("username_search"))
            with col_button_search:
                st.write("")
                search_button = st.form_submit_button(
                    "Search",
                    use_container_width=True,
                    on_click=search_user_info_trigger,
                    kwargs=dict(username=username_search),
                )
    with col_expand_3:
        st.image(image="images/lichess-logo.jpg")

    if not st.session_state.get("username_search"):
        st.caption("Please enter a username")
        st.stop()

    user_data = get_user_data_lichess(st.session_state.get("username_search"))
    if not user_data:
        st.write("No user found")
        st.stop()

    container_first_row = st.container(border=True)
    with container_first_row:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.metric(label="Username", value=user_data.get("username"))
        with col2:
            if user_data.get("profile"):
                country = user_data.get("profile").get("country")
            else:
                country = "Unknown"
            st.metric(label="Country", value=country)
        with col3:
            st.metric(label="Fide Title", value=user_data.get("title"))

        col9, col10, col11 = st.columns([1, 1, 1])
        with col9:
            st.metric(
                label="Rating Blitz", value=str(round(user_data.get("perfs").get("blitz").get("rating")))
            )
        with col10:
            st.metric(
                label="Rating Bullet", value=str(round(user_data.get("perfs").get("bullet").get("rating")))
            )
        with col11:
            st.metric(
                label="Rating Rapid", value=str(round(user_data.get("perfs").get("rapid").get("rating")))
            )

        col12, col13, col14 = st.columns([1, 1, 1])
        with col12:
            st.metric(
                label="Blitz number of games",
                value=str(user_data.get("perfs").get("blitz").get("games")),
            )
        with col13:
            st.metric(
                label="Bullet number of games",
                value=str(user_data.get("perfs").get("bullet").get("games")),
            )
        with col14:
            st.metric(
                label="Rapid number of games",
                value=str(user_data.get("perfs").get("rapid").get("games")),
            )

    # historical rating
    dict_historical_rating = get_user_rating_history_lichess(st.session_state.get("username_search"))
    if dict_historical_rating:
        get_user_historical_graph_lichess(dict_historical_rating)

    # create historical game activity
    user_games = get_historical_games_user_lichess(st.session_state.get("username_search"))
    if user_games.empty:
        st.write("No games found")
        st.stop()

    get_graph_user_winrate_lichess(user_games)

    user_games["Game deep dive"] = False
    user_games = user_games.sort_values(by=["created_at"], ascending=[False])
    st.session_state["df_user_games"] = user_games
    user_games_cleaned = user_games[["Game deep dive", "created_at", "speed", "result", "opponent_name", "opponent_rating"]]
    user_games_cleaned.reset_index(drop=True, inplace=True)
    st.data_editor(user_games_cleaned,
                   use_container_width=True,
                   column_config={"Game deep dive": st.column_config.CheckboxColumn(
                       "Game deep dive",
                       help="Related game, on click send you to a deep dive")},
                   disabled=["created_at", "speed", "result", "opponent_name", "opponent_rating"],
                   key=st.session_state["editor_key"],
                   on_change=get_row_and_clear_selection_user_report)

    if st.session_state.get("game_deep_dive_ready_for_redirect"):
        st.session_state["game_deep_dive_ready_for_redirect"] = False
        st.switch_page("pages/2_Game_Navigator.py")
