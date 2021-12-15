
import typing

import tucal.plugins.c187B12
import tucal.plugins.eventHTU


def plugins() -> typing.List[typing.Tuple[str, typing.Type[tucal.Plugin]]]:
    return [
        ('187B12', c187B12.DWI),  # 187.B12 VU Denkweisen der Informatik
        ('eventHTU', eventHTU.EVENTS),
    ]
