def format_sku(prefix: str, separator: str, pad_width: int, scalar: int) -> str:
    return f"{prefix}{separator}{str(scalar).zfill(pad_width)}"

