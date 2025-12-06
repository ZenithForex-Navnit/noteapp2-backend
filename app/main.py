from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from typing import Optional
from sqlalchemy.orm import joinedload
from . import models, database , schemas
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="signin")


# Assuming .models and .database are in the same folder

# Create tables if they don't exist
# This is typically done during application startup or via a migration tool
models.Base.metadata.create_all(bind=database.engine)

SECRET_KEY = "SUPER_SECRET_KEY"
ALGORITHM = "HS256"

# --- CORS Configuration ---
origins = [
    "http://localhost:3000",  # Allow your Next.js frontend
    "https://noteapp-backend-8vrm.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# yahan routes add karo
@app.get("/")
def read_root():
    return {"message": "Hello World"}
# --- End CORS Configuration ---

# --- Schemas (Pydantic models for request/response) ---
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "user"  # default
    secretpass: Optional[str] = None  # optional for frontend check

class UserInDB(BaseModel):
    id: int
    name: str
    email: str
    role: str

    class Config:
        orm_mode = True


class NoteBase(BaseModel):
    title: str
    description: str

class NoteCreate(NoteBase):
    pass

class Note(NoteBase):
    id: int
    owner_id: int
    class Config:
        orm_mode = True
def create_token(data: dict):
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(hours=10)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# --- Dependency to get the current user (Mock for simplicity) ---
# In a real app, this would decode a JWT token from the Authorization header
# def get_current_user(db: Session = Depends(database.get_db)) -> models.User:
#     # SIMPLIFIED: Assume user with ID 1 is currently logged in for testing
#     user = db.query(models.User).filter(models.User.id == 1).first()
#     if not user:
#          raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="User not logged in/Found"
#         )
#     return user
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)) -> models.User:
    try:
        # Token decode karo
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        )

    # Database se current user nikaalo
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


# --- Authentication Endpoints ---

# @app.post("/signup", response_model=UserInDB)
# # FastAPI automatically reads the JSON request body into the 'user' parameter 
# # because it's a Pydantic model (UserCreate).
# def create_user(user: UserCreate, db: Session = Depends(database.get_db)):
#     """
#     Handles user registration.
#     - Checks for existing email.
#     - Saves user data (with a mock hashed password).
#     """
#         # 1️⃣ Check secretPass
#     BACKEND_SECRET = "MySuperSecret123"  # ye wahi value set kar jo frontend se bhej raha hai
#     if user.role == 'admin' and (user.secretpass != BACKEND_SECRET):
#         raise HTTPException(status_code=403, detail="Invalid secret key")
    
#     db_user = db.query(models.User).filter(models.User.email == user.email).first()
#     if db_user:
#         raise HTTPException(status_code=400, detail="Email already registered")
    
#     # SECURITY NOTE: Replace this mock hashing with a real library like 'passlib' (e.g., bcrypt)
#     fake_hashed_password = f"FAKE_HASH_{user.password}"
    
#     db_user = models.User(
#         name=user.name, 
#         email=user.email, 
#         hashed_password=fake_hashed_password, 
#         role=user.role,
#         secretpass=BACKEND_SECRET
#     )
#     db.add(db_user)
#     db.commit()
#     db.refresh(db_user)
#     return db_user
@app.post("/signup", response_model=UserInDB)
def create_user(user: UserCreate, db: Session = Depends(database.get_db)):
    # check secret for admin
    BACKEND_SECRET = "MySuperSecret123"
    if user.role == 'admin' and (user.secretpass != BACKEND_SECRET):
        raise HTTPException(status_code=403, detail="Invalid secret key")

    # check existing email
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # save user
    fake_hashed_password = f"FAKE_HASH_{user.password}"
    db_user = models.User(
        name=user.name,
        email=user.email,
        hashed_password=fake_hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@app.post("/signin")
def sign_in(email: str, password: str, db: Session = Depends(database.get_db)):
    """
    Handles user sign-in.
    - Authenticates credentials.
    - Returns user details/token.
    """
    db_user = db.query(models.User).filter(models.User.email == email).first()
    
    # SIMPLIFIED: Check password (replace with real hash comparison)
    if db_user and db_user.hashed_password == f"FAKE_HASH_{password}":
        # SUCCESS: In a real app, generate and return a JWT token here
        token = create_token({"user_id": db_user.id})

        return {
            "message": "Login successful",
            "token": token,
            "user_id": db_user.id,
            "role": db_user.role
        }
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

# --- Notes CRUD Endpoints ---

# READ ALL NOTES (Dashboard/List) - Role-Based Access Control
@app.get("/notes", response_model=List[schemas.NoteResponse])
def read_notes(current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):

    if current_user.role == "admin":
        # Admin: all notes with owner info
        notes = db.query(models.Note).options(joinedload(models.Note.owner)).all()
        return notes

    # User: only their notes with owner info
    notes = db.query(models.Note)\
              .filter(models.Note.owner_id == current_user.id)\
              .options(joinedload(models.Note.owner))\
              .all()
    return notes


# CREATE NOTE
@app.post("/notes", response_model=Note, status_code=status.HTTP_201_CREATED)
def create_note(note: NoteCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    
    db_note = models.Note(
        title=note.title, description=note.description, owner_id=current_user.id
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

# Helper for Authorization
def authorize_note_access(note_id: int, current_user: models.User, db: Session):
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if db_note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    # ADMIN: Always allowed to manage
    if current_user.role == "admin":
        return db_note
        
    # USER: Must be the owner
    if db_note.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this note")
        
    return db_note

# UPDATE NOTE
# @app.put("/notes/{note_id}", response_model=Note)
# def update_note(
#     note_id: int, 
#     note_data: NoteCreate, 
#     current_user: models.User = Depends(get_current_user), 
#     db: Session = Depends(database.get_db)
# ):
#     db_note = authorize_note_access(note_id, current_user, db)
    
#     db_note.title = note_data.title
#     db_note.description = note_data.description
#     db.commit()
#     db.refresh(db_note)
#     return db_note
@app.put("/notes/{note_id}", response_model=Note)
def update_note(
    note_id: int,
    note_data: NoteUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    db_note = authorize_note_access(note_id, current_user, db)

    # Only update if field is provided
    if note_data.title is not None:
        db_note.title = note_data.title
    if note_data.description is not None:
        db_note.description = note_data.description

    db.commit()
    db.refresh(db_note)
    return db_note



# DELETE NOTE
@app.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    db_note = authorize_note_access(note_id, current_user, db)
    
    db.delete(db_note)
    db.commit()
    return {"ok": True}