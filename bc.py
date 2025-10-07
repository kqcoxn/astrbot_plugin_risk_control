from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)


class BotController:
    """Bot控制器"""

    @staticmethod
    async def withdraw(event: AiocqhttpMessageEvent):
        """
        撤回消息

        :param event: 消息事件
        """

        client = event.bot
        self_id = int(event.get_self_id())
        message_id = int(event.message_obj.message_id)
        await client.delete_msg(
            message_id=message_id,
            self_id=self_id,
        )

    @staticmethod
    async def ban(event: AiocqhttpMessageEvent, time=10):
        """
        禁言

        :param event: 消息事件
        :param time: 禁言时长 (minutes)
        """
        client = event.bot
        group_id = int(event.get_group_id())
        user_id = int(event.get_sender_id())
        self_id = int(event.get_self_id())
        await client.set_group_ban(
            group_id=group_id,
            user_id=user_id,
            duration=time * 60,
            self_id=self_id,
        )
