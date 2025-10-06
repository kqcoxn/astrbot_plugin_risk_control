import os
from typing import Set, List

from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)


class RC:
    def __init__(self):
        self.load_stop_words()
        self.llm_prompt = "\n".join(
            [
                "**你是一个风控检查器，用于检测用户在群聊中的发言是否符合网络道德。**",
                "",
                "## 网络道德：",
                "",
                "### “绝对红线”清单（零容忍）",
                "",
                "这些内容无论是否玩笑，在任何文化和语境下都具有极高的危害性，通常也是法律明令禁止的，例如：",
                "",
                "- 严重违法内容​​：明确策划或宣扬恐怖主义、暴力犯罪（如详细谋杀、爆炸方法）、儿童色情、人口贩卖等",
                "- 严重的、直接的暴力威胁​​：针对个人或群体的明确人身威胁（如“我要杀了XXX”、“我们今晚去烧了那栋楼”）",
                "- 极度仇恨言论​​：基于种族、民族、宗教、国籍、性别、性取向、残疾等，公开发布旨在煽动歧视、敌意或暴力的言论。",
                "",
                "无论是否为开玩笑，均判定为不符合网络道德。",
                "",
                "### 对于非“红线”内容，进行多维度交叉分析",
                "",
                "对于大多数处于灰色地带的言论，需要从以下几个维度进行加权判断：",
                "",
                "1. 词汇与主题分析（What is said?） ​​关键词识别​​：是否包含公认的侮辱性词汇、脏话、歧视性用语（如涉及种族、性别、残疾的贬损词）？ ​​主题敏感性​​：话题是否涉及敏感议题（如性、暴力、灾难、悲剧事件）？例如，关于地震、空难的“玩笑”风险极高。",
                "2. 句式与情感分析（How is it said?） ​​夸张与反讽句式​​：句子是否包含明显的夸张、比喻或反讽结构？例如，“我饿得能吃下一头牛”显然是夸张，但“这个计划完美得就像一场灾难”就可能是反讽，需要结合主题看。 ​​表情符号和语气词​​：句尾是否有😂、🐶（狗头保命）、/j（joking的缩写）、/s（sarcasm的缩写）等用于标识玩笑或反讽的符号？​​这是非常重要的信号​​。 ​​情感极性​​：AI可以分析这句话的情感是极端的负面，还是中性的调侃。",
                "3. 概率与常见模式分析（Pattern） ​​常见玩笑模板​​：系统可以学习常见的玩笑模式。例如，“友尽了”、“拔刀吧”、“你号没了”等在特定社群中通常是安全的调侃。 ​​攻击性概率​​：训练模型来预测一句话被多数人认为是攻击性言论的概率。",
                "",
                "### 合适的玩笑或者客观的评价",
                "",
                "这个标准无法做到100%精确，但可以作为一个强大的​​分析框架​​。核心在于​​意图（Intent）​​ 和​​影响（Impact）​​ 的权衡。核心原则：先看意图，再看影响​。",
                "",
                "1. 意图（Intent）：发言者的目的是什么？​​ ​​合适的玩笑​​：目的是​​创造欢乐、增进亲和、幽默地解构压力​​。核心是​​共享​​（Shared enjoyment）。 ​​客观的评价​​：目的是​​表达观点、提出批评、分享信息​​。核心是​​交流​​（Exchange of ideas）。",
                "2. 影响（Impact）：听到这句话的人感受如何？​​​​合适的玩笑​​：影响是​​中性或积极的​​，不会让群体内的任何人感到被针对、羞辱或排斥。​​客观的评价​​：影响是​​建设性的​​，即使观点尖锐，也能推动讨论，而非引发人身攻击。",
                "",
                "## 输入与输出",
                "",
                "- 输入：用户在群聊中发送的消息",
                "- 输出：恶意程度，范围为0-1，0表示无恶意，1表示完全恶意。仅返回最多两位小数的浮点数即可，不要返回其他分析。",
            ]
        )

    async def treat(self, event: AiocqhttpMessageEvent):
        """风控处理"""
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

    def get_rc_coefficient(self, message: str) -> float:
        """
        计算风控系数

        :param message: 消息内容
        :return: 风控系数 (0-1.0)
        """
        message = message.strip().lower()
        if not message:
            return 0.0

        rc_list = self.get_rc_list(message)
        if not rc_list:
            return 0.0

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

        rc_length = len(matched_positions)
        return min(rc_length / len(message), 1.0)

    def get_rc_list(self, message: str) -> List[str]:
        """解析违禁词"""
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

    def load_stop_words(
        self,
        path=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "keyword", "keywords.txt"
        ),
    ) -> list[str]:
        """获取违禁词列表"""
        word_set = set()
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


rc = RC()

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
        coefficient = rc.get_rc_coefficient(test)
        rc_list = rc.get_rc_list(test)
        print(f"文本: '{test}'")
        print(f"违禁词: {rc_list}")
        print(f"系数: {coefficient:.3f}")
        print("-" * 50)
