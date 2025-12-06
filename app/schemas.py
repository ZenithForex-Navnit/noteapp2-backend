from pydantic import BaseModel

class OwnerInfo(BaseModel):
    name: str
    email: str

class NoteResponse(BaseModel):
    id: int
    title: str
    description: str
    owner: OwnerInfo

    class Config:
        orm_mode = True
