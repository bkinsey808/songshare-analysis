from typing import Any

class _Frame: ...

class TIT2(_Frame):
    def __init__(self, encoding: int = ..., text: Any = ...) -> None: ...

class TPE1(_Frame):
    def __init__(self, encoding: int = ..., text: Any = ...) -> None: ...

class TALB(_Frame):
    def __init__(self, encoding: int = ..., text: Any = ...) -> None: ...

class TCON(_Frame):
    def __init__(self, encoding: int = ..., text: Any = ...) -> None: ...

class TXXX(_Frame):
    def __init__(
        self, encoding: int = ..., desc: str = ..., text: Any = ...
    ) -> None: ...

class APIC(_Frame):
    def __init__(
        self,
        encoding: int = ...,
        mime: str = ...,
        type: int = ...,
        desc: str = ...,
        data: bytes = ...,
    ) -> None: ...
