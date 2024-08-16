from typing import Union

from PIL import Image

from gsuid_core.utils.download_resource.download_file import download
from .RESOURCE_PATH import ROLE_DETAIL_SKILL_PATH, ROLE_DETAIL_CHAINS_PATH, PHANTOM_PATH


async def get_skill_img(
    char_id: Union[str, int],
    skill_name: str,
    pic_url: str
) -> Union[Image.Image, str, None]:
    _dir = ROLE_DETAIL_SKILL_PATH / str(char_id)
    _dir.mkdir(parents=True, exist_ok=True)

    name = f"skill_{skill_name}.png"
    _path = _dir / name
    if not _path.exists():
        await download(pic_url, _dir, name, tag="[鸣潮]")

    return Image.open(_path).convert("RGBA")


async def get_chain_img(
    char_id: Union[str, int],
    order_id: int,
    pic_url: str
) -> Union[Image.Image, str, None]:
    _dir = ROLE_DETAIL_CHAINS_PATH / str(char_id)
    _dir.mkdir(parents=True, exist_ok=True)

    name = f"chain_{order_id}.png"
    _path = _dir / name
    if not _path.exists():
        await download(pic_url, _dir, name, tag="[鸣潮]")

    return Image.open(_path).convert("RGBA")


async def get_phantom_img(
    phantom_id: int,
    pic_url: str
) -> Union[Image.Image, str, None]:
    name = f"phantom_{phantom_id}.png"
    _path = PHANTOM_PATH / name
    if not _path.exists():
        await download(pic_url, PHANTOM_PATH, name, tag="[鸣潮]")

    return Image.open(_path).convert("RGBA")
