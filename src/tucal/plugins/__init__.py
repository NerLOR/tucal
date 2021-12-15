
import typing

import tucal.plugins.c187B12
import tucal.plugins.htu_events


def plugins() -> typing.List[typing.Tuple[typing.Optional[str], typing.Type[tucal.Plugin]]]:
    return [
        ('187B12', c187B12.DWI),  # 187.B12 VU Denkweisen der Informatik
        (None, htu_events.HTUEvents),  # https://events.htu.at
    ]
