import os


def normalize(path: str) -> str:
    return os.path.realpath(os.path.expanduser(path))


def ensure_allowed(path: str, roots: list[str]) -> str:
    """校验路径位于白名单目录内，返回规范化后的真实路径。"""
    if not roots:
        raise PermissionError("未配置允许访问的目录白名单，请先在设置中配置")
    target = normalize(path)
    for root in roots:
        real_root = normalize(root)
        if target == real_root or target.startswith(real_root + os.sep):
            return target
    raise PermissionError(f"路径不在允许访问的白名单内：{path}")


def is_within(path: str, root: str) -> bool:
    target = normalize(path)
    real_root = normalize(root)
    return target == real_root or target.startswith(real_root + os.sep)
