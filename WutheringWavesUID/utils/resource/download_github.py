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
    ("[GitHub Raw]", "https://raw.githubusercontent.com"),  # 包含直连
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


def mirror_head_to_access_url(url: str) -> str:
    """将镜像源URL转换为访问资源的URL格式"""
    if 'jsdelivr.net' in url:
        return f"{url.rstrip('/')}/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}@{GITHUB_BRANCH}"
    else:
        return f"{url.rstrip('/')}/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{GITHUB_BRANCH}"


async def test_mirror_speed(tag: str, base_url: str) -> Tuple[str, str, float, Optional[Dict]]:
    """测试单个GitHub镜像源速度，并尝试获取resource.json"""
    url = mirror_head_to_access_url(base_url) + f"/{INDEX_PATHS['resource']}"
    
    async with httpx.AsyncClient() as client:
        try:
            start_time = time.time()
            response = await client.get(url, timeout=10.0)
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                logger.debug(f'⌛ [测速] {tag} {base_url} 延时: {elapsed_time:.2f}s')
                # 尝试解析JSON获取last_updated
                try:
                    data = json.loads(response.text)
                    if "last_updated" in data:
                        return tag, base_url, elapsed_time, data
                    else:
                        logger.warning(f'⚠️ {tag} {base_url} JSON格式错误: 缺少last_updated')
                        return tag, base_url, elapsed_time, None
                except json.JSONDecodeError:
                    logger.warning(f'⚠️ {tag} {base_url} JSON解析失败')
                    return tag, base_url, elapsed_time, None
            else:
                logger.warning(f'⚠️ {tag} {base_url} 测试文件状态码: {response.status_code}')
        except Exception as e:
            logger.warning(f'⚠️ {tag} {base_url} 连接错误: {str(e)[:50]}...')
    
    return tag, base_url, float('inf'), None


async def check_speed():
    """测速选择最快的GitHub镜像源，比较资源新鲜度"""
    global global_tag, global_url, NOW_SPEED_TEST
    
    if (not global_tag or not global_url) and not NOW_SPEED_TEST:
        NOW_SPEED_TEST = True
        logger.info('[WW资源下载]测速中...')
        
        # 第一步：测试所有源（包括直连和镜像）
        tasks = []
        for tag, base_url in GITHUB_MIRRORS:
            tasks.append(asyncio.create_task(test_mirror_speed(tag, base_url)))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集可用的源
        raw_source = None  # 直连源
        mirror_sources = []  # 镜像源
        
        for result in results:
            if isinstance(result, (Exception, BaseException)):
                continue
            tag, base_url, elapsed, json_data = result
            
            if elapsed < float('inf'):  # 可用的源
                source_info = {
                    'tag': tag,
                    'url': base_url.rstrip('/'),
                    'time': elapsed,
                    'json': json_data
                }
                
                # 分类
                if tag == "[GitHub Raw]":
                    raw_source = source_info
                else:
                    mirror_sources.append(source_info)
        
        # 第二步：决策逻辑
        selected_source = None
        
        if not raw_source:
            # 情况1: 直连不可用 -> 使用最快镜像
            logger.info('❌ GitHub Raw不可用，使用最快镜像源')
            if mirror_sources:
                # 按速度排序
                mirror_sources.sort(key=lambda x: x['time'])
                selected_source = mirror_sources[0]
        else:
            # 情况2: 直连可用
            logger.info('✅ GitHub Raw可用，开始智能选择...')
            
            # 2.1 找出最快镜像源
            fastest_mirror = None
            if mirror_sources:
                mirror_sources.sort(key=lambda x: x['time'])
                fastest_mirror = mirror_sources[0]
            
            if not fastest_mirror:
                # 没有可用镜像，使用直连
                logger.info('ℹ️ 没有可用镜像源，使用直连源')
                global_tag = raw_source['tag']
                global_url = mirror_head_to_access_url(raw_source['url'])
                NOW_SPEED_TEST = False
                return global_tag, global_url

            logger.info(f'🔍 最快镜像源: {fastest_mirror["tag"]} 延时: {fastest_mirror["time"]:.2f}s')
            
            # 2.2 根据JSON获取情况决策
            has_raw_json = raw_source['json'] is not None
            has_mirror_json = fastest_mirror['json'] is not None
            
            if not has_raw_json and not has_mirror_json:
                # 双方都获取失败，使用直连
                logger.warning('⚠️ 双方JSON获取失败，使用直连源')
                selected_source = raw_source
            elif not has_raw_json:
                # 直连JSON获取失败，使用镜像
                logger.info('📥 直连JSON获取失败，使用镜像源')
                selected_source = fastest_mirror
            elif not has_mirror_json:
                # 镜像JSON获取失败，使用直连
                logger.info('📥 镜像JSON获取失败，使用直连源')
                selected_source = raw_source
            else:
                # 双方都有JSON，比较last_updated
                raw_updated = raw_source['json'].get('last_updated', '')
                mirror_updated = fastest_mirror['json'].get('last_updated', '')
                
                logger.debug(f'📅 直连更新日期: {raw_updated} 镜像更新日期: {mirror_updated}')
                
                if mirror_updated >= raw_updated:
                    # 镜像站是最新或一样新 -> 使用镜像站
                    logger.info('🔄 镜像站资源已同步或更新，使用镜像站')
                    selected_source = fastest_mirror
                else:
                    # 镜像站落后 -> 使用直连
                    logger.info('⚡ 镜像站资源落后，使用直连源')
                    selected_source = raw_source
        
        # 第三步：设置全局变量
        if selected_source:
            global_url = mirror_head_to_access_url(selected_source['url'])
            global_tag = selected_source['tag']
            logger.info(f"🚀 最终选择: {global_tag} {global_url}")
        else:
            # 后备方案
            global_url = mirror_head_to_access_url("https://raw.githubusercontent.com")
            global_tag = "[GitHub Raw]"
            logger.warning(f"⚠️ 未找到合适源，使用直连（可能不可用）: {global_tag}")
        
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