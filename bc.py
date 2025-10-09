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
        if time <= 0:
            return
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

    @staticmethod
    async def get_hist_messages(event: AiocqhttpMessageEvent, count=10) -> list[str]:
        """
        获取群聊消息记录

        :param event: 消息事件
        :param count: 获取数量
        """

        bot_instance = event.bot
        group_id = int(event.get_group_id())
        payloads = {
            "group_id": group_id,
            "message_seq": 0,
            "count": count,
            "reverseOrder": False,
        }
        result = await bot_instance.api.call_action("get_group_msg_history", **payloads)
        round_messages = result.get("messages", [])

        messages = []
        self_id = int(event.get_self_id())
        sender_dict = {}
        sender_mask = 1
        for msg in round_messages:
            sender_id = str(msg.get("sender", {}).get("user_id", ""))
            if sender_id != self_id:
                if sender_id not in sender_dict:
                    sender_dict[sender_id] = sender_mask
                    sender_mask += 1
                messages.append(
                    f"用户{sender_dict[sender_id]}：{msg.get('raw_message', '')}"
                )

        return messages
