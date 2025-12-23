import asyncio
import json
from pathlib import Path
import time

import aiofiles
from gsuid_core.logger import logger
import httpx

# GitHub Raw 镜像源列表 (可扩展)
GITHUB_MIRRORS = [
    ("[GitHub Raw]", "https://raw.githubusercontent.com"),  # 包含直连
    # ("[GitHub Mirror CN]", "https://raw.gitmirror.com"),
    ("[GitHub Mirror CN-hub]", "https://hub.gitmirror.com/raw.githubusercontent.com"),
    ("[GitHub Mirror j cdn]", "https://cdn.jsdelivr.net/gh"),
    ("[GitHub Mirror j fastly]", "https://fastly.jsdelivr.net/gh"),
    ("[GitHub Mirror j gcore]", "https://gcore.jsdelivr.net/gh"),
    ("[GitHub Mirror ghproxy]", "https://gh-proxy.org/https://raw.githubusercontent.com"),
]

# 仓库信息 (可配置)
GITHUB_REPO_OWNER = "MoonShadow1976"
GITHUB_REPO_NAME = "WutheringWaves_OverSea_StaticAssets"
GITHUB_BRANCH = "main"

# JSON索引路径
INDEX_PATHS = {
    "resource": "data/resource.json",  # 顶层索引
    # 子目录索引: data/resource/xxx.json
}

# 下载配置
DOWNLOAD_CONFIG = {
    "max_concurrent": 20,  # 最大并发数
    "batch_sizes": {
        "small": 10,  # 小文件（<1MB）
        "medium": 5,  # 中等文件（1MB-10MB）
        "large": 2,  # 大文件（>10MB）
    },
    "retry_times": 3,
    "timeout": 30.0,
}


def mirror_head_to_access_url(url: str) -> str:
    """将镜像源URL转换为访问资源的URL格式"""
    if "jsdelivr.net" in url:
        return f"{url.rstrip('/')}/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}@{GITHUB_BRANCH}"
    else:
        return f"{url.rstrip('/')}/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{GITHUB_BRANCH}"


async def test_mirror_speed(tag: str, base_url: str) -> tuple[str, str, float, dict | None]:
    """测试单个GitHub镜像源速度"""
    url = mirror_head_to_access_url(base_url) + f"/{INDEX_PATHS['resource']}"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            start_time = time.time()
            response = await client.get(url, timeout=10.0)
            elapsed_time = time.time() - start_time

            if response.status_code == 200:
                logger.debug(f"⌛ [测速] {tag} {url} 延时: {elapsed_time:.2f}s")
                try:
                    data = json.loads(response.text)
                    if "last_updated" in data:
                        return tag, base_url, elapsed_time, data
                    else:
                        logger.warning(f"⚠️ {tag} {url} JSON格式错误: 缺少last_updated")
                        return tag, base_url, elapsed_time, None
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ {tag} {url} JSON解析失败")
                    return tag, base_url, elapsed_time, None
            else:
                logger.warning(f"⚠️ {tag} {url} 测试文件状态码: {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ {tag} {url} 连接错误: {str(e)[:50]}...")

    return tag, base_url, float("inf"), None


