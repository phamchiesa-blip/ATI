"""
domain/base.py
--------------
Lop co so DomainModel cho Domain Entities va DTOs theo Clean Architecture.
Tich hop Pydantic BaseModel de xac thuc kieu du lieu manh me, dong thoi
ho tro day du giao dien mapping (__getitem__, get, in, update, to_dict, v.v.)
de dam bao tinh tuong thich nguoc 100% voi toan bo codebase hien co.
"""

from __future__ import annotations

from typing import Any, Iterator, Mapping
from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """Base class cho moi Entity va DTO trong Clean Architecture.
    
    Vua la mot Pydantic v2 model hop le cho FastAPI serialization/docs,
    vua co the truy cap bang dot-notation (obj.name) hoac dictionary subscript (obj["name"]).
    """
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="allow",
        populate_by_name=True,
    )

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def keys(self) -> list[str]:
        field_keys = list(self.__class__.model_fields.keys())
        if self.__pydantic_extra__:
            for k in self.__pydantic_extra__.keys():
                if k not in field_keys:
                    field_keys.append(k)
        return field_keys

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self.keys())

    def update(self, *args: Any, **kwargs: Any) -> None:
        if args:
            arg = args[0]
            if isinstance(arg, Mapping):
                for k, v in arg.items():
                    setattr(self, k, v)
            else:
                for k, v in arg:
                    setattr(self, k, v)
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        return cls(**data)
