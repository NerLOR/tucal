
from typing import List, Tuple, Optional, Type

import tucal.plugins.c187B12
import tucal.plugins.htu_events
import tucal.plugins.tuwien_events


def plugins() -> List[Tuple[Optional[str], Type[tucal.Plugin]]]:
    return [
        ('187B12', c187B12.Plugin),         # 187.B12 VU Denkweisen der Informatik
        (None,     htu_events.Plugin),      # https://events.htu.at
        (None,     tuwien_events.Plugin),   # https://www.tuwien.at/tu-wien/aktuelles/veranstaltungskalender
    ]
