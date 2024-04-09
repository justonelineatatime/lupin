import streamlit as st
from utils import format_milliseconds, style_specific_cell
from io_utils import BQHelper
import chess
import chess.pgn
import chess.svg
import pandas as pd
import plotly.graph_objs as go
import requests as rq
import json


def search_game_info_trigger(username, game_id):
    st.session_state["username_game_search"] = username
    st.session_state["game_id_game_search"] = game_id
    st.session_state["game_retreived"] = True


def display_board(board, arrow, color_playing):
    if color_playing == "black":
        svg = chess.svg.board(board=board, arrows=arrow, flipped=True)
    else:
        svg = chess.svg.board(board=board, arrows=arrow)
    html_string = f'<div style="text-align: center;" >{svg}</div>'
    st.markdown(html_string, unsafe_allow_html=True)


@st.cache_data(ttl=300)
def get_game_data_immortal(username, game_id):
    bq_client = BQHelper.init_client()

    df_game = bq_client.query(
        f"""
        WITH user_info as (
              SELECT
                user_id,
                username
              FROM `immortal-data.dbt_immortal_public_data.users_public`
              WHERE LOWER(username) = LOWER("{username}")
            ),

            user_details as (
                SELECT
                    user_id,
                    username,
                    country_code,
                    fide_title,
                    rating_standard_blitz rating_blitz,
                    rating_standard_bullet rating_bullet,
                    rating_standard_rapid rating_rapid,
                    is_permanent_ban
                FROM `immortal-data.dbt_immortal_public_data.users_public`
            ),

            base_data as (
              SELECT
                game_id,
                user_id,
                created_at,
                moves,
                status,
                time_control,
                activity_category,
                variant,
                game_mode,
                speed,
                competition_edition_id,
                ARRAY_TO_STRING(ARRAY(select CONCAT(move_list.from, move_list.to, IFNULL(move_list.promotion, "")) FROM UNNEST(moves) as move_list), ",") list_of_all_moves,
                ARRAY_TO_STRING(ARRAY(select cast(move.clock.w as string) FROM UNNEST(moves) as move), ",") list_clock_w,
                ARRAY_TO_STRING(ARRAY(select cast(move.clock.b as string) FROM UNNEST(moves) as move), ",") list_clock_b,
                result,
                is_short_game,
                is_ultra_short_game,
                rating_at_game_start,
                opponent_rating_at_game_start,
                color,
                is_permanent_ban
              FROM `immortal-data.dbt_immortal_public_data.competition_game_user_public`
              where date(created_at) >= date_sub(current_date(), interval 4 week) 
              and game_id = "{game_id}"
              and plies_count > 0
            ),

            game_score as (
              SELECT
                user_id,
                game_id,
                ARRAY_TO_STRING(ARRAY(select cast(ifnull(move.r, 6) as string) FROM UNNEST(moves) as move), ",") list_move_rank,
                ARRAY_TO_STRING(ARRAY(select cast(round(cast(move.t as numeric), 2) as string) FROM UNNEST(moves) as move), ",") list_move_duration,
                ARRAY_TO_STRING(ARRAY(select cast(ifnull(move.o, 0) as string) FROM UNNEST(moves) as move), ",") list_move_advantage,
              FROM `immortal-data.dbt_immortal_public_data.game_analyzed_public`
              inner join user_info
                using(user_id)
              where date(created_at) >= date_sub(current_date(), interval 4 week) 
            )

            SELECT
              cgu.game_id,
              cgu.user_id,
              user_details.username,
              user_details.country_code,
              user_details.fide_title,
              user_details.rating_blitz rating_blitz,
              user_details.rating_bullet rating_bullet,
              user_details.rating_rapid rating_rapid,
              user_details.is_permanent_ban,
              cgu_opponent.user_id as user_id_opponent,
              user_details_opponent.username username_opponent,
              user_details_opponent.country_code country_code_opponent,
              user_details_opponent.fide_title fide_title_opponent,
              user_details_opponent.rating_blitz rating_blitz_opponent,
              user_details_opponent.rating_bullet rating_bullet_opponent,
              user_details_opponent.rating_rapid rating_rapid_opponent,
              user_details_opponent.is_permanent_ban is_permanent_ban_opponent,
              game_status.status,
              cgu.time_control,
              cgu.activity_category,
              cgu.variant,
              cgu.game_mode,
              cgu.speed,
              cgu.competition_edition_id,
              ARRAY_TO_STRING(ARRAY(select CONCAT(move_list.from, move_list.to, IFNULL(move_list.promotion, "")) FROM UNNEST(cgu.moves) as move_list), ",") list_of_all_moves,
              ARRAY_TO_STRING(ARRAY(select cast(move.clock.w as string) FROM UNNEST(cgu.moves) as move), ",") list_clock_w,
              ARRAY_TO_STRING(ARRAY(select cast(move.clock.b as string) FROM UNNEST(cgu.moves) as move), ",") list_clock_b,
              cgu.result,
              cgu.is_short_game,
              cgu.is_ultra_short_game,
              cgu.rating_at_game_start,
              cgu.opponent_rating_at_game_start,
              cgu.color,
              cgu_opponent.color color_opponent,
              cgu.is_permanent_ban,
              cgu_opponent.is_permanent_ban is_permanent_ban_opponent,
              game_score.list_move_rank,
              game_score.list_move_duration,
              game_score.list_move_advantage
            FROM base_data cgu
            INNER JOIN user_info
              on cgu.user_id = user_info.user_id
            LEFT JOIN base_data cgu_opponent
              on cgu.game_id = cgu_opponent.game_id
              and cgu.color != cgu_opponent.color
            LEFT JOIN game_score
              on cgu.user_id = game_score.user_id
              and cgu.game_id = game_score.game_id
            LEFT JOIN user_details
                on cgu.user_id = user_details.user_id
            LEFT JOIN user_details user_details_opponent
                on cgu_opponent.user_id = user_details_opponent.user_id
            LEFT JOIN dbt_seed.game_status
              on cgu.status = cast(game_status.id as int)
    """
    ).to_dataframe()

    if df_game.empty:
        st.session_state["game_not_found"] = True
        return None
    else:
        st.session_state["game_not_found"] = False

    # game info
    move_list_uci = df_game["list_of_all_moves"].iloc[0].split(",")
    list_clock_w = df_game["list_clock_w"].iloc[0].split(",")
    list_clock_b = df_game["list_clock_b"].iloc[0].split(",")
    move_list_san = []
    move_arrows = []
    board_san = chess.Board()
    for uci_move in move_list_uci:
        move = chess.Move.from_uci(uci_move)

        # Check if the move is legal
        if move in board_san.legal_moves:
            # Push the move onto the board
            move_arrows.append((move.from_square, move.to_square))
            move_list_san.append(board_san.san(move))
            board_san.push(move)

    list_move_rank_str = df_game["list_move_rank"].iloc[0]
    list_move_duration_str = df_game["list_move_duration"].iloc[0]
    list_move_advantage_str = df_game["list_move_advantage"].iloc[0]

    if list_move_rank_str:
        list_move_rank = [int(elem) for elem in list_move_rank_str.split(",")]
    else:
        list_move_rank = []
    if list_move_duration_str:
        list_move_duration = [
            round(float(elem), 2) for elem in list_move_duration_str.split(",")
        ]
    else:
        list_move_duration = []
    list_move_duration = [0] + list_move_duration
    list_move_duration_clean = [
        j - i for i, j in zip(list_move_duration[:-1], list_move_duration[1:])
    ]
    if list_move_advantage_str:
        list_move_advantage = [int(elem) for elem in list_move_advantage_str.split(",")]
    else:
        list_move_advantage = []

    color_playing = df_game["color"].iloc[0]

    if color_playing == "white":
        color_opponent = "black"
        len_for_color = len(move_list_uci[::2])
    else:
        color_opponent = "white"
        len_for_color = len(move_list_uci[1::2])

    if len(list_move_rank) < len_for_color:
        nb_zero_to_append = len_for_color - len(list_move_rank)
        list_move_rank.extend([0] * nb_zero_to_append)

    if len(list_move_duration_clean) < len_for_color:
        nb_zero_to_append = len_for_color - len(list_move_duration_clean)
        list_move_duration_clean.extend([0] * nb_zero_to_append)

    if len(list_move_advantage) < len_for_color:
        nb_zero_to_append = len_for_color - len(list_move_advantage)
        list_move_advantage.extend([0] * nb_zero_to_append)

    # users infos
    users_info = pd.DataFrame(
        {
            "Stats name": [
                "Username",
                "Country Code",
                "Fide Title",
                "Rating Bullet",
                "Rating Blitz",
                "Rating Rapid",
            ],
            f"{color_playing}": [
                df_game["username"].iloc[0],
                df_game["country_code"].iloc[0],
                df_game["fide_title"].iloc[0],
                df_game["rating_bullet"].iloc[0],
                df_game["rating_blitz"].iloc[0],
                df_game["rating_rapid"].iloc[0],
            ],
            f"{color_opponent}": [
                df_game["username_opponent"].iloc[0],
                df_game["country_code_opponent"].iloc[0],
                df_game["fide_title_opponent"].iloc[0],
                df_game["rating_bullet_opponent"].iloc[0],
                df_game["rating_blitz_opponent"].iloc[0],
                df_game["rating_rapid_opponent"].iloc[0],
            ],
        }
    )

    user_id = df_game["user_id"].iloc[0]

    data_payload = {
        "move_list_uci": move_list_uci,
        "list_clock_w": list_clock_w,
        "list_clock_b": list_clock_b,
        "move_list_san": move_list_san,
        "move_arrows": move_arrows,
        "list_move_rank": list_move_rank,
        "list_move_duration": list_move_duration_clean,
        "list_move_advantage": list_move_advantage,
        "user_info_df": users_info,
        "color_playing": color_playing,
        "user_id": user_id,
    }

    return data_payload


