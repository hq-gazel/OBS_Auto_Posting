import obspython as obs
import get_twitch_info

import datetime
import threading
import time

# ==========================
# グローバル変数定義
# ==========================
version = 1.0

twitch_acc = ""
twitch_client_id = ""
twitch_client_secret = ""

notify_X = False
X_account = ""
X_password = ""
X_API_key = ""
X_API_secret = ""
X_access_token = ""
X_access_secret = ""

notify_bluesky = False
Bluesky_account = ""
Bluesky_password = ""

# notify_mixi2 = False
# mixi2_account = ""
# mixi2_password = ""

notify_discord = False
webhook_url = ""

send_message = ""
hashtags = ""

stream_title = ""
game_name = ""
tags = ""

class info_getter(threading.Thread):
    def __init__(self):
        super().__init__()

    def run(self):
        print(f"OBS Auto Post ver: {version}\nCreated by shin-hq")

        max_retry = 15  # 最大リトライ回数（例: 10秒×15回=150秒）
        for i in range(max_retry):
            try:
                stream_title, game_name, tags = get_twitch_info.get_twitch_info(
                    twitch_client_id, twitch_client_secret, twitch_acc
                )

            except Exception as e:
                if i == max_retry - 1:
                    return log(f"配信情報の取得中にエラーが発生しました: {e}[{datetime.datetime.now()}]")
                time.sleep(10)  # 10秒待って再試行

        message = f"{stream_title} ({game_name})"
        url = f"https://www.twitch.tv/{twitch_acc}"
        tags_str = " ".join([f"#{i}" for i in tags])
        log(f"配信情報を取得しました: {message}\nタグ: {tags_str}[{datetime.datetime.now()}]")

        # 取得できなかった場合は処理をしない
        if not stream_title:
            return

        # Bluesky通知
        if notify_bluesky and Bluesky_account and Bluesky_password:
            send_Bluesky_notification(message, tags_str, url)

        # X通知
        if notify_X and X_account and X_password and X_API_key and X_API_secret and X_access_token and X_access_secret:
            send_X_notification(message, tags_str, url)

        # Discord通知
        if notify_discord and webhook_url:
            send_discord_notification(message, url)

        # mixi2通知（コメントアウト中）
        # if notify_mixi2 and mixi2_account and stream_title is not None:
        #     send_mixi2_notification(message, tags_str)


# ==========================
# ログ出力関数
# ==========================
def log(message):
    obs.script_log(obs.LOG_INFO, message)

# ==========================
# スクリプトの説明
# ==========================
def script_description():
    return (
        "配信開始時にX, Bluesky, mixi2に自動通知するPythonスクリプト。"
        "DiscordはWebhookを介して通知します。"
    )

# ==========================
# スクリプトのロード時に呼び出される関数
# ==========================
def script_load(settings):
    # イベントコールバックの重複登録を防ぐため、一度解除してから登録
    obs.obs_frontend_remove_event_callback(on_event)
    obs.obs_frontend_add_event_callback(on_event)

# ==========================
# イベントコールバック関数
# ==========================
def on_event(event):
    if event == obs.OBS_FRONTEND_EVENT_STREAMING_STARTED:
        log(f"配信が開始されました。情報を取得中... [{datetime.datetime.now()}]")
        thread_A = info_getter()

        thread_A.start()

    elif event == obs.OBS_FRONTEND_EVENT_STREAMING_STOPPED:
        log(f"配信が停止されました。[{datetime.datetime.now()}]")

# ==========================
# Discordに通知を送信する関数
# ==========================
def send_discord_notification(message, url):
    payload = {"content": f"{message}\n\n{url}"}
    try:
        res = requests.post(webhook_url, json=payload)
        if res.status_code == 204:
            print(f"Discordに通知を送信しました。[{datetime.datetime.now()}]")
        else:
            print(f"エラーが発生しました。{res.status_code} - {res.text}")
    except Exception as e:
        print(f"Discord通知送信中にエラー: {e}")

# ==========================
# Xに通知を送信する関数
# ==========================
def send_X_notification(message, tags_str, url):
    try:
        X_client = tweepy.Client(
            consumer_key=X_API_key,
            consumer_secret=X_API_secret,
            access_token=X_access_token,
            access_token_secret=X_access_secret
        )
        X_client.create_tweet(text=f"{message}\n{url}\n\n{tags_str}")

    except Exception as e:
        print(f"Xのアカウント情報が不足しているか、一時的なネットワークエラーです。\n{e}")

