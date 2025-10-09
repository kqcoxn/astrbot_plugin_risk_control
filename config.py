from typing import Dict, List
from dataclasses import dataclass


@dataclass
class Config:
    """配置类"""

    is_enable: bool
    white_groups: List[int]
    l1_threshold: float
    group_description: str
    l2_llm_id: str
    l3_llm_id: str
    context_num: int
    l3_threshold_alert: int
    alert_message: str
    l3_threshold_withdraw: int
    l3_threshold_ban: int
    ban_time: int
    llm_rc_rt: str
    is_display_error: bool
    log_when_gen_l3: bool
    is_dev: bool

    @property
    def llm_id(self) -> str:
        """获取当前使用的LLM ID，优先使用l2_llm_id"""
        return self.l2_llm_id or self.l3_llm_id

    @property
    def l2_threshold(self) -> float:
        """获取l2阈值，使用l3_threshold作为l2的阈值"""
        return self.l3_threshold

    @property
    def l3_threshold(self) -> float:
        """获取l3阈值，使用最小值"""
        return min(
            self.l3_threshold_alert,
            self.l3_threshold_withdraw,
            self.l3_threshold_ban,
        )


def parse_config(config: Dict) -> Config:
    """
    处理配置文件

    :param config: 配置文件
    :return: 处理后的配置对象
    """
    return Config(
        is_enable=config.get("enable", False),
        white_groups=config.get("white_groups", []),
        l1_threshold=config.get("l1_threshold", 0),
        group_description=config.get("group_description", ""),
        l2_llm_id=config.get("l2_llm_id", ""),
        l3_llm_id=config.get("l3_llm_id", ""),
        context_num=config.get("context_num", 10),
        l3_threshold_alert=config.get("l3_threshold_alert", 7),
        alert_message=config.get(
            "alert_message", "检测到可能的违规内容，发言请遵守网络道德！"
        ),
        l3_threshold_withdraw=config.get("l3_threshold_withdraw", 7),
        l3_threshold_ban=config.get("l3_threshold_ban", 8),
        ban_time=config.get("ban_time", 10),
        llm_rc_rt=config.get("llm_rc_rt", "contain inappropriate content"),
        is_display_error=config.get("display_error", False),
        log_when_gen_l3=config.get("log_when_gen_l3", False),
        is_dev=config.get("dev", False),
    )
