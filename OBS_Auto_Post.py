import obspython as obs
import get_twitch_info

import requests

import threading
import time
import re

# ==========================
# グローバル変数定義
# ==========================
version = 1.03

twitch_acc = ""
twitch_client_id = ""
twitch_client_secret = ""
get_info_cnt = 10
get_info_interval = 15

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

notify_discord = False
webhook_url = ""

send_message = ""
hashtags = ""

stream_title = ""
game_name = ""
tags = ""
SNS_retry_cnt = 5
SNS_retry_interval = 60
REQUEST_TIMEOUT = 10


class info_getter(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)

    def run(self):
        print(f"OBS Auto Post ver: {version}\nCreated by shin-hq")

        stream_title = ""
        game_name = ""
        tags = []

        max_retry = max(get_info_cnt, 1)
        for i in range(max_retry):
            try:
                stream_title, game_name, tags = get_twitch_info.get_twitch_info(
                    twitch_client_id, twitch_client_secret, twitch_acc
                )
                break
            except Exception as e:
                if i == max_retry - 1:
                    return log(f"配信情報の取得中にエラーが発生しました: {e}")
                log(f"配信情報の取得に失敗しました。{i + 1}/{max_retry}回目: {e}")
                time.sleep(max(get_info_interval, 1))

        message = f"{stream_title} ({game_name})"
        url = f"https://www.twitch.tv/{twitch_acc}"
        tags_str = " ".join([f"#{i}" for i in tags])
        log(f"配信情報を取得しました: {message}\nタグ: {tags_str}")

        # 取得できなかった場合は処理をしない
        if not stream_title:
            return log("配信情報が正常に取得出来ず、何回か再試行しましたがダメでした。")

        # Bluesky通知
        if notify_bluesky and Bluesky_account and Bluesky_password:
            thread_B = threading.Thread(
                target=send_Bluesky_notification,
                args=(message, tags, url),
                daemon=True,
            )
            thread_B.start()

        # X通知
        if notify_X and X_API_key and X_API_secret and X_access_token and X_access_secret:
            thread_C = threading.Thread(
                target=send_X_notification,
                args=(message, tags_str, url),
                daemon=True,
            )
            thread_C.start()

        # Discord通知
        if notify_discord and webhook_url:
            thread_D = threading.Thread(
                target=send_discord_notification,
                args=(message, url),
                daemon=True,
            )
            thread_D.start()

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
        "配信開始時にX, Blueskyに自動通知するPythonスクリプト。"
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
        log("配信が開始されました。情報を取得中... ")
        thread_A = info_getter()
        thread_A.start()

    elif event == obs.OBS_FRONTEND_EVENT_STREAMING_STOPPED:
        log("配信が停止されました。")

# ==========================
# Discordに通知を送信する関数
# ==========================
def send_discord_notification(message, url):
    payload = {"content": f"{message}\n\n{url}"}
    retry_count = max(SNS_retry_cnt, 1)
    for y in range(retry_count):
        try:
            res = requests.post(webhook_url, json=payload, timeout=REQUEST_TIMEOUT)
            if res.status_code == 204:
                return log("Discordに通知を送信しました。")
            log(f"Discord通知送信に失敗しました。status={res.status_code}, body={res.text[:200]}")
        except requests.RequestException as e:
            log(f"Discord通知送信中にネットワークエラー: {e}")

        if y != retry_count - 1:
            time.sleep(max(SNS_retry_interval, 1))

    log("Discord通知の送信を中断しました。")

# ==========================
# Xに通知を送信する関数
# ==========================
def send_X_notification(message, tags_str, url):
    try:
        import tweepy
    except Exception as e:
        return log(f"tweepyの読み込みに失敗しました。依存ライブラリをインストールしてください: {e}")

    retry_count = max(SNS_retry_cnt, 1)
    X_client = tweepy.Client(
        consumer_key=X_API_key,
        consumer_secret=X_API_secret,
        access_token=X_access_token,
        access_token_secret=X_access_secret,
    )
    for x in range(retry_count):
        try:
            X_client.create_tweet(text=f"{message}\n{url}\n\n{tags_str}")
            return log("Xに通知を送信しました。")

        except Exception as e:
            log(f"Xへの通知送信に失敗しました。{x + 1}/{retry_count}回目: {e}")
            if x != retry_count - 1:
                time.sleep(max(SNS_retry_interval, 1))

    log("X通知の送信を中断しました。")

# ==========================
# Blueskyに通知を送信する関数
# ==========================
def normalize_bluesky_account(account):
    normalized = account.strip()
    if normalized.startswith("@"):
        normalized = normalized[1:]
    if not re.search(r"\.bsky\.social$", normalized, re.IGNORECASE):
        normalized = f"{normalized}.bsky.social"
    return normalized


def send_Bluesky_notification(message, tags, url):
    try:
        import atproto
    except Exception as e:
        return log(f"atprotoの読み込みに失敗しました。依存ライブラリをインストールしてください: {e}")

    retry_count = max(SNS_retry_cnt, 1)
    bluesky_account = normalize_bluesky_account(Bluesky_account)
    for i in range(retry_count):
        try:
            bs_client = atproto.Client()
            bs_client.login(bluesky_account, Bluesky_password)

            text_builder = (
                atproto.client_utils.TextBuilder()
                .text(f"{message}\n")
                .link(text="Twitch URL", url=url)
                .text("\n\n")
            )
            for tag in tags:
                clean_tag = str(tag).strip().lstrip("#")
                if clean_tag:
                    text_builder = text_builder.tag(text=f"#{clean_tag}", tag=clean_tag).text(" ")

            bs_client.send_post(text_builder)
            return log("Blueskyに通知を送信しました。")

        except Exception as e:
            log(f"Blueskyへの通知送信に失敗しました。{i + 1}/{retry_count}回目: {e}")
            if i != retry_count - 1:
                time.sleep(max(SNS_retry_interval, 1))

    log("Bluesky通知の送信を中断しました。")


# ==========================
# 設定変更・リロード時に呼ばれる関数
# ==========================
def script_update(settings):
    global twitch_acc, twitch_client_id, twitch_client_secret
    global notify_discord, webhook_url
    global notify_X, X_account, X_password, X_API_key, X_API_secret, X_access_token, X_access_secret
    global notify_bluesky, Bluesky_account, Bluesky_password

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

    # Discord設定
    obs.obs_properties_add_bool(props, "notify_discord", "Discordに通知を送る")
    obs.obs_properties_add_text(props, "webhook_url", "Webhook URL", obs.OBS_TEXT_PASSWORD)

    return props
