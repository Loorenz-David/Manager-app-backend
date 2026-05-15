from functools import partial


def enum_values_callable(enum_cls: type) -> list[str]:
    return [member.value for member in enum_cls]


def configure_sa_enum_values(sa_enum_factory):
    return partial(sa_enum_factory, values_callable=enum_values_callable)
