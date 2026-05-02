__all__ = ["camelize", "to_camel"]


def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def camelize(obj):
    if isinstance(obj, list):
        return [camelize(item) for item in obj]
    if isinstance(obj, dict):
        return {to_camel(k): camelize(v) for k, v in obj.items()}
    return obj