async def check_speed():
    """测速选择最快的GitHub镜像源，比较资源新鲜度"""
    logger.info("[WW资源下载]测速中...")

    tasks = []
    for tag, base_url in GITHUB_MIRRORS:
        tasks.append(asyncio.create_task(test_mirror_speed(tag, base_url)))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    available_sources = []

    for result in results:
        if isinstance(result, (Exception, BaseException)):
            continue
        tag, base_url, elapsed, json_data = result

        if elapsed < float("inf"):
            # 解析更新时间字符串为时间戳 (UTC)
            last_updated_str = json_data.get("last_updated", "1970-01-01T00:00:00Z") if json_data else "1970-01-01T00:00:00Z"
            try:
                last_updated_timestamp = time.mktime(time.strptime(last_updated_str, "%Y-%m-%dT%H:%M:%SZ"))
            except Exception:
                last_updated_timestamp = 0

            source_info = {
                "tag": tag,
                "url": base_url.rstrip("/"),
                "time": elapsed,
                "json": json_data,
                "last_updated_timestamp": last_updated_timestamp,  # 时间戳用于排序
            }
            available_sources.append(source_info)

    if not available_sources:
        logger.error("❌ 没有可用的镜像源，直接使用GitHub Raw")
        global_url = mirror_head_to_access_url("https://raw.githubusercontent.com")
        global_tag = "[GitHub Raw]"
        return global_tag, global_url

    # 按更新时间戳降序（越新越好），然后按延时升序（越小越好）
    available_sources.sort(key=lambda s: (-s["last_updated_timestamp"], s["time"]))

    # 获取最佳的更新时间和对应的源
    best_update_timestamp = available_sources[0]["last_updated_timestamp"]
    best_sources = [s for s in available_sources if s["last_updated_timestamp"] == best_update_timestamp]

    if len(best_sources) > 1:
        logger.info(f"🔍 有{len(best_sources)}个源具有相同的最新更新时间")
        # 在这些具有相同更新时间的源中选择最快的
        best_sources.sort(key=lambda x: x["time"])
        selected_source = best_sources[0]
        logger.info(f"⚡ 在这些源中选择最快的: {selected_source['tag']} ({selected_source['time']:.2f}s)")
    else:
        selected_source = available_sources[0]
        logger.info(f"📅 选择唯一一个资源最新的源: {selected_source['tag']}")

    # 特殊处理：如果最佳源不是GitHub Raw但更新时间落后于GitHub Raw，显示警告
    raw_source = next((s for s in available_sources if s["tag"] == "[GitHub Raw]"), None)
    if raw_source:
        if (
            selected_source["tag"] != "[GitHub Raw]"
            and selected_source["last_updated_timestamp"] < raw_source["last_updated_timestamp"]
        ):
            logger.warning(f"⚠️ 选择的镜像站({selected_source['tag']})资源比GitHub Raw旧，改为使用GitHub Raw")

            selected_source = raw_source
    else:
        logger.info(f"GitHub Raw不可用，直接使用镜像站{selected_source['tag']}")

    global_url = mirror_head_to_access_url(selected_source["url"])
    global_tag = selected_source["tag"]
    logger.info(f"🚀 最终选择: {global_tag} {global_url}")

    return global_tag, global_url


async def fetch_json_index(client: httpx.AsyncClient, base_url: str, json_path: str) -> dict | None:
    """获取并解析JSON索引文件"""
    url = f"{base_url.rstrip('/')}/{json_path}"
    try:
        response = await client.get(url, timeout=30.0)
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            logger.warning(f"获取JSON索引失败 {url}: HTTP {response.status_code}")
    except Exception as e:
        logger.warning(f"获取JSON索引失败 {url}: {e}")
    return None


