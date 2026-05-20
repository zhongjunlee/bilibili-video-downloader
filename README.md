📖 项目简介
BiliDownloader 是一个简单易用的B站视频下载工具，提供了友好的命令行交互界面。用户只需要粘贴视频链接，即可自动完成解析和下载，无需复杂配置。

✨ 主要特性
一键下载 - 粘贴链接即可下载，自动解析BV号

智能画质选择 - 自动检测可用画质，支持1080P/720P/480P

进度可视化 - 实时显示下载进度条

Cookie可选 - 非必须，不配置也可下载（仅限480P）

自动合并 - 集成FFmpeg，自动合并音视频

配置持久化 - Cookie配置自动保存，无需重复输入

🖥️ 运行效果
text
╔══════════════════════════════════════════════════════════╗
║              B站视频下载器 - 一键下载版                   ║
╚══════════════════════════════════════════════════════════╝

请输入B站视频链接: https://www.bilibili.com/video/BV15bLH60E6B/

视频: 还在手动逆向？你OUT了！
开始下载 (1080P)...
视频: [████████████████████████████████] 100.0%
音频: [████████████████████████████████] 100.0%
合并音视频...

✓ 下载完成: ./downloads/还在手动逆向？你OUT了！.mp4
🚀 快速开始
环境要求
Python 3.7 或更高版本

FFmpeg（用于合并音视频）

安装FFmpeg
操作系统	安装方式
Windows	下载 FFmpeg 并添加到系统PATH
macOS	brew install ffmpeg
Linux	sudo apt install ffmpeg
验证安装：

bash
ffmpeg -version
安装依赖
bash
pip install requests
下载运行
bash
# 克隆仓库
git clone https://github.com/zhongjunlee/bilibili-video-downloader.git
cd bilibili-video-downloader

# 运行程序
python bili_downloader.py
📋 使用指南
基础使用
运行 python bili_downloader.py

粘贴B站视频链接（或输入BV号）

等待下载完成

配置Cookie（可选，用于1080P）
如果需要下载1080P高清视频，可以配置Cookie：

登录 bilibili.com

按 F12 打开开发者工具

切换到 Network 标签

刷新页面，点击任意请求

在 Request Headers 中找到 Cookie 字段，复制完整值

运行程序，按提示粘贴Cookie

💡 提示：不配置Cookie也可以正常使用，但只能下载480P及以下画质。

下载的文件在哪里？
所有下载的视频保存在程序运行目录下的 ./downloads/ 文件夹中。

🛠️ 技术实现
核心原理
text
用户链接 → 解析BV号 → 获取视频信息(aid/cid) → WBI签名 → 
调用API获取播放地址 → 下载音视频流 → FFmpeg合并 → 输出MP4
技术要点
技术点	说明
WBI签名	动态从B站首页获取密钥，模拟合法请求
DASH协议	处理音视频分离存储，分别下载后合并
断点续传	支持部分下载恢复
画质检测	自动测试可用画质，选择最佳方案
📁 项目结构
text
bili-downloader/
├── bili_downloader.py   # 主程序
├── README.md            # 项目文档
└── downloads/           # 下载目录（自动创建）
❓ 常见问题
Q1: 提示"未检测到FFmpeg"
解决方法：下载并安装FFmpeg，确保命令行可以运行 ffmpeg -version。

Q2: 下载的只有480P
原因：未配置Cookie或Cookie已过期。

解决方法：按照使用指南配置有效的Cookie即可。

Q3: 提示"SESSDATA"相关错误
原因：Cookie格式不正确或已过期。

解决方法：重新登录B站，复制最新的完整Cookie。

Q4: 下载速度很慢
解决方法：这是B站服务器限速导致的，与工具无关。可以尝试更换网络环境或使用代理。

⚠️ 法律声明
本项目仅限学习和技术研究使用。

学习目的：本项目旨在学习网络请求、API签名、流媒体下载等编程技术，不得用于任何商业用途。

版权声明：B站视频的版权归原作者和bilibili所有。下载的视频请遵守相关法律法规，尊重知识产权。

个人使用：下载的视频仅限个人学习、研究使用，请勿二次传播、修改或用于任何侵权行为。

风险提示：使用本工具下载视频可能违反bilibili的用户协议，由此产生的任何风险与责任由使用者自行承担。

免责声明：项目作者不对因使用本工具导致的任何直接或间接损失承担责任。

📄 开源协议
本项目采用 MIT License 开源协议。

🙏 致谢
感谢 bilibili 提供的平台

感谢 FFmpeg 项目

感谢所有开源社区贡献者
