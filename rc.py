from typing import List
from pathlib import Path
from typing import List
from dataclasses import dataclass
import json

from astrbot.api import logger
from astrbot.api.star import Context
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from .config import Config
from .utils import Timer
from .bc import BotController


@dataclass
class L3Result:
    """L3风控分析结果"""

    grade: int
    reason: str
    time: float


class _RC:
    def __init__(self):
        # 加载违禁词
        self.sw_list = []
        self.load_stop_words("keyword/keywords.txt")
        # 加载提示词
        self.l2_llm_prompt = self.load_prompt("prompts/l2.txt")
        self.l3_llm_prompt = self.load_prompt("prompts/l3.txt")

    def set_bot_params(self, context: Context = None, config: Config = None):
        """Bot 配置"""
        if context is not None:
            self.context = context
        if config is not None:
            self.config = config

    async def handle(self, event: AiocqhttpMessageEvent):
        # 获取消息
        message = event.message_str.strip()
        if not message:
            return

        # 计算大模型判别系数
        l1_coefficient, l1_time = (
            (1.0, 0.0)
            if self.config.l1_threshold <= 0
            else self.get_l1_coefficient(message)
        )
        if l1_coefficient < self.config.l1_threshold:
            if self.config.is_dev:
                logger.info(
                    f"未触发风控 (敏感词库分析系数(L1)：{l1_coefficient:.2f}, 计算耗时：{l1_time:.4f}s)"
                )
            return

        # 直接使用一级风控
        if not self.config.llm_id:
            yield event.plain_result(self.config.alert_message)
            await BotController.withdraw(event)
            await BotController.ban(event, self.config.ban_time)
            logger.warning(
                f"触发风控 (敏感词库分析系数(L1)：{l1_coefficient:.2f}, 计算耗时：{l1_time:.4f}s)"
            )
            return

        # 二级风控判定
        l2_discrimination, l2_time = await self.get_l2_discrimination(message)
        if not l2_discrimination:
            if self.config.is_dev:
                logger.info(
                    "\n".join(
                        [
                            "未触发风控（由L2初步判别终止）",
                            "——————————",
                            f"原文：{message}",
                            f"  - 敏感词库分析系数(L1)：{l1_coefficient:.2f}, 计算耗时：{l1_time:.4f}s",
                            f"  - 初步判别(L2)：非存疑, 模型耗时：{l2_time:.4f}s",
                            "——————————",
                        ]
                    )
                )
            return

        # 直接使用二级风控
        if not self.config.l3_llm_id:
            yield event.plain_result(self.config.alert_message)
            await BotController.withdraw(event)
            await BotController.ban(event, self.config.ban_time)
            logger.warning(
                "\n".join(
                    [
                        "触发风控（由L2初步判别触发）",
                        "——————————",
                        f"原文：{message}",
                        f"  - 敏感词库分析系数(L1)：{l1_coefficient:.2f}, 计算耗时：{l1_time:.4f}s",
                        f"  - 初步判别(L2)：存疑, 模型耗时：{l2_time:.4f}s",
                        "——————————",
                    ]
                )
            )
            return

        # 三级风控分析
        l3_result = await self.get_l3_result(message)
        flag = False

        # 提示阈值
        if l3_result.grade >= self.config.l3_threshold_alert:
            yield event.plain_result(
                f"{self.config.alert_message}\n风控理由：{l3_result.reason}"
            )
            flag = True

        # 撤回阈值
        if l3_result.grade >= self.config.l3_threshold_withdraw:
            await BotController.withdraw(event)
            flag = True

        # 禁言阈值
        if l3_result.grade >= self.config.l3_threshold_ban:
            await BotController.ban(event, self.config.ban_time)
            flag = True

        # 风控日志
        if flag:
            logger.warning(
                "\n".join(
                    [
                        "触发风控（由L3风控分析触发）",
                        "——————————",
                        f"原文：{message}",
                        f"  - 敏感词库分析系数(L1)：{l1_coefficient:.2f}, 计算耗时：{l1_time:.4f}s",
                        f"  - 初步判别(L2)：存疑, 模型耗时：{l2_time:.4f}s",
                        f"  - 风控分析系数(L3)：{l3_result.grade}（{l3_result.reason}）, 模型耗时：{l3_result.time:.4f}s",
                        "——————————",
                    ]
                )
            )
            return

        # 未触发三级风控
        if self.config.is_dev:
            logger.info(
                "\n".join(
                    [
                        "未触发风控（由L3风控分析终止）",
                        "——————————",
                        f"原文：{message}",
                        f"  - 敏感词库分析系数(L1)：{l1_coefficient:.2f}, 计算耗时：{l1_time:.4f}s",
                        f"  - 初步判别(L2)：存疑, 模型耗时：{l2_time:.4f}s",
                        f"  - 风控分析系数(L3)：{l3_result.grade}（{l3_result.reason}）, 模型耗时：{l3_result.time:.4f}s",
                        "——————————",
                    ]
                )
            )
            return

    def load_stop_words(self, path: str | None = None) -> list[str]:
        """
        加载违禁词列表

        :param path: 违禁词文件路径
        :return: 违禁词列表
        """
        word_set = self.sw_list or []
        word_set = set(word_set)
        try:
            # 兼容相对路径：相对当前文件目录
            if not path:
                path = "keyword/keywords.txt"
            p = Path(path)
            if not p.is_absolute():
                p = Path(__file__).resolve().parent / p
            with open(p, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip().lower()
                    if line:
                        word_set.add(line)
        except FileNotFoundError:
            raise FileNotFoundError(f"无法找到违禁词文件：{path}")

        self.sw_list = sorted(word_set, key=len, reverse=True)
        return self.sw_list

    def load_prompt(self, path: str) -> str:
        """
        加载提示词

        :param path: 提示词文件路径
        :return: 提示词
        """
        try:
            p = Path(path)
            if not p.is_absolute():
                p = Path(__file__).resolve().parent / p
            with open(p, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"无法找到提示词文件：{path}")

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

    async def get_l2_discrimination(self, message: str) -> tuple[bool, float]:
        """
        计算l2风控判别

        :param message: 待处理的消息
        :return: l2风控判别
        """
        timer = Timer()

        # 初始化llm模型
        prov = self.context.get_provider_by_id(provider_id=self.config.l2_llm_id)
        if not prov:
            raise ValueError(f"未找到 LLM 模型：{self.config.l2_llm_id}")

        # 二级风控判断
        llm_resp = await prov.text_chat(prompt=f"{self.l2_llm_prompt}{message}")
        llm_resp = llm_resp.completion_text.upper()
        if "Y" in llm_resp:
            return True, timer.end()
        elif "N" in llm_resp:
            return False, timer.end()
        else:
            raise ValueError(f"意料外的风控分析结果：{llm_resp}")

    async def get_l3_result(self, message: str) -> L3Result:
        """
        计算l3风控系数

        :param message: 待处理的消息
        :return: l3风控系数
        """
        timer = Timer()

        # 初始化llm模型
        prov = self.context.get_provider_by_id(provider_id=self.config.l3_llm_id)
        if not prov:
            raise ValueError(f"未找到 LLM 模型：{self.config.l3_llm_id}")

        # 二级风控判断
        llm_resp = await prov.text_chat(prompt=f"{self.l3_llm_prompt}{message}")
        llm_resp = llm_resp.completion_text
        if self.config.llm_rc_rt in llm_resp:
            return L3Result(
                self.config.l3_threshold_withdraw,
                "大模型推理至自带的风控范畴",
                timer.end(),
            )
        try:
            llm_resp = json.loads(llm_resp)
            return L3Result(
                int(llm_resp.get("grade")), llm_resp.get("reason"), timer.end()
            )
        except Exception as e:
            raise ValueError(f"意料外的风控分析结果：{llm_resp}\n错误信息：{e}")


RC = _RC()
