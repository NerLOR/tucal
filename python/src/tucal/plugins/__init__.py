
from typing import List, Tuple, Optional, Type

import tucal.plugins.c187B12
import tucal.plugins.introsec
import tucal.plugins.htu_events
import tucal.plugins.tuwien_events


def plugins() -> List[Tuple[Optional[str], Type[tucal.Plugin]]]:
    return [
        ('187B12', c187B12.Plugin),         # 187.B12 VU Denkweisen der Informatik
        ('184783', introsec.PluginVU),      # 184.783 VU Introduction to Security
        ('192082', introsec.PluginUE),      # 192.082 UE Introduction to Security
        (None,     htu_events.Plugin),      # https://events.htu.at
        (None,     tuwien_events.Plugin),   # https://www.tuwien.at/tu-wien/aktuelles/veranstaltungskalender
    ]
