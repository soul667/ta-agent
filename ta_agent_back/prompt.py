import xml.etree.ElementTree as ET

class PromptXMLParser:
    """
    一个用于解析和填充 'prompt' XML 模板的类。

    它使用 xml.etree.ElementTree 来解析 XML 结构,
    并提供了填充 <problem> 和 <code> 标签内容的方法。
    """

    def __init__(self, template_xml: str):
        """
        初始化解析器。

        参数:
            template_xml (str): 包含 <problem> 和 <code> 标签作为
                              占位符的 XML 模板字符串。
                              注意：XML 必须有一个单一的根元素。
        """
        self.root = None
        self.problem_node = None
        self.code_node = None
        
        try:
            # 解析字符串, ET.fromstring 返回根元素
            self.root = ET.fromstring(template_xml)
            
            # 找到关键节点
            self.problem_node = self.root.find("problem")
            self.code_node = self.root.find("code")

            if self.problem_node is None:
                print("警告: 在模板中未找到 <problem> 标签。")
            if self.code_node is None:
                print("警告: 在模板中未找到 <code> 标签。")

        except ET.ParseError as e:
            print(f"XML 解析错误: {e}")
            print("请确保 XML 格式正确且有一个单一的根元素 (例如，将所有内容包裹在 <prompt>...</prompt> 中)。")

    def fill_content(self, problem: str, code: str):
        """
        将 'problem' 和 'code' 字符串填充到 XML 节点中。
        ElementTree 会自动处理特殊字符的转义 (例如 <, >, &)。

        参数:
            problem (str): 要插入到 <problem> 标签中的问题描述。
            code (str): 要插入到 <code> 标签中的学生代码。
        """
        if self.root is None:
            print("错误：解析器未成功初始化。")
            return

        if self.problem_node is not None:
            # 直接设置文本，ElementTree 会在序列化时处理转义
            self.problem_node.text = problem
        else:
            print("错误：无法填充 <problem>，节点未找到。")

        if self.code_node is not None:
            # 直接设置文本，ElementTree 会在序列化时处理转义
            self.code_node.text = code
        else:
            print("错误：无法填充 <code>，节点未找到。")

    def get_filled_prompt(self) -> str:
        """
        返回填充内容后的完整 XML 字符串。

        返回:
            str: 包含填充数据的 XML 字符串, 编码为 UTF-8。
        """
        if self.root is None:
            return "错误：XML 未成功初始化。"

        # 序列化为字符串
        # 'unicode' 使其返回 str 而不是 bytes
        # 'method="xml"' 确保按 XML 规则处理
        return ET.tostring(self.root, encoding='unicode', method='xml')

# --- 使用示例 ---

# 1. 您的 XML 模板
# 注意：XML 要求有一个单一的根元素，所以我将您的内容包裹在了 <prompt> 标签中。
template_string = """
<prompt>
    <role>你是一名 C 语言入门课程的助教</role>
    <task>你的职责是辅助另一位主助教进行评分。你将收到一个作业问题和一份学生代码。请严格按照问题要求，对代码进行深入分析，给出一个建议的估分和检查报告（请明确指出学生哪里有错误，以及哪些地方没有遵循题目要求），以供主助教参考</task>
    <output>
        建议估分: [例如：85/100]
        检查报告：供主助教参考的检查报告
    </output>

    <problem>
    {problem}
    </problem>
    <code>
    {code}
    </code>
</prompt>
"""

# 2. 准备要填充的内容
sample_problem = "编写一个 C 程序，计算两个整数的和，并打印结果。"

# 这份代码包含了特殊字符 < 和 >，用来测试 XML 转义
sample_code = """
#include <stdio.h>

int main() {
    int a = 5;
    int b = 10;
    
    // 检查 b > a
    if (b > a) {
        printf("Sum: %d\\n", a + b);
    }
    return 0;
}
"""

# 3. 初始化解析器
parser = PromptXMLParser(template_string)

# 4. 填充内容
if parser.root:  # 检查是否成功初始化
    parser.fill_content(sample_problem, sample_code)

    # 5. 获取并打印最终的 XML
    filled_xml = parser.get_filled_prompt()
    print(filled_xml)