def san_to_uci(list_san_move):
    board = chess.Board()
    # Try to parse the SAN move using the board object
    uci_moves = []

    # Iterate over the SAN moves, convert them to UCI, and apply them to the board
    for san_move in list_san_move:
        # Convert SAN to a move object considering the current board state
        move = board.parse_san(san_move)

        # Convert the move object to UCI notation
        uci_move = move.uci()

        # Append the UCI move to the list
        uci_moves.append(uci_move)

        # Apply the move to the board to update its state
        board.push(move)

    return uci_moves


@st.cache_data(ttl=300)
def get_game_data_lichess(game_id):
    params = {
        'evals': True,
        'pgnInJson': True,
        'moves': True,
        'clocks': True,
        'accuracy': True,
        'division': True,
        'literate': True,
        "perfType": "bullet,blitz,rapid"
    }

    response_game = rq.get(f"https://lichess.org/game/export/{game_id}", params=params, headers={'Accept': 'application/json'})

    if "page not found" in response_game.text:
        st.session_state["game_not_found"] = True
        return None
    else:
        st.session_state["game_not_found"] = False

    game = json.loads(response_game.text)

    move_list_san = game.get("moves").split(" ")
    move_list_uci = san_to_uci(move_list_san)

    clocks = game.get("clocks")

    clocks = [clock * 10 for clock in clocks]

    initial_clock = int(game.get("clock").get("initial")) * 1000
    increment_clock = int(game.get("clock").get("increment")) * 1000

    clocks_with_start = [initial_clock, initial_clock] + clocks

    list_clock_w = clocks_with_start[0::2]
    list_clock_b = clocks_with_start[1::2]
    move_arrows = []
    board_san = chess.Board()
    for uci_move in move_list_uci:
        move = chess.Move.from_uci(uci_move)

        # Check if the move is legal
        if move in board_san.legal_moves:
            # Push the move onto the board
            move_arrows.append((move.from_square, move.to_square))
            board_san.push(move)

    if game.get("analysis"):
        eval_list = [game_eval.get("eval") for game_eval in game.get("analysis")]
    else:
        eval_list = []

    list_move_duration_white = [
        (i - (j - increment_clock))/1000 for i, j in zip(list_clock_w[:-1], list_clock_w[1:])
    ]
    list_move_duration_black = [
        (i - (j - increment_clock))/1000 for i, j in zip(list_clock_b[:-1], list_clock_b[1:])
    ]

    if st.session_state.get("username_game_search").lower() == game.get("players").get("white").get("user").get("name").lower():
        color_playing = "white"
        list_move_duration_clean = list_move_duration_white
        eval_list_clean = eval_list[::2]
    else:
        color_playing = "black"
        list_move_duration_clean = list_move_duration_black
        eval_list_clean = eval_list[1::2]

    if color_playing == "white":
        color_opponent = "black"
        len_for_color = len(move_list_uci[::2])
    else:
        color_opponent = "white"
        len_for_color = len(move_list_uci[1::2])

    if len(list_move_duration_clean) < len_for_color:
        nb_zero_to_append = len_for_color - len(list_move_duration_clean)
        list_move_duration_clean.extend([0] * nb_zero_to_append)

    if len(eval_list_clean) < len_for_color:
        nb_zero_to_append = len_for_color - len(eval_list_clean)
        eval_list_clean.extend([0] * nb_zero_to_append)

    # users infos
    users_info = pd.DataFrame(
        {
            "Stats name": [
                "Username",
                "Title",
                "Rating",

            ],
            f"{color_playing}": [
                game.get("players").get(color_playing).get("user").get("name"),
                game.get("players").get(color_playing).get("user").get("title"),
                game.get("players").get(color_playing).get("rating"),
            ],
            f"{color_opponent}": [
                game.get("players").get(color_opponent).get("user").get("name"),
                game.get("players").get(color_opponent).get("user").get("title"),
                game.get("players").get(color_opponent).get("rating"),
            ],
        }
    )

    data_payload = {
        "move_list_uci": move_list_uci,
        "list_clock_w": list_clock_w,
        "list_clock_b": list_clock_b,
        "move_list_san": move_list_san,
        "move_arrows": move_arrows,
        "list_move_duration": list_move_duration_clean,
        "list_move_eval": eval_list_clean,
        "user_info_df": users_info,
        "color_playing": color_playing,
    }

    return data_payload


