from pydantic import BaseModel

# This is a placeholder for the actual buff data.
# It should be loaded from a file or a database.
BUFF_DATA = {
    "1001": {"id": 1001, "name": "ATK Up", "qualityId": 5, "icon": "buff_1001.png"},
    "1002": {"id": 1002, "name": "DEF Up", "qualityId": 4, "icon": "buff_1002.png"},
}


class BuffModel(BaseModel):
    id: int
    name: str
    qualityId: int
    icon: str


def get_buff_model(buff_id: int) -> BuffModel | None:
    """
    Get buff model by buff_id.
    """
    buff_data = BUFF_DATA.get(str(buff_id))
    if buff_data:
        return BuffModel(**buff_data)

    # Fallback: construct model from buff_id
    return BuffModel(
        id=buff_id,
        name=f"Buff {buff_id}",
        qualityId=3,  # Default quality
        icon=f"{buff_id}.png",
    )
