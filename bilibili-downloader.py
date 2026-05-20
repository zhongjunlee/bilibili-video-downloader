#!/usr/bin/env python3
"""
B站视频下载器 - 产品化版本
用户只需提供链接，自动完成解析和下载
"""

import re
import json
import time
import hashlib
import os
import sys
import subprocess
import requests
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# ==================== 配置管理 ====================

CONFIG_FILE = Path.home() / ".bili_downloader_config.json"


def load_config():
    """加载配置文件"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def setup_cookie():
    """引导用户设置Cookie"""
    print("\n" + "=" * 50)
    print("Cookie 配置（可选）")
    print("=" * 50)
    print("配置Cookie后可以下载1080P高清视频")
    print("不配置则只能下载480P及以下画质")
    print()

    choice = input("是否配置Cookie？(y/n，默认n): ").strip().lower()
    if choice != 'y':
        return None

    print("\n如何获取Cookie：")
    print("1. 用Chrome/Edge打开bilibili.com并登录")
    print("2. 按F12打开开发者工具")
    print("3. 切换到 Network 标签页")
    print("4. 刷新页面，点击任意请求")
    print("5. 在 Request Headers 中找到 Cookie 字段")
    print("6. 复制整个Cookie值（很长）")
    print()

    cookie = input("请粘贴Cookie（直接回车跳过）: ").strip()
    if cookie and 'SESSDATA' in cookie:
        config = load_config()
        config['cookie'] = cookie
        save_config(config)
        print("✓ Cookie已保存")
        return cookie
    else:
        print("✗ Cookie无效或未包含SESSDATA，将使用无Cookie模式")
        return None


def get_cookie():
    """获取已保存的Cookie"""
    config = load_config()
    return config.get('cookie')


# ==================== 链接解析 ====================

def extract_bv_id(url_or_bv):
    """从用户输入中提取BV号"""
    # 已经是BV号格式
    if re.match(r'^BV[a-zA-Z0-9]{10}$', url_or_bv):
        return url_or_bv

    # 提取URL中的BV号
    patterns = [
        r'BV[a-zA-Z0-9]{10}',
        r'bilibili\.com/video/(BV[a-zA-Z0-9]{10})',
        r'b23\.tv/\w+',
    ]

    for pattern in patterns:
        match = re.search(pattern, url_or_bv)
        if match:
            bv = match.group(1) if '(' in pattern else match.group(0)
            if bv.startswith('BV'):
                return bv

    print("✗ 无法解析BV号，请输入正确的B站视频链接")
    return None


# ==================== 核心下载逻辑 ====================

class BilibiliDownloader:
    """B站视频下载器"""

    # 画质映射表
    QUALITY_MAP = {
        80: "1080P",
        64: "720P",
        32: "480P",
        16: "360P",
        112: "1080P高码率(大会员)",
        116: "4K(大会员)"
    }

    def __init__(self, cookie_str=None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com/'
        })
        if cookie_str:
            self.session.headers['Cookie'] = cookie_str
        self.wbi_keys = None
        self.available_qualities = []  # 存储可用画质

    def get_wbi_keys(self):
        """获取WBI签名密钥"""
        try:
            resp = self.session.get('https://www.bilibili.com/')
            match = re.search(r'wbi_img_url:"//(.*?\.js)"', resp.text)
            if match:
                js_url = 'https://' + match.group(1)
                js_resp = self.session.get(js_url)
                img_key = re.search(r'img_key:"(.*?)"', js_resp.text)
                sub_key = re.search(r'sub_key:"(.*?)"', js_resp.text)
                if img_key and sub_key:
                    mixed = img_key.group(1) + sub_key.group(1)
                    self.wbi_keys = mixed[:32]
                    return self.wbi_keys
            self.wbi_keys = "ea1db124af3c7062474693fa704f4ff8"
            return self.wbi_keys
        except:
            self.wbi_keys = "ea1db124af3c7062474693fa704f4ff8"
            return self.wbi_keys

    def sign_wbi(self, params):
        """添加WBI签名"""
        if not self.wbi_keys:
            self.get_wbi_keys()
        params['wts'] = int(time.time())
        sorted_keys = sorted(params.keys())
        query = '&'.join([f'{k}={params[k]}' for k in sorted_keys])
        params['w_rid'] = hashlib.md5((query + self.wbi_keys).encode()).hexdigest()
        return params

    def get_video_info(self, bv_id):
        """获取视频基本信息"""
        url = f'https://www.bilibili.com/video/{bv_id}'
        try:
            resp = self.session.get(url)
            resp.raise_for_status()

            match = re.search(r'window\.__INITIAL_STATE__=({.*?});', resp.text)
            if match:
                data = json.loads(match.group(1))
                video_data = data.get('videoData', {})
                pages = video_data.get('pages', [])

                if pages:
                    return {
                        'aid': video_data.get('aid'),
                        'bvid': bv_id,
                        'cid': pages[0].get('cid'),
                        'title': video_data.get('title', '未命名'),
                        'part_title': pages[0].get('part', ''),
                        'duration': video_data.get('duration', 0)
                    }
            return None
        except Exception as e:
            print(f"获取视频信息失败: {e}")
            return None

    def check_available_qualities(self, aid, cid):
        """检测哪些画质可用（通过测试API返回值）"""
        available = []

        # 按从高到低的顺序测试画质
        for qn in [112, 80, 64, 32, 16]:
            api_url = 'https://api.bilibili.com/x/player/playurl'
            params = {
                'avid': aid,
                'cid': cid,
                'qn': qn,
                'fnval': 4048,
                'fourk': 1,
            }
            signed = self.sign_wbi(params.copy())

            try:
                resp = self.session.get(api_url, params=signed)
                data = resp.json()
                if data.get('code') == 0:
                    dash = data.get('data', {}).get('dash', {})
                    if dash.get('video') and dash['video'][0].get('base_url'):
                        available.append(qn)
            except:
                pass

            time.sleep(0.3)  # 避免请求过快

        return available

    def get_play_url(self, aid, cid, quality):
        """获取下载地址"""
        api_url = 'https://api.bilibili.com/x/player/playurl'
        params = {
            'avid': aid,
            'cid': cid,
            'qn': quality,
            'fnval': 4048,
            'fourk': 1,
        }
        signed = self.sign_wbi(params)

        resp = self.session.get(api_url, params=signed)
        data = resp.json()

        if data.get('code') != 0:
            return None, None

        dash = data.get('data', {}).get('dash', {})
        videos = dash.get('video', [])
        audios = dash.get('audio', [])

        if videos and audios:
            return videos[0].get('base_url'), audios[0].get('base_url')
        return None, None

    def download_file(self, url, filepath, desc, callback=None):
        """下载文件，支持进度回调"""
        try:
            resp = self.session.get(url, stream=True)
            resp.raise_for_status()

            total = int(resp.headers.get('content-length', 0))
            downloaded = 0

            with open(filepath, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if callback and total > 0:
                            callback(desc, downloaded, total)

            return True
        except Exception as e:
            print(f"\n下载失败: {e}")
            return False

    def merge(self, video_path, audio_path, output_path):
        """合并音视频"""
        try:
            subprocess.run([
                'ffmpeg', '-i', video_path, '-i', audio_path,
                '-c:v', 'copy', '-c:a', 'aac', '-y', output_path
            ], check=True, capture_output=True)
            return True
        except:
            print("合并失败，请确保已安装FFmpeg")
            return False

    def download_video(self, bv_id, quality=80, output_dir='./downloads'):
        """完整的下载流程"""
        # 1. 获取视频信息
        info = self.get_video_info(bv_id)
        if not info:
            return False

        print(f"\n视频: {info['title']}")

        # 2. 检测可用画质
        print("检测可用画质...")
        available = self.check_available_qualities(info['aid'], info['cid'])

        if quality not in available:
            quality = available[0] if available else 32
            print(f"请求的画质不可用，将使用: {self.QUALITY_MAP.get(quality, '未知')}")

        # 3. 获取下载地址
        video_url, audio_url = self.get_play_url(info['aid'], info['cid'], quality)
        if not video_url:
            print("获取下载地址失败")
            return False

        # 4. 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        safe_title = re.sub(r'[\\/*?:"<>|]', '_', info['title'])
        temp_video = os.path.join(output_dir, f'{safe_title}_video.tmp')
        temp_audio = os.path.join(output_dir, f'{safe_title}_audio.tmp')
        output_file = os.path.join(output_dir, f'{safe_title}.mp4')

        # 5. 下载
        print(f"\n开始下载 ({self.QUALITY_MAP.get(quality, '未知')})...")

        def progress_callback(desc, current, total):
            percent = current / total * 100
            bar_len = 30
            filled = int(bar_len * current / total)
            bar = '█' * filled + '░' * (bar_len - filled)
            print(f'\r{desc}: [{bar}] {percent:.1f}%', end='')

        if not self.download_file(video_url, temp_video, "视频", progress_callback):
            return False
        print()

        if not self.download_file(audio_url, temp_audio, "音频", progress_callback):
            return False
        print()

        # 6. 合并
        print("合并音视频...")
        if self.merge(temp_video, temp_audio, output_file):
            os.remove(temp_video)
            os.remove(temp_audio)
            print(f"\n✓ 下载完成: {output_file}")
            return True

        return False


# ==================== 主程序 ====================

def show_banner():
    """显示程序横幅"""
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║              B站视频下载器 - 一键下载版                   ║
║                                                          ║
║  只需粘贴链接，自动解析下载，无需手动配置                 ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)


def main():
    show_banner()

    # 检查FFmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except:
        print("[!] 未检测到FFmpeg，请先安装FFmpeg并添加到PATH")
        print("    下载地址: https://ffmpeg.org/download.html")
        input("按回车键退出...")
        return

    # 获取Cookie（可选）
    cookie = get_cookie()
    if not cookie:
        cookie = setup_cookie()

    downloader = BilibiliDownloader(cookie)

    while True:
        print("\n" + "-" * 50)
        url = input("请输入B站视频链接 (或输入 q 退出): ").strip()

        if url.lower() == 'q':
            print("再见！")
            break

        if not url:
            continue

        # 提取BV号
        bv_id = extract_bv_id(url)
        if not bv_id:
            continue

        # 执行下载
        success = downloader.download_video(bv_id, quality=80)

        if success:
            print("\n下载成功！文件保存在 ./downloads 目录")
        else:
            print("\n下载失败，请检查网络或链接是否正确")


if __name__ == "__main__":
    main()