async def download(
    url: str, path: Path, name: str, client: httpx.AsyncClient, tag: str = "", max_retries: int = 3
) -> tuple[bool, str]:
    """
    下载文件
    返回: (是否成功, 错误信息/空字符串)
    """
    for attempt in range(max_retries):
        try:
            logger.debug(f"{tag} 开始下载 {name} (尝试 {attempt + 1}/{max_retries})...")

            response = await client.get(url, follow_redirects=True)

            if response.status_code == 200:
                content = response.content
                path.mkdir(parents=True, exist_ok=True)

                async with aiofiles.open(path / name, "wb") as f:
                    await f.write(content)

                logger.debug(f"{tag} {name} 下载完成！")
                return True, ""
            else:
                logger.warning(f"{tag} {name} 下载失败！HTTP {response.status_code}")
                return False, f"HTTP {response.status_code}"

        except Exception as e:
            logger.error(f"{tag} {name} 下载出错: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)

    logger.warning(f"{tag} {name} 下载失败，已重试{max_retries}次")
    return False, "下载失败，重试次数用尽"


async def download_with_json_index(
    base_url: str, tag: str, endpoint: str, local_path: Path, client: httpx.AsyncClient, plugin_name: str
) -> tuple[int, int, int, list[str]]:
    """
    使用JSON索引下载单个目录的资源
    返回: (总文件数, 已存在文件数, 下载成功数, 失败文件列表)
    """
    dir_name = endpoint.split("/")[-1] if "/" in endpoint else endpoint

    dir_json_path = f"data/resource/{dir_name}.json"
    dir_json = await fetch_json_index(client, base_url, dir_json_path)

    if not dir_json:
        logger.warning(f"{plugin_name} {tag} {endpoint} 无法获取JSON索引: {dir_json_path}")
        return 0, 0, 0, []

    files = dir_json.get("files", [])
    total_files = len(files)
    exist_files = 0
    need_download_files = 0

    logger.info(f"{plugin_name} {tag} 目录 {endpoint} 中有 {total_files} 个文件待检查")

    # 分类文件：按大小分组
    small_files = []  # <1MB
    medium_files = []  # 1MB-10MB
    large_files = []  # >10MB

    for file_info in files:
        file_relative_path = file_info["path"]
        remote_size = file_info.get("size", 0)

        if file_relative_path.startswith(dir_name + "/"):
            local_relative_path = file_relative_path[len(dir_name) + 1 :]
        else:
            local_relative_path = file_info["name"]

        local_file_path = local_path / local_relative_path

        file_exists = local_file_path.exists()

        if file_exists:
            exist_files += 1
            local_size = local_file_path.stat().st_size

            if local_size == remote_size:
                continue
            else:
                logger.info(
                    f"{plugin_name} {tag}🔄 文件大小不一致: {file_relative_path} (本地: {local_size}, 远程: {remote_size})"
                )
        else:
            local_file_path.parent.mkdir(parents=True, exist_ok=True)

        need_download_files += 1

        file_url = f"{base_url.rstrip('/')}/data/resource/{file_relative_path}"

        # 按文件大小分类
        if remote_size < 1024 * 1024:  # <1MB
            small_files.append((file_url, local_file_path.parent, local_file_path.name, file_relative_path))
        elif remote_size < 10 * 1024 * 1024:  # 1MB-10MB
            medium_files.append((file_url, local_file_path.parent, local_file_path.name, file_relative_path))
        else:  # >10MB
            large_files.append((file_url, local_file_path.parent, local_file_path.name, file_relative_path))

    logger.debug(
        f"{tag} 目录 {endpoint} 需要下载 {need_download_files} 个文件 (小: {len(small_files)}, 中: {len(medium_files)}, 大: {len(large_files)})"
    )

    success_count = 0
    failed_files = []

    # 使用信号量控制最大并发数
    semaphore = asyncio.Semaphore(DOWNLOAD_CONFIG["max_concurrent"])

    async def download_with_semaphore(file_url, path, name, file_path):
        async with semaphore:
            success, error_msg = await download(file_url, path, name, client, tag, DOWNLOAD_CONFIG["retry_times"])
            return success, error_msg, file_path

    # 分批下载不同类型文件
    download_groups = [
        (small_files, DOWNLOAD_CONFIG["batch_sizes"]["small"], "小文件"),
        (medium_files, DOWNLOAD_CONFIG["batch_sizes"]["medium"], "中等文件"),
        (large_files, DOWNLOAD_CONFIG["batch_sizes"]["large"], "大文件"),
    ]

    for file_list, batch_size, file_type in download_groups:
        if not file_list:
            continue

        logger.debug(f"{tag} 开始下载{file_type}，数量: {len(file_list)}，批次大小: {batch_size}")

        for i in range(0, len(file_list), batch_size):
            batch = file_list[i : i + batch_size]
            batch_tasks = []

            for file_url, path, name, file_path in batch:
                task = asyncio.create_task(download_with_semaphore(file_url, path, name, file_path))
                batch_tasks.append(task)

            # 等待当前批次完成
            batch_results = await asyncio.gather(*batch_tasks)

            for success, error_msg, file_path in batch_results:
                if success:
                    success_count += 1
                else:
                    failed_files.append(f"{file_path}: {error_msg}")

            # 小批次之间短暂暂停，避免请求过猛
            if i + batch_size < len(file_list):
                await asyncio.sleep(0.1)

    logger.info(
        f"{tag} 目录 {endpoint} 检查完成: 总数={total_files}, 已存在={exist_files}, 下载成功={success_count}, 失败={len(failed_files)}"
    )

    return total_files, exist_files, success_count, failed_files


async def download_all_file(
    plugin_name: str,
    EPATH_MAP: dict[str, Path],
    URL: str | None = None,
    TAG: str | None = None,
    max_concurrent: int | None = None,
) -> str:
    """
    主下载函数 - 支持动态调整并发数
    返回: 简化的下载结果字符串
    """
    # 更新配置
    if max_concurrent:
        DOWNLOAD_CONFIG["max_concurrent"] = max_concurrent

    if URL:
        TAG, BASE_URL = TAG or "[Unknown]", URL
    else:
        TAG, BASE_URL = await check_speed()
        if not BASE_URL:
            return "❌ 无法获取可用的资源站"

    logger.info(f"🔗 {plugin_name} 使用资源站: {TAG}，最大并发数: {DOWNLOAD_CONFIG['max_concurrent']}")

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(DOWNLOAD_CONFIG["timeout"]),
        follow_redirects=True,
        limits=httpx.Limits(max_connections=DOWNLOAD_CONFIG["max_concurrent"] * 2, max_keepalive_connections=10),
    ) as client:
        resource_json = await fetch_json_index(client, BASE_URL, INDEX_PATHS["resource"])
        if not resource_json:
            return "❌ 无法获取顶层资源索引，可能索引文件未生成"

        available_dirs = resource_json.get("directories", [])

        processed_dirs = 0
        total_files = 0
        total_exist = 0
        total_success = 0
        total_fail = 0
        failed_dirs_info = []

        for endpoint, local_path in EPATH_MAP.items():
            dir_name = endpoint.split("/")[-1] if "/" in endpoint else endpoint

            if dir_name not in available_dirs:
                logger.warning(f"⚠️ 目录 {dir_name} 不在 {plugin_name} 资源索引中，跳过")
                failed_dirs_info.append(f"⚠️ {dir_name}: 目录不在索引中")
                continue

            local_path.mkdir(parents=True, exist_ok=True)

            dir_total, dir_exist, dir_success, failed_files = await download_with_json_index(
                BASE_URL, TAG, endpoint, local_path, client, plugin_name
            )

            total_files += dir_total
            total_exist += dir_exist
            total_success += dir_success
            total_fail += len(failed_files)

            if failed_files:
                failed_dirs_info.append(f"❌ {dir_name}: {dir_success}成功, {len(failed_files)}失败")
            else:
                failed_dirs_info.append(f"✅ {dir_name}: {dir_success}个文件下载完成")

            processed_dirs += 1

        # 生成结果字符串
        total_need_download = total_files - total_exist
        failed_items = [info for info in failed_dirs_info if "❌" in info]
        max_display = 5

        if total_fail == 0:
            if total_need_download == 0:
                return f"✅ 所有{processed_dirs}个目录已是最新，无需下载"
            else:
                return f"✅ 所有{processed_dirs}个目录下载完成，{total_success}个文件下载成功"
        else:
            result_lines = [f"❌ {processed_dirs}个目录，{total_success}成功/{total_fail}失败"]

            if failed_items:
                if len(failed_items) > max_display:
                    result_lines.extend(failed_items[:max_display])
                    result_lines.append(f"... 还有 {len(failed_items) - max_display} 个目录失败未显示")
                else:
                    result_lines.extend(failed_items)

            return "\n".join(result_lines)
