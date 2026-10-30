# Toshiba Washer-dryer Combo IoLIFE

[![hacs](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories)

Home Assistant integration for Japanese-market Toshiba washer-dryers that use the **IoLIFE** app (tested with the TW-127XP2R). It talks to the washer over the LAN using stock [midea-local](https://github.com/midea-lan/midea-local); the IoLIFE account is only used once, during setup, to fetch the washer's LAN key.

[中文说明](#中文说明) · [日本語](#日本語)

The UI is translated into English, Simplified Chinese and Japanese.

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/leerchan/Toshiba-Washer-dryer-Combo-IoLIFE`, category **Integration**.
2. Search for **Toshiba Washer-dryer Combo IoLIFE**, download it, and restart Home Assistant.
3. Settings → Devices & services → **Add integration** → *Toshiba Washer-dryer Combo IoLIFE*.
4. Enter your IoLIFE email, password and the washer's IP address. Keep the washer powered on (panel lit) during setup.

> **Requires Home Assistant 2026.11 or newer.** The integration needs `midea-local` 14.0.0+, which Home Assistant first ships in 2026.11 (2026.10.x bundles 12.2.0). Older versions cannot load it.

Manual install: copy `custom_components/toshiba_washer` into your `config/custom_components/` and restart.

## Entities

| Entity | Description |
| --- | --- |
| `sensor.washer_status` | idle / standby / start / pause / end |
| `sensor.washer_finish_time` | When the running course ends |
| `sensor.washer_stage` | wash / rinse / spin / dry / soft_keep |
| `sensor.washer_mode` | wash_dry / wash / dry / clean_care / care |
| `sensor.washer_program` | Selected course (standard, fast, tub_clean, …) |
| `sensor.washer_error_code` | Error code (0 = OK) |
| `binary_sensor.washer_door` | Door open |
| `binary_sensor.washer_drain_filter_needs_cleaning` | Drain filter warning |
| `binary_sensor.washer_dryer_filter_needs_cleaning` | Dryer filter warning |

The washer's Wi-Fi sleeps when it is switched off, so entities are *unavailable* until it is turned on; the integration retries every 5 seconds.

Entity IDs assume the device is named "Washer". The integration is read-only: it cannot start or stop courses.

## Live Activity example

[`examples/live_activity.en.yaml`](examples/live_activity.en.yaml) is an automation blueprint that pushes the course progress to the Home Assistant Companion app as an iOS Live Activity / Android live notification. [Import it](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fleerchan%2FToshiba-Washer-dryer-Combo-IoLIFE%2Fblob%2Fmain%2Fexamples%2Flive_activity.en.yaml) (or Settings → Automations & Scenes → Blueprints → Import Blueprint with the file's URL), create an automation from it, then pick the washer's entities and your phone's notify action. Chinese and Japanese versions: [`live_activity.zh-Hans.yaml`](examples/live_activity.zh-Hans.yaml), [`live_activity.ja.yaml`](examples/live_activity.ja.yaml).

## Development

```bash
pip install -r requirements_test.txt
pytest tests
```

---

## 中文说明

适用于使用 **IoLIFE** App 的日版东芝洗烘一体机（已在 TW-127XP2R 上验证）。通过局域网直连洗衣机，IoLIFE 账号只在添加集成时用一次，用来获取洗衣机的局域网密钥。

**安装：** HACS → ⋮ → 自定义存储库 → 填入 `https://github.com/leerchan/Toshiba-Washer-dryer-Combo-IoLIFE`，类别选「集成」→ 下载 → 重启 HA → 设置 → 设备与服务 → 添加集成 → 搜索 *Toshiba Washer-dryer Combo IoLIFE*，填写 IoLIFE 邮箱、密码和洗衣机 IP。添加时洗衣机需开机（面板亮着）。

**注意：需要 Home Assistant 2026.11 或更高版本。** 本集成依赖 midea-local 14.0.0 及以上，HA 从 2026.11 起才内置该版本（2026.10.x 为 12.2.0），旧版 HA 无法加载。

洗衣机关机后 Wi-Fi 会休眠，实体显示「不可用」，开机后 5 秒内恢复。实时活动通知蓝图见 [`examples/live_activity.zh-Hans.yaml`](examples/live_activity.zh-Hans.yaml)：[一键导入](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fleerchan%2FToshiba-Washer-dryer-Combo-IoLIFE%2Fblob%2Fmain%2Fexamples%2Flive_activity.zh-Hans.yaml)后从蓝图创建自动化，选择洗衣机的各个实体和手机的通知动作。

## 日本語

**IoLIFE** アプリに対応した日本向け東芝ドラム式洗濯乾燥機用のインテグレーションです（TW-127XP2R で動作確認済み）。LAN 経由で洗濯機と直接通信し、IoLIFE アカウントは設定時に洗濯機の LAN キーを取得するために一度だけ使います。

**インストール：** HACS → ⋮ → カスタムリポジトリ → `https://github.com/leerchan/Toshiba-Washer-dryer-Combo-IoLIFE` を追加、カテゴリは「インテグレーション」→ ダウンロード → HA を再起動 → 設定 → デバイスとサービス → インテグレーションを追加 → *Toshiba Washer-dryer Combo IoLIFE* を検索し、IoLIFE のメールアドレス・パスワード・洗濯機の IP アドレスを入力します。設定中は洗濯機の電源を入れておいてください（パネル点灯）。

**注意：Home Assistant 2026.11 以降が必要です。** 本インテグレーションは midea-local 14.0.0 以上に依存しており、HA に同梱されるのは 2026.11 からです（2026.10.x は 12.2.0）。それより古い HA では読み込めません。

洗濯機の電源を切ると Wi-Fi がスリープし、エンティティは「利用不可」になります。電源を入れると 5 秒以内に復帰します。ライブアクティビティ通知のブループリントは [`examples/live_activity.ja.yaml`](examples/live_activity.ja.yaml) です。[インポート](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fleerchan%2FToshiba-Washer-dryer-Combo-IoLIFE%2Fblob%2Fmain%2Fexamples%2Flive_activity.ja.yaml)してからブループリントでオートメーションを作成し、洗濯機の各エンティティとスマホの通知アクションを選択してください。

## License

MIT
