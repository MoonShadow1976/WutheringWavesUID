import os
import time
import asyncio
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from urllib.parse import urljoin

import httpx
from gsuid_core.logger import logger

from gsuid_core.utils.download_resource.download_file import download

# 全局缓存
global_tag, global_url = '', ''
NOW_SPEED_TEST = False

# GitHub Raw 镜像源列表 (可扩展)
GITHUB_MIRRORS = [
    ("[GitHub Raw]", "https://raw.githubusercontent.com"),
    ("[GitHub Mirror CN]", "https://raw.gitmirror.com"),
    ("[GitHub Mirror Fast]", "https://ghproxy.com/https://raw.githubusercontent.com"),
    ("[GitHub Mirror]", "https://raw.fastgit.org"),
]

# 仓库信息 (可配置)
GITHUB_REPO_OWNER = "MoonShadow1976"
GITHUB_REPO_NAME = "WutheringWaves_OverSea_StaticAssets"
GITHUB_BRANCH = "main"

# JSON索引路径 (扁平化结构)
INDEX_PATHS = {
    "resource": "data/resource.json",  # 顶层索引
    # 子目录索引: data/resource/xxx.json
}


async def test_mirror_speed(tag: str, base_url: str) -> Tuple[str, str, float]:
    """测试单个GitHub镜像源速度"""
    test_file = f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{GITHUB_BRANCH}/{INDEX_PATHS['resource']}"
    url = f"{base_url.rstrip('/')}/{test_file}"
    
    async with httpx.AsyncClient() as client:
        try:
            start_time = time.time()
            response = await client.get(url, timeout=10.0)
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                logger.debug(f'⌛ [测速] {tag} {base_url} 延时: {elapsed_time:.2f}s')
                return tag, base_url, elapsed_time
            else:
                logger.info(f'⚠ {tag} {base_url} 测试文件状态码: {response.status_code}')
        except Exception as e:
            logger.info(f'⚠ {tag} {base_url} 连接错误: {str(e)[:50]}...')
    
    return tag, base_url, float('inf')


async def check_speed():
    """测速选择最快的GitHub镜像源 (保持原有接口)"""
    global global_tag, global_url, NOW_SPEED_TEST
    
    if (not global_tag or not global_url) and not NOW_SPEED_TEST:
        NOW_SPEED_TEST = True
        logger.info('[WWCore资源下载]测速中...')
        
        # 并发测试所有镜像源
        tasks = []
        for tag, base_url in GITHUB_MIRRORS:
            tasks.append(asyncio.create_task(test_mirror_speed(tag, base_url)))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        fastest_tag = ''
        fastest_url = ''
        fastest_time = float('inf')
        
        for result in results:
            if isinstance(result, (Exception, BaseException)):
                continue
            tag, base_url, elapsed = result
            if elapsed < fastest_time:
                fastest_time = elapsed
                fastest_tag = tag
                fastest_url = base_url
        
        # 构建完整的资源站URL
        if fastest_url:
            global_url = f"{fastest_url.rstrip('/')}/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{GITHUB_BRANCH}"
            global_tag = fastest_tag
            logger.info(f"🚀 最快资源站: {global_tag} {global_url}")
        else:
            # 如果所有镜像都失败，使用主站作为后备
            global_url = f"https://raw.githubusercontent.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{GITHUB_BRANCH}"
            global_tag = "[GitHub Raw]"
            logger.warning(f"⚠ 所有镜像测速失败，使用主站: {global_tag}")
        
        NOW_SPEED_TEST = False
        return global_tag, global_url
    
    if NOW_SPEED_TEST:
        while NOW_SPEED_TEST:
            await asyncio.sleep(0.5)
    
    return global_tag, global_url


async def fetch_json_index(client: httpx.AsyncClient, base_url: str, json_path: str) -> Optional[Dict]:
    """获取并解析JSON索引文件"""
    url = f"{base_url.rstrip('/')}/{json_path}"
    try:
        response = await client.get(url, timeout=30.0)
        if response.status_code == 200:
            return json.loads(response.text)
    except Exception as e:
        logger.warning(f"获取JSON索引失败 {url}: {e}")
    return None


