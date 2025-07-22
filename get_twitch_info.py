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

    # アクセストークン取得
    auth_url = 'https://id.twitch.tv/oauth2/token'
    auth_params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }

    auth_response = requests.post(auth_url, params=auth_params, timeout=timeout).json()
    access_token = auth_response['access_token']

    # APIリクエスト用ヘッダーを準備
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {access_token}'
    }

    # ユーザーID取得
    user_response = requests.get(
        'https://api.twitch.tv/helix/users',
        headers=headers,
        params={'login': username},
        timeout=timeout
    ).json()
    user_id = user_response['data'][0]['id']

    # 配信情報の取得
    stream_response = requests.get(
        'https://api.twitch.tv/helix/streams',
        headers=headers,
        params={'user_id': user_id},
        timeout=timeout
    ).json()

    # 配信中の場合は情報を返す
    if stream_response['data']:
        stream_data = stream_response['data'][0]
        stream_title = stream_data['title']
        game_name = stream_data['game_name']
        tags = stream_data['tags']
        return stream_title, game_name, tags

    # 配信していない場合は例外を投げる
    else:
        raise ValueError("配信が見つかりませんでした。")