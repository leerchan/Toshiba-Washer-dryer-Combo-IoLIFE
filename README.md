# Toshiba Washer-dryer Combo IoLIFE

[![hacs](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories)

Home Assistant integration for Japanese-market Toshiba washer-dryers that use the **IoLIFE** app (tested with the TW-127XP2R). It talks to the washer over the LAN using stock [midea-local](https://github.com/midea-lan/midea-local); the IoLIFE account is only used once, during setup, to fetch the washer's LAN key.

[中文说明](#中文说明)

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/leerchan/Toshiba-Washer-dryer-Combo-IoLIFE`, category **Integration**.
2. Search for **Toshiba Washer-dryer Combo IoLIFE**, download it, and restart Home Assistant.
3. Settings → Devices & services → **Add integration** → *Toshiba Washer-dryer Combo IoLIFE*.
4. Enter your IoLIFE email, password and the washer's IP address. Keep the washer powered on (panel lit) during setup.

> **Note:** the built-in *Midea* integration pins a different `midea-local` version. Remove it before installing this one.

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

[`examples/live_activity.yaml`](examples/live_activity.yaml) is an automation that pushes the course progress to the Home Assistant Companion app as an iOS Live Activity / Android live notification. Paste it into a new automation (Edit in YAML) and change `notify_target` to your phone.

## Development

```bash
pip install -r requirements_test.txt
pytest tests
```

---

## 中文说明

适用于使用 **IoLIFE** App 的日版东芝洗烘一体机（已在 TW-127XP2R 上验证）。通过局域网直连洗衣机，IoLIFE 账号只在添加集成时用一次，用来获取洗衣机的局域网密钥。

**安装：** HACS → ⋮ → 自定义存储库 → 填入 `https://github.com/leerchan/Toshiba-Washer-dryer-Combo-IoLIFE`，类别选「集成」→ 下载 → 重启 HA → 设置 → 设备与服务 → 添加集成 → 搜索 *Toshiba Washer-dryer Combo IoLIFE*，填写 IoLIFE 邮箱、密码和洗衣机 IP。添加时洗衣机需开机（面板亮着）。

**注意：** HA 自带的 Midea 集成锁定了另一个版本的 midea-local，需先删除。

洗衣机关机后 Wi-Fi 会休眠，实体显示「不可用」，开机后 5 秒内恢复。实时活动通知示例见 [`examples/live_activity.yaml`](examples/live_activity.yaml)。

## License

MIT
