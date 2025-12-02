import time
import asyncio
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

import httpx
from gsuid_core.logger import logger

from gsuid_core.utils.download_resource.download_file import download

# 全局缓存
global_tag, global_url = '', ''
NOW_SPEED_TEST = False

# GitHub Raw 镜像源列表 (可扩展)
GITHUB_MIRRORS = [
    # ("[GitHub Raw]", "https://raw.githubusercontent.com"),
    # ("[GitHub Mirror CN]", "https://raw.gitmirror.com"),
    ("[GitHub Mirror CN-hub]", "https://hub.gitmirror.com/raw.githubusercontent.com"),
    ("[GitHub Mirror j cdn]", "https://cdn.jsdelivr.net/gh"),
    ("[GitHub Mirror j fastly]", "https://fastly.jsdelivr.net/gh"),
    ("[GitHub Mirror j gcore]", "https://gcore.jsdelivr.net/gh"),
    ("[GitHub Mirror fastgit]", "https://raw.fastgit.org"),
    ("[GitHub Mirror ghproxy]", "https://ghproxy.com/https://raw.githubusercontent.com"),
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
    """测速选择最快的GitHub镜像源 (优先使用GitHub Raw，如果可用)"""
    global global_tag, global_url, NOW_SPEED_TEST
    
    if (not global_tag or not global_url) and not NOW_SPEED_TEST:
        NOW_SPEED_TEST = True
        logger.info('[WWCore资源下载]测速中...')
        
        # 第一步：优先测试GitHub Raw（原站）
        raw_tag = "[GitHub Raw]"
        raw_url = "https://raw.githubusercontent.com"
        
        logger.info(f'🔍 优先测试原站: {raw_tag}')
        raw_tag_result, raw_url_result, raw_time = await test_mirror_speed(raw_tag, raw_url)
        
        # 如果GitHub Raw可以访问且速度快于5秒，直接使用
        if raw_time < 5.0:
            logger.info('✅ GitHub Raw可用，直接使用原站')
            global_tag = raw_tag_result
            global_url = f"{raw_url_result.rstrip('/')}/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{GITHUB_BRANCH}"
            NOW_SPEED_TEST = False
            logger.info(f"🚀 使用资源站: {global_tag} {global_url}")
            return global_tag, global_url
        
        # 第二步：如果GitHub Raw不可用，测试所有镜像源
        logger.info('❌ GitHub Raw不可用，开始测试镜像源...')
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
            logger.info(f"🚀 最快镜像源: {global_tag} {global_url}")
        else:
            # 如果所有镜像都失败，仍然使用原站作为后备（即使可能不可用）
            global_url = f"https://raw.githubusercontent.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{GITHUB_BRANCH}"
            global_tag = "[GitHub Raw]"
            logger.warning(f"⚠️ 所有镜像测速失败，使用原站（可能不可用）: {global_tag}")
        
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
    # 从endpoint提取目录名
    dir_name = endpoint.split('/')[-1] if '/' in endpoint else endpoint
    
    # 获取目录的JSON索引
    dir_json_path = f"data/resource/{dir_name}.json"
    dir_json = await fetch_json_index(client, base_url, dir_json_path)
    
    if not dir_json:
        logger.warning(f'{plugin_name} {tag} {endpoint} 无法获取JSON索引: {dir_json_path}')
        return
    
    # 统计信息
    files = dir_json.get("files", [])
    total_files = len(files)
    exist_files = 0
    need_download_files = 0
    logger.debug(f'{plugin_name} {tag} 目录 {endpoint} 中有 {total_files} 个文件待检查')
    
    # 准备下载任务
    download_tasks = []
    size_checked = 0
    batch_size_limit = 1500000  # 1.5MB 批次限制
    batch_num = 0  # 批次编号，用于日志
    
    for idx, file_info in enumerate(files, 1):
        file_relative_path = file_info["path"]
        remote_size = file_info.get("size", 0)
        
        # 构建本地路径
        if file_relative_path.startswith(dir_name + "/"):
            local_relative_path = file_relative_path[len(dir_name)+1:]
        else:
            local_relative_path = file_info["name"]
        
        local_file_path = local_path / local_relative_path
        
        # 检查文件是否存在且大小一致
        file_exists = local_file_path.exists()
        
        if file_exists:
            exist_files += 1
            local_size = local_file_path.stat().st_size
            
            if local_size == remote_size:
                logger.debug(f'{tag}✅ 文件已存在: {file_relative_path}')
                continue  # 文件存在且大小一致，跳过下载
            else:
                logger.info(f'{plugin_name} {tag}🔄 文件大小不一致: {file_relative_path} (本地: {local_size}, 远程: {remote_size})')
        else:
            # 确保目录存在
            local_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        need_download_files += 1
        size_checked += remote_size
        
        # 构建下载URL
        file_url = f"{base_url.rstrip('/')}/data/resource/{file_relative_path}"
        
        # 创建下载任务
        task = asyncio.create_task(
            download(file_url, local_file_path.parent, local_file_path.name, client, tag)
        )
        download_tasks.append(task)
        
        # 批次控制：达到限制或处理完最后一个文件时
        if size_checked >= batch_size_limit or idx == total_files:
            batch_num += 1
            
            if len(download_tasks) > 0:
                logger.debug(f'{tag} 开始第 {batch_num} 批下载，共 {len(download_tasks)} 个文件')
                await asyncio.gather(*download_tasks)
            
            # 重置批次
            download_tasks.clear()
            size_checked = 0
    
    logger.info(f'{tag} 目录 {endpoint} 检查完成-> 总数: {total_files}, 本地已存在: {exist_files}, 需下载: {need_download_files}')


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
    
    logger.info(f'🔗 {plugin_name} 使用资源站: {TAG}')
    
    # 2. 获取顶层资源索引，验证目录存在
    async with httpx.AsyncClient(timeout=httpx.Timeout(200.0)) as client:
        # 获取顶层索引
        resource_json = await fetch_json_index(client, BASE_URL, INDEX_PATHS['resource'])
        if not resource_json:
            logger.error(f'❌ {plugin_name} 无法获取顶层资源索引，可能索引文件未生成')
            return
        
        available_dirs = resource_json.get('directories', [])
        
        # 3. 遍历所有endpoint进行下载
        processed_count = 0
        for endpoint, local_path in EPATH_MAP.items():
            # 提取目录名
            dir_name = endpoint.split('/')[-1] if '/' in endpoint else endpoint
            
            # 检查目录是否在索引中
            if dir_name not in available_dirs:
                logger.warning(f'⚠ 目录 {dir_name} 不在 {plugin_name} 资源索引中，跳过')
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
            logger.success(f'📦 [资源检查] 插件 {plugin_name} 已完成 {processed_count}/{len(EPATH_MAP)} 个目录')
        else:
            logger.warning(f'⚠ [资源检查] 插件 {plugin_name} 未找到任何匹配的资源目录')