import obspython as obs
import get_twitch_info

import requests

import threading
import time

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

debug_log = False

SNS_retry_cnt = 5
SNS_retry_interval = 100
REQUEST_TIMEOUT = 10

_TWITTER_URL_CHARS = 23  # Twitter は URL を常に23文字でカウント
_TWEET_MAX = 280


def log(message):
    obs.script_log(obs.LOG_INFO, message)


def debug(message):
    if debug_log:
        obs.script_log(obs.LOG_DEBUG, message)


def _mask_secret(value):
    return "***" if value else "(未設定)"


class _NonRetryableError(Exception):
    pass


def _with_retry(fn, name):
    retry_count = max(SNS_retry_cnt, 1)
    for i in range(retry_count):
        debug(f"{name}への通知送信を試行します。{i + 1}/{retry_count}回目")
        try:
            fn()
            return log(f"{name}に通知を送信しました。")
        except _NonRetryableError as e:
            return log(f"{name}への通知を中断しました: {e}")
        except Exception as e:
            log(f"{name}への通知送信に失敗しました。{i + 1}/{retry_count}回目: {e}")
            if i != retry_count - 1:
                time.sleep(max(SNS_retry_interval, 1))
    log(f"{name}通知の送信を中断しました。")


def _fetch_stream_info():
    print(f"OBS Auto Post ver: {version}\nCreated by shin-hq")
    debug("配信情報の取得を開始します。")

    try:
        get_twitch_info._validate_credentials(twitch_client_id, twitch_client_secret, twitch_acc)
    except ValueError as e:
        return log(f"Twitchの設定が未入力です: {e}")

    try:
        access_token = get_twitch_info.get_access_token(twitch_client_id, twitch_client_secret, debug_log=debug)
        user_id = get_twitch_info.get_user_id(twitch_client_id, access_token, twitch_acc, debug_log=debug)
    except get_twitch_info.TwitchAuthError as e:
        return log(f"Twitch認証に失敗しました。設定を確認してください: {e}")
    except Exception as e:
        return log(f"Twitchのトークン/ユーザーID取得中にエラーが発生しました: {e}")

    max_retry = max(get_info_cnt, 1)
    stream_title, game_name, tags = "", "", []

    for i in range(max_retry):
        debug(f"配信情報(streams)の取得を試行します。{i + 1}/{max_retry}回目")
        try:
            stream_title, game_name, tags = get_twitch_info.get_stream_info(
                twitch_client_id, access_token, user_id, debug_log=debug
            )
        except get_twitch_info.TwitchAuthError as e:
            return log(f"Twitch認証に失敗しました。設定を確認してください: {e}")
        except Exception as e:
            if i == max_retry - 1:
                return log(f"配信情報の取得中にエラーが発生しました: {e}")
            log(f"配信情報の取得に失敗しました。{i + 1}/{max_retry}回目: {e}")
            time.sleep(max(get_info_interval, 1))
            continue

        if stream_title:
            debug(f"配信情報(streams)の取得に成功しました。{i + 1}/{max_retry}回目")
            break

        debug(f"配信情報(streams)がまだ空でした。{i + 1}/{max_retry}回目")
        if i != max_retry - 1:
            time.sleep(max(get_info_interval, 1))

    if not stream_title:
        return log("配信情報が正常に取得出来ず、何回か再試行しましたがダメでした。")

    message = f"{stream_title} ({game_name})"
    url = f"https://www.twitch.tv/{twitch_acc}"
    tags_str = " ".join(f"#{t}" for t in tags)
    log(f"配信情報を取得しました: {message}\nタグ: {tags_str}")

    if notify_bluesky and Bluesky_account and Bluesky_password:
        threading.Thread(target=send_Bluesky_notification, args=(message, tags, url), daemon=True).start()

    if notify_X and X_API_key and X_API_secret and X_access_token and X_access_secret:
        threading.Thread(target=send_X_notification, args=(message, tags_str, url), daemon=True).start()

    if notify_discord and webhook_url:
        threading.Thread(target=send_discord_notification, args=(message, url), daemon=True).start()


def script_description():
    return "配信開始時にX, Blueskyに自動通知するPythonスクリプト。DiscordはWebhookを介して通知します。"


def script_defaults(settings):
    obs.obs_data_set_default_int(settings, "get_info_cnt", 10)
    obs.obs_data_set_default_int(settings, "get_info_interval", 15)
    obs.obs_data_set_default_int(settings, "SNS_retry_cnt", 5)
    obs.obs_data_set_default_int(settings, "SNS_retry_interval", 100)
    obs.obs_data_set_default_bool(settings, "notify_X", False)
    obs.obs_data_set_default_bool(settings, "notify_Bluesky", False)
    obs.obs_data_set_default_bool(settings, "notify_discord", False)
    obs.obs_data_set_default_bool(settings, "debug_log", False)


def script_load(settings):
    debug("script_load: スクリプトを読み込みました。")
    obs.obs_frontend_remove_event_callback(on_event)
    obs.obs_frontend_add_event_callback(on_event)


