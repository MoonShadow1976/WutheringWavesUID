from pydantic import BaseModel


class LinkConfig(BaseModel):
    linkUrl: str | None = None
    linkType: int
    entryId: str


class ProgressData(BaseModel):
    progressType: int
    dataRange: list[str]
    title: str


class RepeatConfig(BaseModel):
    endDate: str
    isNeverEnd: bool
    repeatInterval: int
    dataRanges: list[ProgressData]


class CountDown(BaseModel):
    dateRange: list[str] | None = None


class ContentData(BaseModel):
    contentUrl: str
    countDown: CountDown | None = None
    title: str


class VersionActivity(BaseModel):
    content: list[ContentData]


class ImageItem(BaseModel):
    linkConfig: LinkConfig
    img: str
    title: str


class SpecialImages(BaseModel):
    name: str
    imgs: list[ImageItem]