# ==========================
# Blueskyに通知を送信する関数
# ==========================
def send_Bluesky_notification(message, tags_str, url):
    try:
        bs_client = atproto.Client()
        bs_client.login(Bluesky_account, Bluesky_password)
        text_builder = atproto.client_utils.TextBuilder().text(f"{message}\n").link(text="Twitch URL", url=url).text("\n\n")
        for tag in tags_str.split(" "):
            text_builder = text_builder.tag(text=tag, tag=tag).text(" ")

        bs_client.send_post(text_builder)

    except Exception as e:
        print(f"Blueskyへの通知送信に失敗しました。アカウント情報を確認してください。\n{e}")

# ==========================
# 設定変更・リロード時に呼ばれる関数
# ==========================
def script_update(settings):
    global twitch_acc, twitch_client_id, twitch_client_secret
    global notify_discord, webhook_url
    global notify_X, X_account, X_password, X_API_key, X_API_secret, X_access_token, X_access_secret
    global notify_bluesky, Bluesky_account, Bluesky_password
    # global notify_mixi2, mixi2_account, mixi2_password

    # 各種設定値を取得
    twitch_acc = obs.obs_data_get_string(settings, "twitch_acc")
    twitch_client_id = obs.obs_data_get_string(settings, "twitch_client_id")
    twitch_client_secret = obs.obs_data_get_string(settings, "twitch_client_secret")

    notify_discord = obs.obs_data_get_bool(settings, "notify_discord")
    webhook_url = obs.obs_data_get_string(settings, "webhook_url")

    notify_X = obs.obs_data_get_bool(settings, "notify_X")
    X_account = obs.obs_data_get_string(settings, "X_account")
    X_password = obs.obs_data_get_string(settings, "X_password")
    X_API_key = obs.obs_data_get_string(settings, "X_API_key")
    X_API_secret = obs.obs_data_get_string(settings, "X_API_secret")
    X_access_token = obs.obs_data_get_string(settings, "X_access_token")
    X_access_secret = obs.obs_data_get_string(settings, "X_access_secret")

    notify_bluesky = obs.obs_data_get_bool(settings, "notify_Bluesky")
    Bluesky_account = obs.obs_data_get_string(settings, "Bluesky_account")
    Bluesky_password = obs.obs_data_get_string(settings, "Bluesky_password")

    # notify_mixi2 = obs.obs_data_get_bool(settings, "notify_mixi2")
    # mixi2_account = obs.obs_data_get_string(settings, "mixi2_account")
    # mixi2_password = obs.obs_data_get_string(settings, "mixi2_password")

# ==========================
# OBSプロパティ（設定UI）定義
# ==========================
def script_properties():
    props = obs.obs_properties_create()

    # Twitch API設定
    obs.obs_properties_add_text(props, "twitch_acc", "Twitch Account ID", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "twitch_client_id", "Twitch Client ID", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "twitch_client_secret", "Twitch Client Secret", obs.OBS_TEXT_PASSWORD)

    # X設定
    obs.obs_properties_add_bool(props, "notify_X", "Xに通知を送る")
    obs.obs_properties_add_text(props, "X_account", "Xのアカウント名", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "X_password", "Xのパスワード", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "X_API_key", "XのAPIキー", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "X_API_secret", "XのシークレットAPIキー", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "X_access_token", "Xのアクセストークン", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "X_access_secret", "Xのシークレットトークン", obs.OBS_TEXT_PASSWORD)

    # Bluesky設定
    obs.obs_properties_add_bool(props, "notify_Bluesky", "Blueskyに通知を送る")
    obs.obs_properties_add_text(props, "Bluesky_account", "Blueskyのアカウント名", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "Bluesky_password", "Blueskyのパスワード", obs.OBS_TEXT_PASSWORD)

    # # mixi2設定
    # obs.obs_properties_add_bool(props, "notify_mixi2", "mixi2に通知を送る")
    # obs.obs_properties_add_text(props, "mixi2_account", "mixi2のアカウント名", obs.OBS_TEXT_DEFAULT)
    # obs.obs_properties_add_text(props, "mixi2_password", "mixi2のパスワード", obs.OBS_TEXT_PASSWORD)

    # Discord設定
    obs.obs_properties_add_bool(props, "notify_discord", "Discordに通知を送る")
    obs.obs_properties_add_text(props, "webhook_url", "Webhook URL", obs.OBS_TEXT_PASSWORD)

    return props