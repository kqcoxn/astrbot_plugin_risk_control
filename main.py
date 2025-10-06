from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


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

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def rc_handle(self, event: AstrMessageEvent):
        """获取最近一个部分的简报"""
        try:
            return
        except Exception as e:
            logger.error(e)
            yield event.plain_result("发生错误: " + str(e))
