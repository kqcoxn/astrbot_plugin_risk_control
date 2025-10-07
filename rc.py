from typing import List


from astrbot.api import logger
from astrbot.api.star import Context, Star, register
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from .config import Config
from utils import Timer


class _RC:
    def __init__(self):
        # 加载违禁词
        self.load_stop_words("keyword/keywords.txt")

    def set_bot_params(self, context: Context = None, config: Config = None):
        """Bot 配置"""
        if context is not None:
            self.context = context
        if config is not None:
            self.config = config

    async def handle(self, event: AiocqhttpMessageEvent):
        # 获取消息
        message_str = event.message_str
        if not message_str:
            return

        # 计算大模型判别系数
        l1_coefficient, l1_time = self.get_l1_coefficient(message_str)
        if l1_coefficient < self.config.l1_threshold:
            if self.config.is_dev:
                logger.info(
                    f"未触发风控 (l1风控系数：{l1_coefficient:.2f}, 计算耗时：{l1_time:.4f}s)"
                )
            return

        # 直接使用一级风控
        if not self.config.llm_id:
            async for _yield in self.treat(event):
                yield _yield
            logger.info(
                f"触发风控 (l1风控系数：{l1_coefficient:.2f}, 计算耗时：{l1_time:.4f}s)"
            )
            return

        # 初始化llm模型
        prov = self.context.get_provider_by_id(provider_id=self.config.llm_id)
        if not prov:
            logger.error(f"未找到 LLM 模型：{self.config.llm_id}")
            return

        # 二级风控判断
        timer = Timer()
        llm_resp = await prov.text_chat(
            prompt=f"{RC.llm_prompt}\n\n-----\n\n用户消息：\n{message_str}"
        )
        l2_coefficient = float(llm_resp.completion_text)
        l2_diff = timer.end()

        # 未触发风控
        if l2_coefficient < self.config.l2_threshold:
            if self.config.is_dev:
                logger.info(
                    "\n".join(
                        [
                            "未触发风控",
                            "——————————",
                            f"原文：{message_str}",
                            f"  - l1风控系数：{l1_coefficient:.2f}, 计算耗时：{l1_time:.4f}s",
                            f"  - l2风控系数：{l2_coefficient:.2f}, 模型耗时：{l2_diff:.4f}s",
                            "——————————",
                        ]
                    )
                )
            return
        # 触发风控
        else:
            async for _result in RC.treat(event):
                yield _result
            logger.info(
                "\n".join(
                    [
                        "触发风控！",
                        "——————————",
                        f"原文：{message_str}",
                        f"  - l1风控系数：{l1_coefficient:.2f}, 计算耗时：{l1_time:.4f}s",
                        f"  - l2风控系数：{l2_coefficient:.2f}, 模型耗时：{l2_diff:.4f}s",
                        "——————————",
                    ]
                )
            )
            return

    def load_stop_words(self, path: str) -> list[str]:
        """
        加载违禁词列表

        :param path: 违禁词文件路径
        :return: 违禁词列表
        """
        word_set = self.sw_list or []
        word_set = set(word_set)
        try:
            with open(path, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip().lower()
                    if line:
                        word_set.add(line)
        except FileNotFoundError:
            raise FileNotFoundError(f"无法找到违禁词文件：{path}")

        self.sw_list = sorted(word_set, key=len, reverse=True)
        return self.sw_list

    def get_l1_coefficient(self, message: str) -> tuple[float, float]:
        """
        计算l1风控系数

        :param message: 消息内容
        :return: l1风控系数 (0-1.0)
        """
        timer = Timer()

        # 消息预处理
        message = message.strip().lower()
        if not message:
            return 0.0, timer.end()

        # 检查违禁词
        rc_list = self.get_rc_list(message)
        if not rc_list:
            return 0.0, timer.end()

        # 计算l1系数
        matched_positions = set()
        for word in rc_list:
            start = 0
            while True:
                pos = message.find(word, start)
                if pos == -1:
                    break
                for i in range(pos, pos + len(word)):
                    matched_positions.add(i)
                start = pos + 1
        coefficient = min(len(matched_positions) / len(message), 1.0)

        return coefficient, timer.end()

    def get_rc_list(self, message: str) -> List[str]:
        """
        解析消息中包含的违禁词

        :param message: 待解析的消息
        :return: 违禁词列表
        """
        if not self.sw_list:
            self.load_stop_words()

        rc_list = []
        matched_positions = set()
        for sw in self.sw_list:
            start = 0
            found = False
            while True:
                pos = message.find(sw, start)
                if pos == -1:
                    break
                overlap = False
                for i in range(pos, pos + len(sw)):
                    if i in matched_positions:
                        overlap = True
                        break
                if not overlap:
                    rc_list.append(sw)
                    found = True
                    # 标记这些位置为已匹配
                    for i in range(pos, pos + len(sw)):
                        matched_positions.add(i)
                start = pos + 1

        return rc_list

    async def treat(self, event: AiocqhttpMessageEvent):
        """
        风控处理

        :param event: 消息事件
        """
        client = event.bot
        group_id = int(event.get_group_id())
        user_id = int(event.get_sender_id())
        self_id = int(event.get_self_id())
        message_id = int(event.message_obj.message_id)

        # 撤回
        await client.delete_msg(
            message_id=message_id,
            self_id=self_id,
        )

        # 禁言
        await client.set_group_ban(
            group_id=group_id,
            user_id=user_id,
            duration=10 * 60,
            self_id=self_id,
        )

        # 提示
        yield event.plain_result(
            "检测到可能的违规内容，发言请遵守网络道德！\n（若误判请联系群风纪委员处理）"
        )
        event.stop_event()


RC = _RC()

if __name__ == "__main__":
    # 测试示例
    test_cases = [
        "妈",  # 单个词
        "你妈",  # 包含重叠词
        "你妈妈",  # 包含多个重叠词
        "正常文本",  # 无违禁词
        "你妈真是个好人，妈妈我爱你",  # 多个违禁词
        "不要理解傻逼和串子以及真正的孝子",  # 模棱两可
    ]

    for test in test_cases:
        coefficient = RC.get_l1_coefficient(test)
        rc_list = RC.get_rc_list(test)
        print(f"文本: '{test}'")
        print(f"违禁词: {rc_list}")
        print(f"系数: {coefficient:.3f}")
        print("-" * 50)
