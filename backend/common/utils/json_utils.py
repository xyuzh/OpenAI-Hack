def extract_json_from_string(content: str) -> str | None:
    """
    从字符串中提取第一个完整的JSON对象
    
    此函数会:
    1. 找到第一个左花括号 '{' 作为JSON开始
    2. 持续跟踪括号平衡情况，考虑字符串内的括号
    3. 一旦找到平衡的JSON对象，返回该JSON字符串
    4. 如果没有找到完整的JSON，返回None
    
    Args:
        content (str): 输入字符串，可能包含JSON和其他内容
        
    Returns:
        str | None: 提取的完整JSON字符串，如果没有找到则返回None
        
    注意:
        - 只返回第一个找到的完整JSON对象
        - 会自动过滤掉Markdown代码块标记和其他非JSON内容
    """

    def is_json_complete(json_str: str) -> tuple[bool, int]:
        """
        检查JSON是否完整 (内部函数)
        
        简化算法：只关注两个核心条件
        1. 所有花括号必须配对闭合 (只在字符串外部计数)
        2. 所有字符串必须闭合 (最后不能处于字符串内部)
        
        Returns:
            tuple: (是否完整, 如果完整则返回结束位置索引，否则返回-1)
        """
        if not json_str or not json_str.startswith('{'):
            return False, -1

        # 状态变量
        bracket_count = 0  # 花括号计数器
        in_string = False  # 是否在字符串内部
        escaped = False  # 上一个字符是否为转义符

        for i, char in enumerate(json_str):
            # 处理字符串边界
            if char == '"' and not escaped:
                in_string = not in_string  # 切换字符串状态

            # 处理转义字符
            elif char == '\\' and in_string:
                escaped = not escaped
                continue

            # 只在字符串外部时计数花括号
            elif not in_string:
                if char == '{':
                    bracket_count += 1
                elif char == '}':
                    bracket_count -= 1
                    # 右括号多于左括号，无效JSON
                    if bracket_count < 0:
                        return False, -1

                    # 检查是否找到了完整JSON
                    if bracket_count == 0:
                        return True, i

            # 重置转义标志
            if char != '\\':
                escaped = False

        # 如果遍历完所有字符后仍未找到平衡点
        return bracket_count == 0 and not in_string, -1

    if not content:
        return None

    # 寻找JSON开始标记
    start_index = content.find('{')
    if start_index == -1:
        return None

    # 提取从第一个花括号开始的内容
    json_candidate = content[start_index:]

    # 检查是否为完整的JSON
    is_complete, end_position = is_json_complete(json_candidate)

    if is_complete and end_position >= 0:
        # 返回完整的JSON字符串
        return json_candidate[:end_position + 1]
    else:
        # 没有找到完整的JSON
        return None


# 使用示例和测试函数
def test_extract_json():
    """测试函数，演示如何使用 extract_json_from_string"""

    test_cases = [
        # 基本JSON测试
        '{"name": "test", "value": 123}',

        # 带有前导和后续内容的JSON
        'Some text before {"key": "value", "number": 42} and some text after',

        # 包含嵌套对象的JSON
        'prefix {"user": {"name": "John", "age": 30}, "status": "active"} suffix',

        # 包含字符串中有花括号的JSON
        '{"message": "Hello {world}", "data": {"nested": true}}',

        # Markdown代码块中的JSON
        '```json\n{"formatted": true, "value": 100}\n```',

        # 不完整的JSON
        '{"incomplete": "json"',

        # 没有JSON的字符串
        'This is just plain text without any JSON',

        # 空字符串
        '',

        # 包含转义字符的JSON
        '{"text": "He said \\"Hello\\"", "escaped": "backslash\\\\test"}'
    ]

    print("JSON提取测试结果:")
    print("=" * 50)

    for i, test_case in enumerate(test_cases, 1):
        result = extract_json_from_string(test_case)
        print(f"测试 {i}:")
        print(f"输入: {test_case[:60]}{'...' if len(test_case) > 60 else ''}")
        print(f"结果: {result}")
        print("-" * 30)


# 如果直接运行此文件，执行测试
if __name__ == "__main__":
    test_extract_json()