async def download_with_json_index(
    base_url: str,
    tag: str,
    endpoint: str,
    local_path: Path,
    client: httpx.AsyncClient,
    plugin_name: str
):
    """使用JSON索引下载单个目录的资源"""
    
    # 从endpoint提取目录名（用于查找JSON索引）
    # endpoint格式: "resource/avatar" -> 目录名: "avatar"
    dir_name = endpoint.split('/')[-1] if '/' in endpoint else endpoint
    
    # 获取目录的JSON索引
    dir_json_path = f"data/resource/{dir_name}.json"
    dir_json = await fetch_json_index(client, base_url, dir_json_path)
    
    if not dir_json:
        logger.warning(f'{tag} {endpoint} 无法获取JSON索引: {dir_json_path}')
        return
    
    # 统计信息
    files = dir_json.get("files", [])
    total_files = len(files)
    exist_files = 0
    need_download_files = 0
    logger.info(f'{tag} 目录 {endpoint} 中有 {total_files} 个文件待检查')
    
    # 准备下载任务
    download_tasks = []
    
    for file_info in files:
        # file_info中的path是相对于data/resource/的完整路径
        # 例如: "avatar/1001.png" 或 "avatar/special/1003.png"
        file_relative_path = file_info["path"]
        remote_size = file_info.get("size", 0)
        
        # 从完整的相对路径中移除目录名前缀
        # 例如: "avatar/1001.png" -> 去掉 "avatar/" -> "1001.png"
        # 例如: "avatar/special/1003.png" -> 去掉 "avatar/" -> "special/1003.png"
        if file_relative_path.startswith(dir_name + "/"):
            # 移除目录名前缀和后面的斜杠
            local_relative_path = file_relative_path[len(dir_name)+1:]
        else:
            # 如果不以目录名开头，可能是其他情况，使用文件名
            local_relative_path = file_info["name"]
        
        # 构建本地完整路径
        local_file_path = local_path / local_relative_path
        
        # 检查文件是否存在且大小匹配
        file_exists = local_file_path.exists()
        
        if file_exists:
            exist_files += 1
            local_size = local_file_path.stat().st_size
            
            if local_size == remote_size:
                # 文件存在且大小一致，跳过下载
                continue
            else:
                # 文件存在但大小不一致，需要重新下载
                logger.debug(f'{tag}🔄 文件大小不一致: {file_relative_path} (本地: {local_size}, 远程: {remote_size})')
                need_download_files += 1
        else:
            # 文件不存在，需要下载
            need_download_files += 1
            # 确保目录存在
            local_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 构建下载URL
        file_url = f"{base_url.rstrip('/')}/data/resource/{file_relative_path}"
        
        logger.info(f'{tag} {plugin_name} 开始下载 {file_relative_path}')
        
        # 创建下载任务
        task = asyncio.create_task(
            download(file_url, local_file_path.parent, local_file_path.name, client, tag)
        )
        download_tasks.append(task)
        
        # 批次控制
        if len(download_tasks) >= 5:  # 每批5个任务
            await asyncio.gather(*download_tasks)
            download_tasks.clear()
    
    # 执行剩余下载任务
    if download_tasks:
        await asyncio.gather(*download_tasks)
    
    # 输出统计信息
    logger.info(f'{tag} 目录 {endpoint} 检查完成:')
    logger.info(f'  总数: {total_files}, 已存在: {exist_files}, 需下载: {need_download_files}')
    
    if need_download_files == 0:
        logger.success(f'{tag} 目录 {endpoint} 所有文件已是最新!')


async def download_all_file(
    plugin_name: str,
    EPATH_MAP: Dict[str, Path],
    URL: Optional[str] = None,
    TAG: Optional[str] = None,
):
    """主下载函数 (接口保持不变)"""
    
    # 1. 确定资源站URL和TAG
    if URL:
        TAG, BASE_URL = TAG or '[Unknown]', URL
    else:
        TAG, BASE_URL = await check_speed()
        if not BASE_URL:
            logger.error("❌ 无法获取可用的资源站")
            return
    
    logger.info(f'🔗 使用资源站: {TAG}')
    
    # 2. 获取顶层资源索引，验证目录存在
    async with httpx.AsyncClient(timeout=httpx.Timeout(200.0)) as client:
        # 获取顶层索引
        resource_json = await fetch_json_index(client, BASE_URL, INDEX_PATHS['resource'])
        if not resource_json:
            logger.error('❌ 无法获取顶层资源索引，可能索引文件未生成')
            return
        
        available_dirs = resource_json.get('directories', [])
        
        # 3. 遍历所有endpoint进行下载
        processed_count = 0
        for endpoint, local_path in EPATH_MAP.items():
            # 提取目录名
            dir_name = endpoint.split('/')[-1] if '/' in endpoint else endpoint
            
            # 检查目录是否在索引中
            if dir_name not in available_dirs:
                logger.warning(f'⚠ 目录 {dir_name} 不在资源索引中，跳过')
                continue
            
            # 确保本地目录存在
            local_path.mkdir(parents=True, exist_ok=True)
            
            # 下载该目录资源
            await download_with_json_index(
                BASE_URL, TAG, endpoint, local_path, client, plugin_name
            )
            processed_count += 1
        
        # 4. 最终状态
        if processed_count == len(EPATH_MAP):
            logger.success(f'🍱 [资源检查] 插件 {plugin_name} 所有资源已是最新!')
        elif processed_count > 0:
            logger.info(f'📦 [资源检查] 插件 {plugin_name} 已完成 {processed_count}/{len(EPATH_MAP)} 个目录')
        else:
            logger.warning(f'⚠ [资源检查] 插件 {plugin_name} 未找到任何匹配的资源目录')