def on_event(event):
    debug(f"on_event: event={event}")
    if event == obs.OBS_FRONTEND_EVENT_STREAMING_STARTED:
        log("配信が開始されました。情報を取得中... ")
        threading.Thread(target=_fetch_stream_info, daemon=True).start()
    elif event == obs.OBS_FRONTEND_EVENT_STREAMING_STOPPED:
        log("配信が停止されました。")


def send_discord_notification(message, url):
    payload = {"content": f"{message}\n\n{url}"}

    def _send():
        res = requests.post(webhook_url, json=payload, timeout=REQUEST_TIMEOUT)
        if res.status_code != 204:
            raise Exception(f"status={res.status_code}, body={res.text[:200]}")

    debug("Discordへの通知送信を開始します。")
    _with_retry(_send, "Discord")


def send_X_notification(message, tags_str, url):
    try:
        import tweepy
    except Exception as e:
        return log(f"tweepyの読み込みに失敗しました。依存ライブラリをインストールしてください: {e}")

    client = tweepy.Client(
        consumer_key=X_API_key,
        consumer_secret=X_API_secret,
        access_token=X_access_token,
        access_token_secret=X_access_secret,
    )

    # URL は Twitter 側で23文字扱い・280文字制限に収まるようタイトルをトリム
    footer_len = 1 + _TWITTER_URL_CHARS + 2 + len(tags_str)  # \n + url(23) + \n\n + tags
    max_msg = _TWEET_MAX - footer_len
    trimmed = message if len(message) <= max_msg else message[:max(0, max_msg - 3)] + "..."
    tweet_text = f"{trimmed}\n{url}\n\n{tags_str}"

    debug("Xへの通知送信を開始します。")

    def _post():
        try:
            client.create_tweet(text=tweet_text)
        except tweepy.errors.HTTPException as e:
            status = getattr(e, "status_code", "?")
            log(f"X APIエラー HTTP {status}: {e}")
            if status in (401, 403):
                raise _NonRetryableError(
                    f"HTTP {status} 認証/権限エラー。X Developer Portalでアプリ権限とアクセストークンを確認してください。"
                )
            if status == 400:
                raise _NonRetryableError(
                    f"HTTP {status} リクエスト内容が不正です(重複ツイート等の可能性があります)。再試行しても解消しません。"
                )
            if status == 429:
                log("X APIのレート制限(429)に達しました。")
            raise

    _with_retry(_post, "X")


def _normalize_bluesky_account(account):
    normalized = account.strip().lstrip("@")
    if not normalized.lower().endswith(".bsky.social"):
        normalized = f"{normalized}.bsky.social"
    return normalized


def send_Bluesky_notification(message, tags, url):
    try:
        import atproto
    except Exception as e:
        return log(f"atprotoの読み込みに失敗しました。依存ライブラリをインストールしてください: {e}")

    bluesky_account = _normalize_bluesky_account(Bluesky_account)

    def _login_and_send():
        bs_client = atproto.Client()
        bs_client.login(bluesky_account, Bluesky_password)
        builder = atproto.client_utils.TextBuilder().text(f"{message}\n").link(text="Twitch URL", url=url).text("\n\n")
        for tag in tags:
            clean_tag = str(tag).strip().lstrip("#")
            if clean_tag:
                builder = builder.tag(text=f"#{clean_tag}", tag=clean_tag).text(" ")
        bs_client.send_post(builder)

    debug("Blueskyへの通知送信を開始します。")
    _with_retry(_login_and_send, "Bluesky")


def script_update(settings):
    global twitch_acc, twitch_client_id, twitch_client_secret
    global get_info_cnt, get_info_interval
    global SNS_retry_cnt, SNS_retry_interval
    global notify_discord, webhook_url
    global notify_X, X_account, X_password, X_API_key, X_API_secret, X_access_token, X_access_secret
    global notify_bluesky, Bluesky_account, Bluesky_password
    global debug_log

    twitch_acc = obs.obs_data_get_string(settings, "twitch_acc")
    twitch_client_id = obs.obs_data_get_string(settings, "twitch_client_id")
    twitch_client_secret = obs.obs_data_get_string(settings, "twitch_client_secret")
    get_info_cnt = obs.obs_data_get_int(settings, "get_info_cnt")
    get_info_interval = obs.obs_data_get_int(settings, "get_info_interval")
    SNS_retry_cnt = obs.obs_data_get_int(settings, "SNS_retry_cnt")
    SNS_retry_interval = obs.obs_data_get_int(settings, "SNS_retry_interval")

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

    debug_log = obs.obs_data_get_bool(settings, "debug_log")

    debug(
        f"script_update: twitch_acc={twitch_acc or '(未設定)'}, "
        f"twitch_client_id={'設定済み' if twitch_client_id else '(未設定)'}, "
        f"twitch_client_secret={_mask_secret(twitch_client_secret)}, "
        f"get_info_cnt={get_info_cnt}, get_info_interval={get_info_interval}, "
        f"SNS_retry_cnt={SNS_retry_cnt}, SNS_retry_interval={SNS_retry_interval}"
    )
    debug(f"script_update: notify_discord={notify_discord}, webhook_url={_mask_secret(webhook_url)}")
    debug(
        f"script_update: notify_X={notify_X}, X_account={X_account or '(未設定)'}, "
        f"X_password={_mask_secret(X_password)}, X_API_key={_mask_secret(X_API_key)}, "
        f"X_API_secret={_mask_secret(X_API_secret)}, X_access_token={_mask_secret(X_access_token)}, "
        f"X_access_secret={_mask_secret(X_access_secret)}"
    )
    debug(
        f"script_update: notify_bluesky={notify_bluesky}, Bluesky_account={Bluesky_account or '(未設定)'}, "
        f"Bluesky_password={_mask_secret(Bluesky_password)}"
    )


