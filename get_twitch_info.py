import requests

TIMEOUT = 10


class TwitchAuthError(Exception):
    """Twitch APIの認証に失敗した場合(HTTP 401等)に送出される例外。"""

    pass


def _validate_credentials(client_id: str, client_secret: str, username: str) -> None:
    """
    Twitch API認証情報・アカウント名が入力済みかを検証する。

    Args:
        client_id (str): TwitchのClient ID
        client_secret (str): TwitchのClient Secret
        username (str): Twitchのユーザー名

    Raises:
        ValueError: いずれかが未設定の場合
    """
    if not client_id or not client_secret or not username:
        raise ValueError("Twitch APIの認証情報またはアカウント名が未設定です。")


def get_access_token(client_id: str, client_secret: str, debug_log=None) -> str:
    """
    Twitchのアプリアクセストークンを取得する。

    Args:
        client_id (str): TwitchのClient ID
        client_secret (str): TwitchのClient Secret
        debug_log (Callable[[str], None] | None): デバッグログ出力用コールバック

    Returns:
        str: アクセストークン

    Raises:
        TwitchAuthError: 認証に失敗した場合(HTTP 401)
        RuntimeError: アクセストークンを取得できなかった場合、または通信に失敗した場合
    """
    if debug_log:
        debug_log("Twitchアクセストークンを取得中...")

    auth_url = "https://id.twitch.tv/oauth2/token"
    auth_params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }

    try:
        auth_response = requests.post(auth_url, params=auth_params, timeout=TIMEOUT)
        if auth_response.status_code == 401:
            raise TwitchAuthError("Twitch認証に失敗しました(HTTP 401)。Client ID/Client Secretを確認してください。")
        auth_response.raise_for_status()
        access_token = auth_response.json().get("access_token")
        if not access_token:
            raise RuntimeError("Twitchアクセストークンを取得できませんでした。")
    except requests.RequestException as e:
        raise RuntimeError(f"Twitch APIへの通信に失敗しました: {e}") from e

    if debug_log:
        debug_log("Twitchアクセストークンを取得しました。")
    return access_token


def get_user_id(client_id: str, access_token: str, username: str, debug_log=None) -> str:
    """
    TwitchのユーザーIDを取得する。

    Args:
        client_id (str): TwitchのClient ID
        access_token (str): 取得済みのアクセストークン
        username (str): Twitchのユーザー名
        debug_log (Callable[[str], None] | None): デバッグログ出力用コールバック

    Returns:
        str: TwitchユーザーID

    Raises:
        TwitchAuthError: 認証に失敗した場合(HTTP 401)
        ValueError: 指定したユーザーが見つからない場合
        RuntimeError: ユーザーIDを取得できなかった場合、または通信に失敗した場合
    """
    if debug_log:
        debug_log(f"TwitchユーザーIDを取得中: {username}")

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}",
    }

    try:
        user_response = requests.get(
            "https://api.twitch.tv/helix/users",
            headers=headers,
            params={"login": username},
            timeout=TIMEOUT,
        )
        if user_response.status_code == 401:
            raise TwitchAuthError("Twitch認証に失敗しました(HTTP 401)。アクセストークンを確認してください。")
        user_response.raise_for_status()
        users = user_response.json().get("data", [])
        if not users:
            raise ValueError("指定したTwitchユーザーが見つかりませんでした。")
        user_id = users[0].get("id")
        if not user_id:
            raise RuntimeError("TwitchユーザーIDを取得できませんでした。")
    except requests.RequestException as e:
        raise RuntimeError(f"Twitch APIへの通信に失敗しました: {e}") from e

    if debug_log:
        debug_log(f"TwitchユーザーIDを取得しました: {user_id}")
    return user_id


def get_stream_info(client_id: str, access_token: str, user_id: str, debug_log=None):
    """
    配信情報(タイトル・ゲーム名・タグ)を取得する。配信していない場合は空文字/空リストを返す。

    Args:
        client_id (str): TwitchのClient ID
        access_token (str): 取得済みのアクセストークン
        user_id (str): 取得済みのTwitchユーザーID
        debug_log (Callable[[str], None] | None): デバッグログ出力用コールバック

    Returns:
        tuple: (配信タイトル, ゲーム名, タグリスト)。配信していない場合は ("", "", [])

    Raises:
        TwitchAuthError: 認証に失敗した場合(HTTP 401)
        RuntimeError: 通信に失敗した場合
    """
    if debug_log:
        debug_log("配信情報(streams)を取得中...")

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}",
    }

    try:
        stream_response = requests.get(
            "https://api.twitch.tv/helix/streams",
            headers=headers,
            params={"user_id": user_id},
            timeout=TIMEOUT,
        )
        if stream_response.status_code == 401:
            raise TwitchAuthError("Twitch認証に失敗しました(HTTP 401)。アクセストークンを確認してください。")
        stream_response.raise_for_status()
        stream_data = stream_response.json().get("data", [])
    except requests.RequestException as e:
        raise RuntimeError(f"Twitch APIへの通信に失敗しました: {e}") from e

    if not stream_data:
        if debug_log:
            debug_log("配信情報は空でした(配信が検知されていません)。")
        return "", "", []

    stream = stream_data[0]
    stream_title = stream.get("title", "")
    game_name = stream.get("game_name", "")
    tags = stream.get("tags", [])

    if debug_log:
        debug_log(f"配信情報を取得しました: title={stream_title!r}, game={game_name!r}")

    return stream_title, game_name, tags


def test_twitch_connection(client_id: str, client_secret: str, username: str, debug_log=None) -> str:
    """
    Twitch接続テスト用の軽量関数。アクセストークン取得とユーザーID検索のみ実施し、
    配信中チェック(streams API)は呼び出さない。

    Args:
        client_id (str): TwitchのClient ID
        client_secret (str): TwitchのClient Secret
        username (str): Twitchのユーザー名
        debug_log (Callable[[str], None] | None): デバッグログ出力用コールバック

    Returns:
        str: 見つかったTwitchユーザーID

    Raises:
        ValueError: 認証情報またはアカウント名が未設定の場合、指定したユーザーが見つからない場合
        TwitchAuthError: Twitch API認証に失敗した場合(HTTP 401)
        RuntimeError: Twitch APIへの通信に失敗した場合
    """
    _validate_credentials(client_id, client_secret, username)

    access_token = get_access_token(client_id, client_secret, debug_log=debug_log)
    return get_user_id(client_id, access_token, username, debug_log=debug_log)
