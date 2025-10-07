from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from .rc import RC
from .config import parse_config


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

        self.config = parse_config(config)
        RC.set_bot_params(context, self.config)

        if self.config.is_dev:
            logger.info(self.config)

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self):
        if self.config.is_enable:
            logger.info("风控管理已启动")
        else:
            logger.warning("风控管理未启动")

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def rc_handler(self, event: AiocqhttpMessageEvent):
        """风控检测"""
        try:
            # 群组白名单
            group_id = event.get_group_id()
            if group_id not in self.config.white_groups:
                return

            # 风控分析
            async for _yield in RC.handle(event):
                yield _yield

        except Exception as e:
            logger.error(e)
            if self.config.is_display_error:
                yield event.plain_result("发生错误: " + str(e))
