# OBS Auto Post

OBS Studioで配信を開始した際に、X (旧Twitter)、Bluesky、Discordへ自動的に開始通知を投稿するPythonスクリプトです。

## セットアップ

### ① Python 3.10.11のインストール (Windows 64bit版)

1. [Python公式サイト](https://www.python.org/downloads/windows/) から「Python 3.10.11 Windows installer (64-bit)」をダウンロードし、実行します。
2. インストーラーの最初の画面で、**「Add Python 3.10 to PATH」に必ずチェックを入れてください。** コマンドプロンプトからPythonを実行できるようになります。
3. 「Install Now」をクリックし、インストールを完了させます。
4. インストール後、コマンドプロンプトで以下を実行し、正しくインストールされたか確認します。

   ```
   python --version
   ```

   バージョンが「Python 3.10.11」と表示されれば成功です。

### ② 必要なPythonライブラリのインストール

スクリプトが依存するPythonライブラリをインストールします。同梱の `library_install.bat` を実行してください。

### ③ OBSのPythonフォルダパスの設定

1. OBS Studioを開きます。
2. メニューバーから「ツール」→「スクリプト」を選択します。
3. スクリプトウィンドウ下部にある「Python Path」の欄に、Python 3.10.11がインストールされているフォルダのパスを入力します。通常は以下のパスです。

   ```
   %USERPROFILE%\AppData\Local\Programs\Python\Python310
   ```

   このパスは、エクスプローラーのアドレスバーに直接入力して開くことができます。

### ④ OBSの再起動

Pythonパスの設定を反映させるため、OBS Studioを一度完全に終了し、再起動してください。

### ⑤ スクリプトファイルの配置とOBSへの登録

1. `OBS_Auto_Post.py` と `get_twitch_info.py` の2つのファイルを、任意の同じフォルダに配置します(例: デスクトップ上に新しいフォルダを作成してその中に入れる)。
2. OBS Studioを起動し、再び「ツール」→「スクリプト」を開きます。
3. スクリプトウィンドウの左下にある「+」ボタンをクリックし、先ほど配置した `OBS_Auto_Post.py` ファイルを選択して追加します。

### ⑥ 各種サービスAPI情報の入力

OBSのスクリプト設定画面で、各サービスのAPI情報を入力します。各サービスのアカウントを事前に準備してください。

#### Twitch API設定

1. [Twitch Developerサイト](https://dev.twitch.tv/) にログインします。
2. ダッシュボードから「Applications」に移動し、「Register Your Application」をクリックします。
3. アプリケーション登録画面で、以下の情報を入力します。
   - **Name**: アプリケーションの名前 (例: OBS Auto Post)
   - **OAuth Redirect URLs**: `https://api.twitch.tv/kraken/oauth2/authorize`
   - **Category**: アプリケーションのカテゴリ (例: Broadcasting Tools)
4. 「Create」をクリックしてアプリケーションを作成します。
5. 作成されたアプリケーションの詳細画面に「Client ID」が表示されます。また「New Secret」をクリックすると「Client Secret」が生成されます。これらを控えておきます。
6. OBS Studioのスクリプト設定画面で、以下の情報を入力します。
   - **Twitch Account ID**: あなたのTwitchユーザー名
   - **Twitch Client ID**: 取得したClient ID
   - **Twitch Client Secret**: 取得したClient Secret

#### X (旧Twitter) API設定

> [!IMPORTANT]
> Xは2026年2月からAPIの新規開発者向け無料枠を廃止しており、X投稿機能を利用するには有料プランへの加入、または従量課金クレジットの購入が必要です。X Developer Portal ([console.x.com](https://console.x.com/)) でプラン・クレジット残高を確認してください。クレジットが枯渇すると投稿はエラー(HTTP 402 "credits depleted")で失敗します。この場合スクリプト側の設定に問題はなく、ポータル側でのクレジット補充・プラン加入が必要です。

X DeveloperサイトでAPIキーなどを取得し、OBSのスクリプト設定に入力します。X APIの利用には、開発者アカウントの申請とプロジェクト・アプリの作成が必要です。

1. [X Developer Portal](https://developer.twitter.com/en/portal/dashboard) にログインします。開発者アカウントをお持ちでない場合は、申請プロセスを完了させてください。
2. ダッシュボードで「Projects & Apps」セクションに移動し、「+ New Project」をクリックして新しいプロジェクトを作成します。
3. プロジェクト作成後、そのプロジェクト内で新しいアプリケーション (App) を作成します。「Add App」または「+ New App」をクリックします。
4. アプリ作成時に、アプリケーションの名前、使用目的などを入力します。
5. 作成したアプリケーションの詳細ページに移動し、「Keys and tokens」タブを選択します。
6. 以下のキーを生成または確認します。
   - **API Key (Consumer Key)**
   - **API Secret (Consumer Secret)**
   - **Access Token** (まだ生成されていない場合は「Generate」または「Regenerate」をクリックして生成)
   - **Access Token Secret** (Access Tokenと同時に生成)

   > [!NOTE]
   > Access TokenとAccess Token Secretを生成する際に、アプリケーションの「User authentication settings」で「App permissions」を「Read and write」に設定し、OAuth 1.0aを有効にしていることを確認してください。また、生成されたキーは一度しか表示されないため、必ず控えておいてください。

7. OBS Studioのスクリプト設定画面で「Xに通知を送る」にチェックを入れ、以下の情報を入力します。
   - **Xのアカウント名**: あなたのXのユーザー名 (例: `@your_username`)
   - **Xのパスワード**: あなたのXのパスワード
   - **XのAPIキー**: 取得したAPI Key
   - **XのシークレットAPIキー**: 取得したAPI Secret
   - **Xのアクセストークン**: 取得したAccess Token
   - **Xのシークレットトークン**: 取得したAccess Token Secret

#### Bluesky API設定

OBS Studioのスクリプト設定画面で「Blueskyに通知を送る」にチェックを入れ、以下の情報を入力します。

- **Blueskyのアカウント名**: あなたのBlueskyハンドル (例: `yourname.bsky.social`)
- **Blueskyのパスワード**: あなたのBlueskyのパスワード

#### Discord Webhook URL設定

1. Discordを開き、通知を送信したいサーバーのチャンネルを右クリックします。
2. 「チャンネル設定」→「連携サービス」→「Webhook」を選択し、新しいWebhookを作成します。
3. 作成したWebhookの「Webhook URLをコピー」をクリックします。
4. OBS Studioのスクリプト設定画面で「Discordに通知を送る」にチェックを入れ、以下の情報を入力します。
   - **Webhook URL**: コピーしたDiscordのWebhook URL

## 使い方

### 接続テストの実行(推奨)

各種API情報を入力したら、配信を開始する前に動作確認を行うことをおすすめします。OBSのスクリプト設定画面の一番下にある「接続テスト」ボタンをクリックすると、Twitch・Discord・X・Blueskyのうち設定済みのサービスについてのみ接続確認を行います(実際の投稿は行いません)。結果はスクリプトウィンドウ下部のログ出力エリアに `[OK]` (成功)・`[NG]` (失敗)・`[--]` (未設定のためスキップ)として表示されます。

> [!TIP]
> スクリプト設定画面の上部にある「デバッグログを有効にする」にチェックを入れると、配信情報の取得やSNS通知送信の詳細な処理状況がログ出力エリアに表示されるようになります。うまく動作しない場合の原因調査に役立ちます。

### 配信の開始

すべての設定が完了したら、あとはOBS Studioで配信を開始するだけです。配信が開始されると、自動的に設定したプラットフォームに通知が投稿されます。

> [!TIP]
> スクリプトの動作状況は、OBS Studioの「ツール」→「スクリプト」ウィンドウの下部にあるログ出力エリアで確認できます。
