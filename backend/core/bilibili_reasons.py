"""
Bilibili举报原因ID映射表

提供视频、评论、用户举报原因的ID到中文名称的映射。
"""

from typing import Literal

# 视频举报原因映射表
VIDEO_REPORT_REASONS = {
    1: "违法违禁",
    2: "色情低俗",
    3: "赌博诈骗",
    4: "血腥暴力",
    5: "人身攻击",
    6: "侵犯隐私",
    7: "垃圾广告",
    8: "引战",
    9: "其他",
}

# 评论举报原因映射表（仅包含B站支持的原因）
COMMENT_REPORT_REASONS = {
    1: "垃圾广告信息",
    2: "色情低俗信息",
    3: "恶意刷屏信息",
    4: "赌博诈骗信息",
    5: "违法违禁信息",
    7: "人身攻击",
    8: "侵犯隐私",
    9: "其他",
}

# 用户举报原因映射表
USER_REPORT_REASONS = {
    1: "头像违规",
    2: "昵称违规",
    3: "签名违规",
    4: "人身攻击",
    5: "色情低俗",
    6: "垃圾广告",
    7: "违法违禁",
    8: "其他",
}

ReasonType = Literal["video", "comment", "user"]


def get_reason_name(reason_type: ReasonType, reason_id: int) -> str:
    """
    获取举报原因的中文名称

    Args:
        reason_type: 举报类型 ("video", "comment", "user")
        reason_id: 举报原因ID

    Returns:
        举报原因的中文名称，如果ID不存在则返回"未知原因"

    Examples:
        >>> get_reason_name("video", 1)
        '违法违禁'
        >>> get_reason_name("comment", 7)
        '人身攻击'
        >>> get_reason_name("user", 999)
        '未知原因'
    """
    mapping = {
        "video": VIDEO_REPORT_REASONS,
        "comment": COMMENT_REPORT_REASONS,
        "user": USER_REPORT_REASONS,
    }

    reason_dict = mapping.get(reason_type)
    if reason_dict is None:
        return "未知类型"

    return reason_dict.get(reason_id, "未知原因")
