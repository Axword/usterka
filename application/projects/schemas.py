import datetime as dt

from ninja import Schema
from pydantic import field_validator


class ProjectIn(Schema):
    name: str
    address: str = ''
    investor: str = ''
    contractor: str = ''
    inspection_date: dt.date | None = None
    author: str = ''

    @field_validator('name', 'address', 'investor', 'contractor', 'author')
    @classmethod
    def strip(cls, v: str) -> str:
        return v.strip()

    @field_validator('name')
    @classmethod
    def name_required(cls, v: str) -> str:
        if not v:
            raise ValueError('Nazwa inwestycji jest wymagana.')
        return v


class ProjectPatch(Schema):
    name: str | None = None
    address: str | None = None
    investor: str | None = None
    contractor: str | None = None
    inspection_date: dt.date | None = None
    author: str | None = None


class ReportSettings(Schema):
    date: dt.date | None = None
    filter: str = 'all'
    plans: bool = True
    logo: bool = True
    sharepoint: bool = True


class ProjectOut(Schema):
    id: str
    name: str
    address: str
    investor: str
    contractor: str
    inspection_date: dt.date | None
    author: str
    has_logo: bool
    is_complete: bool
    report_settings: dict
    plans_count: int = 0
    open_count: int = 0
    fixed_count: int = 0
    created_at: dt.datetime
    updated_at: dt.datetime
