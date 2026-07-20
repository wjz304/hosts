# hosts

## 简介

每日自动解析并生成常用服务的 hosts 文件，支持 **GitHub**、**Docker**、**TinyMediaManager (TMM)** 和 **Synology (DSM)** 域名组。

## 直接使用 hosts 文件

hosts Url:
- Raw Url: https://raw.githubusercontent.com/wjz304/hosts/main/hosts
- CDN Url: https://gcore.jsdelivr.net/gh/wjz304/hosts@main/hosts
- CDN Url: https://cdn.staticaly.com/gh/wjz304/hosts/main/hosts (推荐)

### Windows / macOS
推荐使用 [SwitchHosts](https://swh.app/zh) 管理 hosts 文件。

### Linux
```bash
# 删除旧数据
sudo sed -i '/# ING Hosts Start/,/# ING Hosts End/d' /etc/hosts

# 添加（任选其一）
curl -s -k -L https://raw.githubusercontent.com/wjz304/hosts/main/hosts | sudo tee -a /etc/hosts
```

---

## 本地脚本 `hosts.py`

支持通过 DoH（DNS over HTTPS）解析域名，可直接写入系统 hosts 文件。

### 环境要求

```bash
pip install requests
```

### 基本用法

```bash
# 显示帮助信息
python hosts.py

# 生成并写入系统 hosts（需要管理员权限）
python hosts.py --create

# 指定 DNS 提供商和记录类型
python hosts.py --create --dns Google --type A
python hosts.py --create --dns Aliyun --type AAAA

# 预览（只打印不写入）
python hosts.py --dry-run

# 写入自定义路径
python hosts.py --create --output ./my-hosts

# 移除已生成的标记段
python hosts.py --remove

# 查看所有分组
python hosts.py --list-groups

# 新增分组
python hosts.py --add-group MyGroup

# 删除分组
python hosts.py --del-group MyGroup

# 向已有分组添加域名
python hosts.py --add-domain GitHub my-new-domain.com

# 从分组移除域名
python hosts.py --del-domain Docker some-old-image.io
```

### 当前默认分组

- **GitHub** — github.com, api.github.com, raw.githubusercontent.com 等 ~45 个域名
- **Docker** — hub.docker.com, ghcr.io, gcr.io, quay.io 等
- **TMM** — themoviedb.org, tmdb.org, opensubtitles.org, fanart.tv 等
- **DSM** — synology.com, synology.cn, global.synologydownload.com 等

## 跨平台定时任务

通过系统定时任务定期运行 `hosts.py --create`，自动更新 hosts 文件。

### Linux / macOS (cron)

```bash
# 编辑 crontab（需要 sudo 写入 /etc/hosts）
crontab -e

# 每 6 小时执行一次（00:00, 06:00, 12:00, 18:00）
0 0,6,12,18 * * * cd /path/to/hosts && python hosts.py --create --output /etc/hosts
```

### macOS (launchd)

> 写入 `/etc/hosts` 需要 root 权限。推荐使用 **LaunchDaemon**（系统级），它以 root 运行，无需额外提权。

创建 `/Library/LaunchDaemons/com.hosts.update.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hosts.update</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/hosts.py</string>
        <string>--create</string>
        <string>--output</string>
        <string>/etc/hosts</string>
    </array>
    <key>StartInterval</key>
    <integer>21600</integer>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

```bash
# 安装（需要 sudo）
sudo cp com.hosts.update.plist /Library/LaunchDaemons/
sudo chown root:wheel /Library/LaunchDaemons/com.hosts.update.plist
sudo chmod 644 /Library/LaunchDaemons/com.hosts.update.plist

# 加载
sudo launchctl load -w /Library/LaunchDaemons/com.hosts.update.plist

# 卸载
sudo launchctl unload -w /Library/LaunchDaemons/com.hosts.update.plist
```

### Windows (计划任务)

```powershell
# 以管理员身份打开 PowerShell，创建每天 6 小时执行一次的计划任务

$taskName = "HostsAutoUpdate"
$action = New-ScheduledTaskAction -Execute "python" -Argument "-u C:\path\to\hosts.py --create"
$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Hours 6) -StartBoundary (Get-Date -Hour 0 -Minute 0 -Second 0)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Auto update hosts file every 6 hours" -RunLevel Highest
```

查看/删除任务：

```powershell
# 查看任务
Get-ScheduledTask | Where-Object { $_.TaskName -eq 'HostsAutoUpdate' }

# 删除任务
Unregister-ScheduledTask -TaskName 'HostsAutoUpdate' -Confirm:$false
```
