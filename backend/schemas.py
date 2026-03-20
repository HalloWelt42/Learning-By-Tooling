"""schemas.py -- Alle Pydantic-Modelle (Request/Response)."""

from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    email:    str
    password: str

class RegisterRequest(BaseModel):
    email:        str
    password:     str
    display_name: Optional[str] = None

class PackageCreate(BaseModel):
    name:        str
    description: Optional[str]  = None
    color:       Optional[str]  = "#5C6BC0"
    icon:        Optional[str]  = "fa-graduation-cap"

class PackageUpdate(BaseModel):
    name:        Optional[str]  = None
    description: Optional[str]  = None
    color:       Optional[str]  = None
    icon:        Optional[str]  = None

class CardCreate(BaseModel):
    card_id:       Optional[str]  = None
    package_id:    Optional[int]  = None
    category_code: str
    question:      str
    answer:        str
    hint:          Optional[str]  = None
    tags:          Optional[list] = []
    difficulty:    Optional[int]  = 2

class CardUpdate(BaseModel):
    package_id:    Optional[int]  = None
    category_code: Optional[str]  = None
    question:      Optional[str]  = None
    answer:        Optional[str]  = None
    hint:          Optional[str]  = None
    tags:          Optional[list] = None
    difficulty:    Optional[int]  = None
    active:        Optional[int]  = None

class CategoryCreate(BaseModel):
    code:        str
    name:        str
    description: Optional[str]  = None
    color:       Optional[str]  = "#5C6BC0"
    icon:        Optional[str]  = "fa-layer-group"

class SessionCreate(BaseModel):
    mode:            Optional[str]  = "standard"
    package_id:      Optional[int]  = None
    category_filter: Optional[list] = []
    card_limit:      Optional[int]  = 20
    srs_mode:        Optional[bool] = False
    card_ids:        Optional[list] = None

class ReviewSubmit(BaseModel):
    session_id:  int
    card_id:     str
    result:      str
    user_answer: Optional[str]  = None
    use_ai:      Optional[bool] = False

class SessionReviewNext(BaseModel):
    """Review der aktuellen Karte + naechste Karte holen."""
    result:      str            # correct | wrong | skip | unknown (fuer KI)
    user_answer: Optional[str]  = None
    use_ai:      Optional[bool] = False
    srs_quality: Optional[int]  = None  # 0-5 fuer SRS-Modus
    time_ms:     Optional[int]  = 0     # Antwortzeit in Millisekunden
    mc_used:     Optional[bool] = None  # MC-Optionen tatsaechlich angezeigt?

class SRSReview(BaseModel):
    card_id: str
    quality: int
    session_id: Optional[int] = None

class LexiconCreate(BaseModel):
    package_id:    Optional[int]  = None
    term:          str
    definition:    str
    category_code: Optional[str]  = None
    related_cards: Optional[list] = []

class LexiconUpdate(BaseModel):
    term:          Optional[str]  = None
    definition:    Optional[str]  = None
    category_code: Optional[str]  = None

class PathCreate(BaseModel):
    package_id:     Optional[int]  = None
    name:           str
    description:    Optional[str]  = None
    category_codes: Optional[list] = []
    card_ids:       Optional[list] = []

class DraftAction(BaseModel):
    action:        str
    question:      Optional[str]  = None
    answer:        Optional[str]  = None
    hint:          Optional[str]  = None
    difficulty:    Optional[int]  = None
    category_code: Optional[str]  = None
    package_id:    Optional[int]  = None

class MarkdownImport(BaseModel):
    fragen:     str
    antworten:  str
    package_id: Optional[int] = None

class MistakeAnalysisRequest(BaseModel):
    card_ids:   list[int]
    package_id: int

class ChapterCreate(BaseModel):
    title:          str
    description:    Optional[str]  = None
    document_ids:   Optional[list] = []
    card_ids:       Optional[list] = []
    pass_threshold: Optional[float] = 0.7
    sort_order:     Optional[int]  = 0

class ChapterUpdate(BaseModel):
    title:          Optional[str]   = None
    description:    Optional[str]   = None
    document_ids:   Optional[list]  = None
    card_ids:       Optional[list]  = None
    pass_threshold: Optional[float] = None
    sort_order:     Optional[int]   = None
