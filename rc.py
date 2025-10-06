import os
from typing import Set, List


class RC:
    def __init__(self):
        self.load_stop_words()

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
    ]

    for test in test_cases:
        coefficient = rc.get_rc_coefficient(test)
        rc_list = rc.get_rc_list(test)
        print(f"文本: '{test}'")
        print(f"违禁词: {rc_list}")
        print(f"系数: {coefficient:.3f}")
        print("-" * 50)
