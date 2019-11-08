import string

from typing import List, Set, Dict, Tuple, Optional, Any, Iterable


def quote_args(args: Iterable[str]) -> List[str]:
    """Quote the arguments which contain whitespaces (only for printing)"""
    r = []
    for arg in args:
        if any(map(lambda c: c in string.whitespace, arg)):
            r.append(f'"{arg}"')
        else:
            r.append(arg)
    return r

