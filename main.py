from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .rc import rc


@register(
    "astrbot_plugin_risk_control",
    "kqcoxn",
    "级联式风控处理插件",
    "0.1",
    "https://github.com/kqcoxn/astrbot_plugin_risk_control",
)
class RiskControl(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self):
        logger.info("风控管理已启动")

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def rc_handle(self, event: AstrMessageEvent):
        """风控检测"""
        try:
            message_str = event.message_str
            logger.info(f"风控系数：{rc.get_rc_coefficient(message_str):.2f}")

        except Exception as e:
            logger.error(e)
            yield event.plain_result("发生错误: " + str(e))
