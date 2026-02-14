import requests


def get_twitch_info(client_id: str, client_secret: str, username: str):
    """
    Twitchの配信タイトル・ゲーム名・タグを取得する関数

    Args:
        client_id (str): TwitchのClient ID
        client_secret (str): TwitchのClient Secret
        username (str): Twitchのユーザー名

    Returns:
        tuple: (配信タイトル, ゲーム名, タグリスト)

    Raises:
        ValueError: 配信が見つからない場合
    """
    timeout = 10
    if not client_id or not client_secret or not username:
        raise ValueError("Twitch APIの認証情報またはアカウント名が未設定です。")

    auth_url = "https://id.twitch.tv/oauth2/token"
    auth_params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }

    try:
        # アクセストークン取得
        auth_response = requests.post(auth_url, params=auth_params, timeout=timeout)
        auth_response.raise_for_status()
        access_token = auth_response.json().get("access_token")
        if not access_token:
            raise RuntimeError("Twitchアクセストークンを取得できませんでした。")

        headers = {
            "Client-ID": client_id,
            "Authorization": f"Bearer {access_token}",
        }

        # ユーザーID取得
        user_response = requests.get(
            "https://api.twitch.tv/helix/users",
            headers=headers,
            params={"login": username},
            timeout=timeout,
        )
        user_response.raise_for_status()
        users = user_response.json().get("data", [])
        if not users:
            raise ValueError("指定したTwitchユーザーが見つかりませんでした。")
        user_id = users[0].get("id")
        if not user_id:
            raise RuntimeError("TwitchユーザーIDを取得できませんでした。")

        # 配信情報の取得
        stream_response = requests.get(
            "https://api.twitch.tv/helix/streams",
            headers=headers,
            params={"user_id": user_id},
            timeout=timeout,
        )
        stream_response.raise_for_status()
        stream_data = stream_response.json().get("data", [])
        if not stream_data:
            raise ValueError("配信が見つかりませんでした。")

        stream = stream_data[0]
        stream_title = stream.get("title", "")
        game_name = stream.get("game_name", "")
        tags = stream.get("tags", [])
        return stream_title, game_name, tags

    except requests.RequestException as e:
        raise RuntimeError(f"Twitch APIへの通信に失敗しました: {e}") from e
