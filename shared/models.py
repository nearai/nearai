from pydantic import BaseModel


class SimilaritySearch(BaseModel):
    file_id: str
    chunk_text: str
    distance: float
