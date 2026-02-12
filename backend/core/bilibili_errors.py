"""Bilibili API error code mappings for user-friendly error messages."""

BILIBILI_ERROR_CODES = {
    # Success
    0: "操作成功",

    # Authentication errors
    -101: "账号未登录或登录已失效",
    -799: "需要人机验证，账号已被风控",

    # Rate limiting
    -412: "请求过于频繁，请稍后再试",
    862: "操作频率受限",
    101: "操作频率受限",

    # Risk control
    -352: "触发风控校验，账号已被标记",

    # Internal errors
    -999: "请求失败：已达最大重试次数",

    # Report-specific errors
    12008: "该内容已被举报过",
    12012: "举报理由不适用于此类型内容",
    12019: "举报操作过于频繁",
    12022: "内容已被删除",

    # QR login errors
    86101: "二维码未扫描",
    86090: "二维码已扫描，等待确认",
    86038: "二维码已过期",
}


def get_error_message(code: int, default: str = "未知错误") -> str:
    """
    Get user-friendly error message for Bilibili API error code.

    Args:
        code: Bilibili API error code
        default: Default message if code not found

    Returns:
        User-friendly error message in Chinese
    """
    return BILIBILI_ERROR_CODES.get(code, default)
