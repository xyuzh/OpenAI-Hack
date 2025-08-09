import re
import uuid

from common.type.domain import DomainType


def generate_uuid(domain_type: DomainType) -> str:
    """生成UUID"""
    uuid_str = domain_type.value + "-" + str(uuid.uuid4()).replace("-", "")
    return uuid_str


def validate_uuid_format(v: str) -> str:
    """验证UUID格式是否符合 domain_type-uuid4_without_hyphens 格式"""
    # 获取所有有效的 domain type 值
    valid_prefixes = [domain_type.value for domain_type in DomainType]

    # 检查是否以有效的 domain type 开头，后跟一个横线
    pattern_found = False
    for prefix in valid_prefixes:
        if v.startswith(f"{prefix}-"):
            # 提取横线后的部分
            uuid_part = v[len(prefix) + 1:]

            # 验证UUID部分：应该是32位十六进制字符（uuid4去掉横线后的格式）
            if re.match(r'^[0-9a-f]{32}$', uuid_part, re.IGNORECASE):
                pattern_found = True
                break
            else:
                raise ValueError(
                    f'UUID part "{uuid_part}" must be 32 hexadecimal characters '
                    f'(UUID4 without hyphens)'
                )

    if not pattern_found:
        valid_prefixes_str = ', '.join(valid_prefixes)
        raise ValueError(
            f'UUID must start with one of [{valid_prefixes_str}] '
            f'followed by "-" and 32 hexadecimal characters. '
            f'Got: "{v}"'
        )

    return v


__all__ = ["generate_uuid", "validate_uuid_format"]