def _run_connection_test():
    log("=== 接続テストを開始します ===")

    if twitch_client_id and twitch_client_secret and twitch_acc:
        try:
            user_id = get_twitch_info.test_twitch_connection(
                twitch_client_id, twitch_client_secret, twitch_acc, debug_log=debug
            )
            log(f"[OK] Twitch: 認証・ユーザーID取得に成功しました (user_id={user_id})")
        except Exception as e:
            log(f"[NG] Twitch: {e}")
    else:
        log("[--] Twitch: 未設定のためスキップしました。")

    if notify_discord and webhook_url:
        try:
            res = requests.get(webhook_url, timeout=REQUEST_TIMEOUT)
            if res.status_code == 200:
                log("[OK] Discord: Webhook URLへの接続に成功しました。")
            else:
                log(f"[NG] Discord: Webhook URLの応答が異常です (status={res.status_code})")
        except Exception as e:
            log(f"[NG] Discord: {e}")
    else:
        log("[--] Discord: 未設定または無効のためスキップしました。")

    if notify_X and X_API_key and X_API_secret and X_access_token and X_access_secret:
        try:
            import tweepy

            client = tweepy.Client(
                consumer_key=X_API_key,
                consumer_secret=X_API_secret,
                access_token=X_access_token,
                access_token_secret=X_access_secret,
            )
            client.get_me()
            log("[OK] X: 認証に成功しました。")
        except Exception as e:
            log(f"[NG] X: {e}")
    else:
        log("[--] X: 未設定または無効のためスキップしました。")

    if notify_bluesky and Bluesky_account and Bluesky_password:
        try:
            import atproto

            bluesky_account = _normalize_bluesky_account(Bluesky_account)
            atproto.Client().login(bluesky_account, Bluesky_password)
            log("[OK] Bluesky: ログインに成功しました。")
        except Exception as e:
            log(f"[NG] Bluesky: {e}")
    else:
        log("[--] Bluesky: 未設定または無効のためスキップしました。")

    log("=== 接続テストを終了します ===")


def on_test_connection_clicked(props, prop):
    threading.Thread(target=_run_connection_test, daemon=True).start()
    return False


def script_properties():
    props = obs.obs_properties_create()

    obs.obs_properties_add_bool(props, "debug_log", "デバッグログを有効にする")

    obs.obs_properties_add_int(props, "SNS_retry_cnt", "SNS通知リトライ回数", 1, 30, 1)
    obs.obs_properties_add_int(props, "SNS_retry_interval", "SNS通知リトライ間隔 (秒)", 1, 600, 1)

    obs.obs_properties_add_text(props, "twitch_acc", "Twitch Account ID", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "twitch_client_id", "Twitch Client ID", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "twitch_client_secret", "Twitch Client Secret", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_int(props, "get_info_cnt", "配信情報取得リトライ回数", 1, 30, 1)
    obs.obs_properties_add_int(props, "get_info_interval", "配信情報取得リトライ間隔 (秒)", 1, 300, 1)

    obs.obs_properties_add_bool(props, "notify_X", "Xに通知を送る")
    obs.obs_properties_add_text(props, "X_account", "Xのアカウント名", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "X_password", "Xのパスワード", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "X_API_key", "XのAPIキー", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "X_API_secret", "XのシークレットAPIキー", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "X_access_token", "Xのアクセストークン", obs.OBS_TEXT_PASSWORD)
    obs.obs_properties_add_text(props, "X_access_secret", "Xのシークレットトークン", obs.OBS_TEXT_PASSWORD)

    obs.obs_properties_add_bool(props, "notify_Bluesky", "Blueskyに通知を送る")
    obs.obs_properties_add_text(props, "Bluesky_account", "Blueskyのアカウント名", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "Bluesky_password", "Blueskyのパスワード", obs.OBS_TEXT_PASSWORD)

    obs.obs_properties_add_bool(props, "notify_discord", "Discordに通知を送る")
    obs.obs_properties_add_text(props, "webhook_url", "Webhook URL", obs.OBS_TEXT_PASSWORD)

    obs.obs_properties_add_button(props, "test_connection", "接続テスト", on_test_connection_clicked)

    return props