def create_graph_immortal(
    list_move_rank,
    list_move_duration,
    list_move_advantage,
    current_move_index,
    list_move_san,
    color,
):

    # Create traces for each dataset
    trace2 = go.Bar(
        x=list(range(len(list_move_rank))),
        y=list_move_rank,
        name="Move rank",
        yaxis="y2",
        opacity=0.4,
    )
    trace3 = go.Scatter(
        x=list(range(len(list_move_duration))),
        y=list_move_duration,
        mode="lines+markers",
        name="Move duration (s)",
    )
    trace4 = go.Scatter(
        x=list(range(len(list_move_advantage))),
        y=list_move_advantage,
        mode="lines+markers",
        name="Move advantage",
    )
    if color == "white":
        move_to_outline = (current_move_index - 1) // 2
    else:
        move_to_outline = current_move_index // 2 - 1

    if move_to_outline < 0:
        move_to_outline = 0

    # Create the layout of the graph, include a secondary y-axis with the domain set to [1, 6]
    layout = go.Layout(
        title="Evolution of the game",
        xaxis=dict(title="Move Number"),
        yaxis=dict(title="Duration / Advantage"),
        yaxis2=dict(
            title="Rank",
            overlaying="y",
            side="right",
            range=[0, 6],  # Set the range for the secondary y-axis
        ),
        shapes=[
            # Line Vertical
            go.layout.Shape(
                type="line",
                label=dict(text=f"{list_move_san[move_to_outline]}"),
                x0=move_to_outline,
                y0=0,
                x1=move_to_outline,
                y1=1,
                xref="x",
                yref="paper",  # Refers to the entire y-axis area
                line=dict(color="orange", width=3),
            ),
        ],
    )

    # Create a figure
    fig = go.Figure(data=[trace2, trace3, trace4], layout=layout)
    fig.update_layout(
        xaxis=dict(showgrid=False),  # Remove x-axis gridlines
        yaxis=dict(showgrid=False),
        yaxis2=dict(showgrid=False),
    )
    # Show the plot in Streamlit
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def create_graph_lichess(
    list_move_duration,
    list_move_advantage,
    current_move_index,
    list_move_san,
    color,
):

    trace3 = go.Scatter(
        x=list(range(len(list_move_duration))),
        y=list_move_duration,
        mode="lines+markers",
        name="Move duration (s)",
    )
    trace4 = go.Scatter(
        x=list(range(len(list_move_advantage))),
        y=list_move_advantage,
        mode="lines+markers",
        name="Move advantage",
    )
    if color == "white":
        move_to_outline = (current_move_index - 1) // 2
    else:
        move_to_outline = current_move_index // 2 - 1

    if move_to_outline < 0:
        move_to_outline = 0

    # Create the layout of the graph, include a secondary y-axis with the domain set to [1, 6]
    layout = go.Layout(
        title="Evolution of the game",
        xaxis=dict(title="Move Number"),
        yaxis=dict(title="Duration / Advantage"),
        yaxis2=dict(
            title="Rank",
            overlaying="y",
            side="right",
            range=[0, 6],  # Set the range for the secondary y-axis
        ),
        shapes=[
            # Line Vertical
            go.layout.Shape(
                type="line",
                label=dict(text=f"{list_move_san[move_to_outline]}"),
                x0=move_to_outline,
                y0=0,
                x1=move_to_outline,
                y1=1,
                xref="x",
                yref="paper",  # Refers to the entire y-axis area
                line=dict(color="orange", width=3),
            ),
        ],
    )

    # Create a figure
    fig = go.Figure(data=[trace3, trace4], layout=layout)
    fig.update_layout(
        xaxis=dict(showgrid=False),  # Remove x-axis gridlines
        yaxis=dict(showgrid=False),
        yaxis2=dict(showgrid=False),
    )
    # Show the plot in Streamlit
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def content_immortal_game_game_navigator():
    if not st.session_state.get("username_game_search"):
        st.session_state["username_game_search"] = None
    if not st.session_state.get("game_id_game_search"):
        st.session_state["game_id_game_search"] = None
    col_main_header_1, col_main_header_2 = st.columns([5, 1])
    with col_main_header_1:
        game_info_expander = st.expander("Game Information", expanded=True)
        with game_info_expander:
            with st.form(key="game_info_form"):
                col_expand_1, col_expand_2, col_expand_3 = st.columns([2, 2, 1])
                with col_expand_1:
                    username_game_search = st.text_input("Username", value=st.session_state.get("username_game_search"))
                with col_expand_2:
                    game_id_game_search = st.text_input("Game ID", value=st.session_state.get("game_id_game_search"))
                with col_expand_3:
                    st.write("")
                    search_button = st.form_submit_button(
                        "Search", use_container_width=True, on_click=search_game_info_trigger, args=(username_game_search, game_id_game_search)
                    )
    with col_main_header_2:
        st.image(image="images/IGE-logo.png")

    if not st.session_state.get("username_game_search") or not st.session_state.get(
        "game_id_game_search"
    ):
        st.caption("Please enter a username and a game ID to search for a game")
        st.stop()

    # Initialize or load a game
    data_payload = get_game_data_immortal(
        username=st.session_state.get("username_game_search"),
        game_id=st.session_state.get("game_id_game_search"),
    )

    if not data_payload:
        st.error(
            "Game not found - Whether the username or the game ID is incorrect or it is a game that tookplace more that a month ago"
        )
        st.write(st.session_state)
        st.stop()

    st.session_state["data_payload"] = data_payload

    move_list_uci = data_payload.get("move_list_uci")
    list_clock_w = data_payload.get("list_clock_w")
    list_clock_b = data_payload.get("list_clock_b")
    move_list_san = data_payload.get("move_list_san")
    list_move_rank = data_payload.get("list_move_rank")
    list_move_duration = data_payload.get("list_move_duration")
    list_move_advantage = data_payload.get("list_move_advantage")
    df_user_info = data_payload.get("user_info_df")
    color_playing = data_payload.get("color_playing")
    move_arrows = data_payload.get("move_arrows")

    # to remove
    print("Game deep dive session state", st.session_state)
    # ----

    list_san_white = move_list_san[::2]
    list_san_black = move_list_san[1::2]
    length_difference = abs(len(list_san_white) - len(list_san_black))

    # Append empty strings to the smaller list
    board = chess.Board()
    if len(list_san_white) > len(list_san_black):
        list_san_black.extend([""] * length_difference)
    else:
        list_san_white.extend([""] * length_difference)
    moves_tab_df = pd.DataFrame({"White": list_san_white, "Black": list_san_black})

    username = st.session_state.get("username_game_search")
    color = st.session_state.get("color")
    st.title(f"Game Navigator for {username} playing as {color_playing}")
    current_move_index = st.session_state.get("current_move_index", 0)
    if current_move_index > len(move_list_uci):
        current_move_index = 0
        st.session_state["current_move_index"] = current_move_index
    # Display updated board
    container_chess_game = st.container()
    with container_chess_game:
        col1, col2, col3 = st.columns([1, 2, 3])
        with col1:
            st.write("")
            if st.button("Next", use_container_width=True):
                if current_move_index < len(move_list_uci):
                    current_move_index += 1
                    st.session_state["current_move_index"] = current_move_index
            if st.button("Previous", use_container_width=True):
                if current_move_index > 0:
                    current_move_index -= 1
                    st.session_state["current_move_index"] = current_move_index
            st.divider()
            if st.button("Reset", use_container_width=True):
                current_move_index = 0
                st.session_state["current_move_index"] = current_move_index
            st.write("")
            if current_move_index > 0:
                st.write("Black clock:")
                st.markdown(
                    f"### {format_milliseconds(list_clock_b[current_move_index-1])}"
                )
                st.write("")
                st.write("")
                st.write("White clock:")
                st.markdown(
                    f"### {format_milliseconds(list_clock_w[current_move_index-1])}"
                )
        with col3:
            container_side_info = st.container()
            with container_side_info:
                col4, col5 = st.columns([1, 2])
                with col4:
                    col = 0 if (current_move_index - 1) % 2 == 0 else 1
                    row_index = (current_move_index - 1) // 2
                    color = "blue"
                    st.dataframe(
                        moves_tab_df.style.apply(
                            lambda x: style_specific_cell(
                                x, row=row_index, col=col, color=color
                            ),
                            axis=None,
                        ),
                        use_container_width=True,
                    )
                with col5:
                    st.dataframe(df_user_info, use_container_width=True, hide_index=True)
                    if color_playing == "white":
                        move_to_look_for = current_move_index // 2
                    else:
                        move_to_look_for = current_move_index // 2 - 1
                if move_to_look_for >= 0:
                    df_move_info = pd.DataFrame(
                        {
                            "Move Number": [move_to_look_for],
                            "Move Duration (s)": [list_move_duration[move_to_look_for]],
                            "Move Rank Stockfish": [list_move_rank[move_to_look_for]],
                            "Move Advantage (100)": [
                                list_move_advantage[move_to_look_for]
                            ],
                        }
                    )
                    st.dataframe(
                        df_move_info, use_container_width=True, hide_index=True
                    )
        with col2:
            # Update board to the current move
            for i in range(current_move_index):
                board.push(chess.Move.from_uci(move_list_uci[i]))
            if current_move_index - 1 >= 0:
                arrow = [move_arrows[current_move_index - 1]]
            else:
                arrow = []
            display_board(board, arrow=arrow, color_playing=color_playing)
            st.write("")
            bar = st.progress(
                int((current_move_index / len(move_list_uci)) * 100),
                f"Move {current_move_index}/{len(move_list_uci)}",
            )

    if (
        not list_move_rank
        or not list_move_duration
        or not list_move_advantage
    ):
        st.header("This game has not been processed yet.")
        st.button("Send this game for processing")
        st.stop()

    if color_playing == "white":
        move_list_san_graph = list_san_white
    else:
        move_list_san_graph = list_san_black

    create_graph_immortal(
        list_move_rank,
        list_move_duration,
        list_move_advantage,
        current_move_index,
        move_list_san_graph,
        color_playing
    )


