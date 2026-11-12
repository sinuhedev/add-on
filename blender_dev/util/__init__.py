def hex_to_rgba(value, alpha=1.0):
    value = value.lstrip("#")
    r, g, b = (int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return r, g, b, alpha
