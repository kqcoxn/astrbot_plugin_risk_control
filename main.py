from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig

import time

from .rc import rc


@register(
    "astrbot_plugin_risk_control",
    "kqcoxn",
    "级联式风控处理插件",
    "0.1",
    "https://github.com/kqcoxn/astrbot_plugin_risk_control",
)
class RiskControl(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)

        self.config = config
        self.white_groups: list[str] = config.get("white_groups", [])
        self.l1_threshold: float = config.get("l1_threshold", 0.1)
        self.llm_id = config.get("llm_id", "")
        self.l2_threshold = config.get("l2_threshold", 0.5)
        self.is_dev = config.get("dev", False)

        if self.is_dev:
            logger.info(self.config)

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self):
        logger.info("风控管理已启动")

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def rc_handler(self, event: AstrMessageEvent):
        """风控检测"""
        try:
            message_str = event.message_str
            if not message_str:
                return

            # 计算一级风控系数
            start_time = time.time()
            l1_coefficient = rc.get_rc_coefficient(message_str)
            l1_diff = time.time() - start_time

            if l1_coefficient < self.l1_threshold:
                if self.is_dev:
                    logger.info(
                        f"未触发风控 (l1风控系数：{l1_coefficient:.2f}, 计算耗时：{l1_diff:.4f}s)"
                    )
                return

            # 直接使用一级风控
            if not self.llm_id:
                if self.is_dev:
                    logger.info(
                        f"触发风控 (l1风控系数：{l1_coefficient:.2f}, 计算耗时：{l1_diff:.4f}s)"
                    )
                return

            # 初始化llm模型
            prov = self.context.get_provider_by_id(provider_id=self.llm_id)
            if not prov:
                logger.error(f"未找到 LLM 模型：{self.llm_id}")
                return

            # 二级风控判断
            start_time = time.time()
            llm_resp = await prov.text_chat(
                prompt=f"{rc.llm_prompt}\n\n-----\n\n用户消息：\n{message_str}"
            )
            l2_coefficient = float(llm_resp.completion_text)
            l2_diff = time.time() - start_time

            # 触发风控
            if l2_coefficient >= self.l2_threshold:
                if self.is_dev:
                    logger.info(
                        "\n".join(
                            [
                                "未触发风控",
                                "——————————",
                                f"原文：{message_str}",
                                f"  - l1风控系数：{l1_coefficient:.2f}, 计算耗时：{l1_diff:.4f}s",
                                f"  - l2风控系数：{l2_coefficient:.2f}, 模型耗时：{l2_diff:.4f}s",
                                "——————————",
                            ]
                        )
                    )
                return
            else:
                if self.is_dev:
                    logger.info(
                        "\n".join(
                            [
                                "触发风控！",
                                "——————————",
                                f"原文：{message_str}",
                                f"  - l1风控系数：{l1_coefficient:.2f}, 计算耗时：{l1_diff:.4f}s",
                                f"  - l2风控系数：{l2_coefficient:.2f}, 模型耗时：{l2_diff:.4f}s",
                                "——————————",
                            ]
                        )
                    )
                return

        except Exception as e:
            logger.error(e)
            yield event.plain_result("发生错误: " + str(e))