def content_lichess_game_navigator():
    if not st.session_state.get("username_game_search"):
        st.session_state["username_game_search"] = None
    if not st.session_state.get("game_id_game_search"):
        st.session_state["game_id_game_search"] = None
    col_main_header_1, col_main_header_2 = st.columns([5, 1])
    with col_main_header_1:
        game_info_expander = st.expander("Game Information", expanded=True)
        with game_info_expander:
            with st.form(key="game_info_form"):
                col_expand_1, col_expand_2, col_expand_3 = st.columns([2, 2, 1])
                with col_expand_1:
                    username_game_search = st.text_input("Username", value=st.session_state.get("username_game_search"))
                with col_expand_2:
                    game_id_game_search = st.text_input("Game ID", value=st.session_state.get("game_id_game_search"))
                with col_expand_3:
                    st.write("")
                    search_button = st.form_submit_button(
                        "Search", use_container_width=True, on_click=search_game_info_trigger,
                        args=(username_game_search, game_id_game_search)
                    )

    with col_main_header_2:
        st.image(image="images/lichess-logo.jpg")

    if not st.session_state.get(
            "game_id_game_search"
    ) or not st.session_state.get("username_game_search"):
        st.caption("Please enter a game ID to search for a game")
        st.stop()

    # Initialize or load a game
    data_payload = get_game_data_lichess(
        game_id=st.session_state.get("game_id_game_search"),
    )

    if not data_payload:
        st.error(
            "Game not found - Whether the username or the game ID is incorrect or it is a game that tookplace more that a month ago"
        )
        st.write(st.session_state)
        st.stop()

    st.session_state["data_payload"] = data_payload

    move_list_uci = data_payload.get("move_list_uci")
    list_clock_w = data_payload.get("list_clock_w")
    list_clock_b = data_payload.get("list_clock_b")
    move_list_san = data_payload.get("move_list_san")
    list_move_duration = data_payload.get("list_move_duration")
    list_move_eval = data_payload.get("list_move_eval")
    df_user_info = data_payload.get("user_info_df")
    color_playing = data_payload.get("color_playing")
    move_arrows = data_payload.get("move_arrows")

    # to remove
    print("Game deep dive session state", st.session_state)
    # ---

    list_san_white = move_list_san[::2]
    list_san_black = move_list_san[1::2]
    length_difference = abs(len(list_san_white) - len(list_san_black))

    # Append empty strings to the smaller list
    board = chess.Board()
    if len(list_san_white) > len(list_san_black):
        list_san_black.extend([""] * length_difference)
    else:
        list_san_white.extend([""] * length_difference)
    moves_tab_df = pd.DataFrame({"White": list_san_white, "Black": list_san_black})

    username = st.session_state.get("username_game_search")
    color = st.session_state.get("color")
    st.title(f"Game Navigator for {username} playing as {color_playing}")
    current_move_index = st.session_state.get("current_move_index", 0)
    if current_move_index > len(move_list_uci):
        current_move_index = 0
        st.session_state["current_move_index"] = current_move_index
    # Display updated board
    container_chess_game = st.container()
    with container_chess_game:
        col1, col2, col3 = st.columns([1, 2, 3])
        with col1:
            st.write("")
            if st.button("Next", use_container_width=True):
                if current_move_index < len(move_list_uci):
                    current_move_index += 1
                    st.session_state["current_move_index"] = current_move_index
            if st.button("Previous", use_container_width=True):
                if current_move_index > 0:
                    current_move_index -= 1
                    st.session_state["current_move_index"] = current_move_index
            st.divider()
            if st.button("Reset", use_container_width=True):
                current_move_index = 0
                st.session_state["current_move_index"] = current_move_index
            st.write("")
            if current_move_index > 0:
                st.write("Black clock:")
                move_to_look_for_black = current_move_index // 2
                if move_to_look_for_black < 0:
                    move_to_look_for_black = 0
                st.markdown(
                    f"### {format_milliseconds(list_clock_b[move_to_look_for_black])}"
                )
                st.write("")
                st.write("")
                st.write("White clock:")
                move_to_look_for_white = ((current_move_index - 1) // 2) + 1
                if move_to_look_for_white < 0:
                    move_to_look_for_white = 0
                st.markdown(
                    f"### {format_milliseconds(list_clock_w[move_to_look_for_white])}"
                )
        with col3:
            container_side_info = st.container()
            with container_side_info:
                col4, col5 = st.columns([1, 2])
                with col4:
                    col = 0 if (current_move_index - 1) % 2 == 0 else 1
                    row_index = (current_move_index - 1) // 2
                    color = "blue"
                    st.dataframe(
                        moves_tab_df.style.apply(
                            lambda x: style_specific_cell(
                                x, row=row_index, col=col, color=color
                            ),
                            axis=None,
                        ),
                        use_container_width=True,
                    )
                with col5:
                    st.dataframe(df_user_info, use_container_width=True, hide_index=True)
                    if color_playing == "white":
                        move_to_look_for = current_move_index // 2
                    else:
                        move_to_look_for = current_move_index // 2 - 1
                if move_to_look_for >= 0:
                    df_move_info = pd.DataFrame(
                        {
                            "Move Number": [move_to_look_for],
                            "Move Duration (s)": [list_move_duration[move_to_look_for]],
                            "Move Eval": [list_move_eval[move_to_look_for]],
                        }
                    )
                    st.dataframe(
                        df_move_info, use_container_width=True, hide_index=True
                    )
        with col2:
            # Update board to the current move
            for i in range(current_move_index):
                board.push(chess.Move.from_uci(move_list_uci[i]))
            if current_move_index - 1 >= 0:
                arrow = [move_arrows[current_move_index - 1]]
            else:
                arrow = []
            display_board(board, arrow=arrow, color_playing=color_playing)
            st.write("")
            bar = st.progress(
                int((current_move_index / len(move_list_uci)) * 100),
                f"Move {current_move_index}/{len(move_list_uci)}",
            )

    if (
            not list_move_duration
            or not list_move_eval
    ):
        st.header("This game has not been processed yet.")
        st.button("Send this game for processing")
        st.stop()

    if color_playing == "white":
        move_list_san_graph = list_san_white
    else:
        move_list_san_graph = list_san_black

    create_graph_lichess(
        list_move_duration,
        list_move_eval,
        current_move_index,
        move_list_san_graph,
        color_playing
    )