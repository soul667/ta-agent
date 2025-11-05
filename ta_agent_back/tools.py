# 加载excel zip  
import csv
from dataclasses import dataclass, fields, asdict, field
from typing import List, Dict, Any, Type, TypeVar, get_type_hints, Optional, ClassVar, Tuple
from pathlib import Path
import re
import pprint
import xml.etree.ElementTree as ET
import os
from openai import OpenAI
from datetime import datetime


T = TypeVar('T', bound='BaseCsvRow')
T1 = TypeVar('T', bound='BaseTxtRecord')
@dataclass
class BaseCsvRow:
    """
    一个可扩展的基类，用于表示 CSV 文件中的一行 (V2)。
    
    支持两种加载模式：
    1. 自动匹配：(默认) 匹配 CSV 列标题 和 dataclass 字段名。
    2. 顺序映射：(当提供 keys_list 时) 
       将 keys_list 中的列名按顺序映射到 dataclass 的字段。
    """
    keys_list: ClassVar[Optional[List[str]]] = None
    def to_dict(self) -> Dict[str, Any]:
        """将此数据类实例转换为字典。"""
        return asdict(self)

    @classmethod
    def _coerce_value(cls, value_str: str, field_type: Type) -> Any:
        """
        内部辅助方法，用于将 CSV 中的字符串值强制转换为
        dataclass 字段声明的类型。
        """
        if value_str is None or value_str == '':
            return None
        
        try:
            if field_type is bool:
                return value_str.lower() in ('true', '1', 't', 'y', 'yes')
            # 检查是否为 Optional[T] 类型 (例如 Optional[int])
            # 注意：这是一个简化的检查，在 Python 3.10+ (Union |) 中更复杂
            if hasattr(field_type, '__origin__') and field_type.__origin__ is list:
                # 简单处理，假设是逗号分隔的列表
                return [item.strip() for item in value_str.split(',')]
                
            return field_type(value_str)
        except (ValueError, TypeError):
            print(f"警告: 无法将 '{value_str}' 转换为 {field_type}。返回 None。")
            return None
        except Exception as e:
            print(f"警告: 类型转换时出错: {e}。返回原始字符串。")
            return value_str

    @classmethod
    def load_from_csv(
                      cls: Type[T], 
                      filepath: str, 
                    #   keys_list: Optional[List[str]] = None, 
                      encoding: str = 'utf-8') -> List[T]:
        """
        从 CSV 文件加载数据行。
        
        :param filepath: CSV 文件的路径。
        :param keys_list: (可选) 要读取的 CSV 列标题列表。
                        如果提供，它将按顺序映射到 dataclass 字段。
                        如果为 None (默认)，则自动按名称匹配列标题和字段。
        :param encoding: 文件编码 (默认为 'utf-8')。
        :return: 一个由子类实例组成的列表。
        """
        keys_list = cls.keys_list
        instances = []
        
        # 获取 dataclass 的字段定义和类型
        dc_fields = fields(cls)
        field_type_map = get_type_hints(cls)

        with open(filepath, mode='r', encoding=encoding) as f:
            reader = csv.DictReader(f)
            
            # --- 新逻辑：根据是否提供了 keys_list 来决定模式 ---
            
            if keys_list is None:
                # 模式 1: 自动匹配 (与之前相同)
                dc_field_names_set = {f.name for f in dc_fields}
                for row in reader:
                    kwargs = {}
                    for field_name in dc_field_names_set:
                        if field_name in row:
                            value_str = row[field_name]
                            field_type = field_type_map[field_name]
                            kwargs[field_name] = cls._coerce_value(value_str, field_type)
                    
                    try:
                        instances.append(cls(**kwargs))
                    except TypeError as e:
                        print(f"警告 (自动模式): 无法实例化行 {row}。错误: {e}")
            
            else:
                # 模式 2: 顺序映射
                if not keys_list:
                    raise ValueError("keys_list 已提供，但列表为空。")
                
                # 按顺序获取 dataclass 字段的名称
                dc_field_names_ordered = [f.name for f in dc_fields]
                
                if len(keys_list) > len(dc_field_names_ordered):
                    raise ValueError(
                        f"keys_list 包含 {len(keys_list)} 个键, "
                        f"但 {cls.__name__} 只有 {len(dc_field_names_ordered)} 个字段。"
                    )
                
                # 创建从 "CSV列名" -> "dataclass字段名" 的映射
                # e.g., {"Username": "student_id", "First Name": "first_name"}
                mapping = dict(zip(keys_list, dc_field_names_ordered[:len(keys_list)]))
                
                for row in reader:
                    kwargs = {}
                    for csv_key, dc_field_name in mapping.items():
                        if csv_key not in row:
                            print(f"警告: 在CSV文件中未找到指定的键: '{csv_key}'")
                            continue
                        
                        value_str = row[csv_key]
                        field_type = field_type_map[dc_field_name]
                        kwargs[dc_field_name] = cls._coerce_value(value_str, field_type)
                    
                    try:
                        # 即使 kwargs 只包含部分字段 (例如 keys_list 较短)，
                        # 只要 dataclass 中剩余的字段有默认值，这也会成功。
                        instances.append(cls(**kwargs))
                    except TypeError as e:
                        print(f"警告 (映射模式): 无法实例化行 {row}。错误: {e}")

        return instances

    @classmethod
    def load_from_csv_as_dict(
                              cls: Type[T], 
                              filepath: str, 
                              key_field: str, 
                            #   keys_list: Optional[List[str]] = None, 
                              encoding: str = 'utf-8') -> Dict[str, T]:
        """
        从 CSV 文件加载数据，并返回一个以指定字段为键的字典。
        
        :param filepath: CSV 文件的路径。
        :param key_field: 用作字典键的 *dataclass 字段名* (例如 'id' 或 'student_id')。
        :param keys_list: (可选) 传递给 load_from_csv 的键列表。
        :param encoding: 文件编码 (默认为 'utf-8')。
        :return: 一个以 key_field 的值为键，子类实例为值的字典。
        """
        # 检查 key_field 是否是此类的一个有效字段
        field_names = {f.name for f in fields(cls)}
        if key_field not in field_names:
            raise ValueError(f"'{key_field}' 不是 {cls.__name__} 的有效字段。有效字段为: {field_names}")

        # 重用列表加载逻辑
        instances_list = cls.load_from_csv(filepath, encoding=encoding)
        
        instance_map = {}
        for instance in instances_list:
            key_value = getattr(instance, key_field)
            
            if key_value is None:
                print(f"警告: 实例 {instance} 的键字段 '{key_field}' 为 None，跳过索引。")
                continue

            key_str = str(key_value)
            
            if key_str in instance_map:
                print(f"警告: 发现重复键 '{key_str}'。后来的行将覆盖前面的行。")
            
            instance_map[key_str] = instance
            
        return instance_map
    
@dataclass
class Student:
    student_id: str
    student_name: str
    student_grade: int|str

@dataclass
class GradeList(BaseCsvRow):
    """
    代表一个产品。字段名必须匹配 CSV 列标题。
    类型提示 (int, str, float, bool) 将用于自动类型转换。
    """
    Username: int
    FirstName: str
    Score: str
    
    keys_list: ClassVar[List[str]] = [
        "Username",
        "First Name",
        "PA #6 Submission [Total Pts: 100 Score] |403340"
    ]

@dataclass
class BaseTxtRecord:
    """
    一个可扩展的基类，用于从单个、
    半结构化的 "Key: Value" TXT 文件加载数据。
    """

    def to_dict(self) -> Dict[str, Any]:
        """将处理后的数据类实例转换为字典。"""
        return asdict(self)

    @classmethod
    def _parse_txt_to_raw_map(cls, filepath: str, encoding: str = 'utf-8') -> Dict[str, str]:
        """
        一个通用的解析器，用于解析 "Key: Value" 文件。
        - 它将 'Key: Value' 转换为 dict item。
        - 它能处理多行值（无论是缩进的还是非缩进的）。
        """
        raw_data_map = {}
        current_key = None
        value_buffer = []

        with open(filepath, mode='r', encoding=encoding) as f:
            for line in f:
                stripped_line = line.strip()
                
                # 检查是否为新 Key (非缩进且包含':')
                # 假设 Key 本身不包含 ':'
                if (not line.startswith(('\t', '    '))) and ':' in line:
                    # 1. 保存上一个 Key 的数据
                    if current_key:
                        raw_data_map[current_key] = "\n".join(value_buffer).strip()
                    
                    # 2. 处理这个新 Key
                    try:
                        key, value = line.split(':', 1)
                        current_key = key.strip()
                        value_buffer = [value.strip()]
                    except ValueError:
                        # 异常情况：行中可能只有':'，没有Key
                        if current_key:
                            value_buffer.append(stripped_line)
                
                # 检查是否为多行值的延续（例如缩进的 'Files:'）
                elif line.startswith(('\t', '    ')) and current_key:
                    value_buffer.append(stripped_line)
                
                # 检查是否为空行（通常是分隔符）
                elif not stripped_line:
                    if current_key:
                        value_buffer.append("") # 保留空行作为分隔
                
                # 其他情况：非缩进、无冒号的行（例如 'Submission Field:' 下的内容）
                elif current_key and stripped_line:
                    value_buffer.append(stripped_line)

        # 3. 别忘了保存文件中的最后一个 Key
        if current_key:
            raw_data_map[current_key] = "\n".join(value_buffer).strip()
            
        return raw_data_map

    @classmethod
    def load_from_txt(cls: Type[T1], filepath: str, encoding: str = 'utf-8') -> T1:
        """
        从 TXT 文件加载、解析并实例化一个子类记录。
        
        :param filepath: TXT 文件的路径。
        :param encoding: 文件编码 (默认为 'utf-8')。
        :return: 一个已填充和处理的子类实例。
        """
        # 步骤 1: 将 TXT 文件解析为一个 {str: str} 的原始字典
        raw_map = cls._parse_txt_to_raw_map(filepath, encoding)
        
        # 步骤 2: 获取子类定义的 "TXT Key" -> "dataclass 字段" 的映射
        try:
            key_mapping = cls._get_key_mapping()
        except AttributeError:
            raise NotImplementedError(
                f"{cls.__name__} 必须实现 `_get_key_mapping()` 类方法。"
            )
            
        # 步骤 3: 准备传递给 dataclass 构造函数的 kwargs
        kwargs = {}
        dc_fields = {f.name for f in fields(cls)}
        
        for txt_key, dc_field_name in key_mapping.items():
            if dc_field_name not in dc_fields:
                print(f"警告: 映射中定义的字段 '{dc_field_name}' 不在 {cls.__name__} 中。")
                continue
            
            if txt_key in raw_map:
                kwargs[dc_field_name] = raw_map[txt_key]
            else:
                print(f"警告: 在TXT文件中未找到键 '{txt_key}'。将使用 None。")
                kwargs[dc_field_name] = None # 稍后 __post_init__ 会处理 None
        
        # 步骤 4: 实例化子类
        # 这将自动触发子类的 __post_init__ 方法进行数据清理
        return cls(**kwargs)

    # --- 必须被子类实现的方法 ---

    @classmethod
    def _get_key_mapping(cls) -> Dict[str, str]:
        """
        子类必须重写此方法。
        
        返回一个字典，格式为:
        {"TXT 文件中的 Key 名": "dataclass 上的字段名"}
        """
        raise NotImplementedError
    
@dataclass
class FileEntry:
    """一个简单的 dataclass 来保存文件信息"""
    original_filename: str
    filename: str

@dataclass
class SubmissionRecord(BaseTxtRecord):
    """
    代表一个具体的学生提交记录。
    它负责将原始 TXT 键映射到字段，并清理数据。
    """
    
    # --- 1. 临时原始字段 ---
    # 这些字段用于接收来自解析器的原始、未处理的字符串。
    # 它们的名字必须与 _get_key_mapping() 中的值匹配。
    # repr=False 使其在打印实例时保持整洁。
    _raw_name: Optional[str] = field(repr=False)
    _raw_assignment: Optional[str] = field(repr=False)
    _raw_date: Optional[str] = field(repr=False)
    _raw_grade: Optional[str] = field(repr=False)
    _raw_submission: Optional[str] = field(repr=False)
    _raw_comments: Optional[str] = field(repr=False)
    _raw_files: Optional[str] = field(repr=False)

    # --- 2. 最终的、干净的字段 ---
    # init=False 意味着它们不由构造函数填充，
    # 而是由 __post_init__ 填充。
    name: Optional[str] = field(init=False)
    student_id: Optional[str] = field(init=False)
    major: Optional[str] = field(init=False)
    assignment: Optional[str] = field(init=False)
    date_submitted: Optional[str] = field(init=False)
    current_grade: Optional[int] = field(init=False)
    submission_text: Optional[str] = field(init=False)
    comments: Optional[str] = field(init=False)
    files: List[FileEntry] = field(init=False, default_factory=list)

    @classmethod
    def _get_key_mapping(cls) -> Dict[str, str]:
        """
        实现基类要求：
        将 TXT 文件中的 Key 映射到此类上的 `_raw_...` 字段。
        """
        return {
            "Name": "_raw_name",
            "Assignment": "_raw_assignment",
            "Date Submitted": "_raw_date",
            "Current Grade": "_raw_grade",
            "Submission Field": "_raw_submission",
            "Comments": "_raw_comments",
            "Files": "_raw_files",
        }
    
    def __post_init__(self):
        """
        数据清理和转换的魔法在这里发生。
        我们解析 _raw_ 字段并填充最终字段。
        """
        
        # --- 解析 Name 字段 ---
        if self._raw_name:
            # 使用正则表达式匹配: "中文名(Pinyin) 专业 (ID)"
            match = re.search(r"^(.*)\((.*)\)\s(.*)\s\((.*)\)$", self._raw_name)
            if match:
                self.name = f"{match.group(1).strip()} ({match.group(2).strip()})"
                self.major = match.group(3).strip()
                self.student_id = match.group(4).strip()
            else:
                self.name = self._raw_name # 回退
                self.major = None
                self.student_id = None
        
        # --- 解析简单字段 ---
        self.assignment = self._raw_assignment
        self.date_submitted = self._raw_date
        
        # --- 解析 Grade (类型转换) ---
        try:
            self.current_grade = int(self._raw_grade)
        except (ValueError, TypeError):
            self.current_grade = None
            
        # --- 解析文本字段 (检查占位符) ---
        if self._raw_submission and "There is no student submission text data" in self._raw_submission:
            self.submission_text = None
        else:
            self.submission_text = self._raw_submission
            
        if self._raw_comments and "There are no student comments" in self._raw_comments:
            self.comments = None
        else:
            self.comments = self._raw_comments
            
        # --- 解析 Files 字段 (最复杂) ---
        self.files = []
        if self._raw_files:
            # 原始字符串包含由空行分隔的块
            file_blocks = self._raw_files.split("\n\n")
            for block in file_blocks:
                if not block.strip():
                    continue
                
                lines = block.strip().split('\n')
                try:
                    # 假设 'Original filename:' 在第一行
                    # 假设 'Filename:' 在第二行
                    orig_name = lines[0].split(":", 1)[1].strip()
                    new_name = lines[1].split(":", 1)[1].strip()
                    self.files.append(FileEntry(original_filename=orig_name, filename=new_name))
                except (IndexError, AttributeError):
                    print(f"警告: 无法解析文件块: {block}")

@dataclass 
class AssignmentBase:
    data: str = ""  # 比如c文件的内容
    filename: str = ""
    orig_name: str = ""
    def __post_init__(self):
        # read self.data from self.filename with encoding fallback
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
        for encoding in encodings:
            try:
                with open(self.filename, 'r', encoding=encoding) as f:
                    self.data = f.read()
                return
            except (UnicodeDecodeError, Exception) as e:
                continue
        
        # 如果所有编码都失败，记录警告并设为空
        print(f"警告：无法用任何编码读取文件 {self.filename}")
        self.data = ""    

# @dataclass
class Student:
    student_id: str
    name: str
    homeworks: List[AssignmentBase] = field(default_factory=list)
    
    def __init__(self, dict_data:Dict, father_path: str = ""):
        self.student_id = dict_data.get("student_id", "")
        self.name = dict_data.get("name", "")
        self.homeworks = []
        files = dict_data.get("files", [])
        for file in files:
            if not file['original_filename'].endswith('.c'):
                continue
            assignment = AssignmentBase(
                data="",
                filename=file['filename'] if father_path == "" else str(Path(father_path) / file['filename']),
                orig_name=file['original_filename']
            )
            self.homeworks.append(assignment)

class PromptXMLParser:
    """
    一个用于解析和填充 'prompt' 模板的类。
    
    支持两种格式：
    1. XML 格式：包含 <problem> 和 <code> 标签
    2. Markdown 格式：包含 {problem} 和 {code} 占位符
    """

    def __init__(self, template_string: str):
        """
        初始化解析器。

        参数:
            template_string (str): XML 或 Markdown 模板字符串。
        """
        self.template_string = template_string
        self.is_xml = False
        self.root = None
        self.problem_node = None
        self.code_node = None
        
        # 尝试作为 XML 解析
        try:
            self.root = ET.fromstring(template_string)
            self.problem_node = self.root.find("problem")
            self.code_node = self.root.find("code")
            
            if self.problem_node is not None and self.code_node is not None:
                self.is_xml = True
            else:
                # XML 解析成功但找不到必需的标签，降级为 Markdown 模式
                self.is_xml = False
        except ET.ParseError:
            # 不是有效的 XML，按 Markdown 模式处理
            self.is_xml = False

    def fill_content(self, problem: str, code: str):
        """
        将 'problem' 和 'code' 填充到模板中。
        
        :param problem: 问题描述
        :param code: 代码内容
        """
        if self.is_xml:
            # XML 模式
            if self.problem_node is not None:
                self.problem_node.text = problem
            if self.code_node is not None:
                self.code_node.text = code
        else:
            # Markdown 模式：直接替换占位符
            pass  # 在 get_filled_prompt 中处理替换

    def get_filled_prompt(self, problem: str = "", code: str = "") -> str:
        """
        返回填充内容后的完整字符串。

        参数:
            problem: 问题描述（仅在 Markdown 模式下使用）
            code: 代码内容（仅在 Markdown 模式下使用）

        返回:
            str: 包含填充数据的字符串
        """
        if self.is_xml:
            if self.root is None:
                return "错误：XML 未成功初始化。"
            return ET.tostring(self.root, encoding='unicode', method='xml')
        else:
            # Markdown 模式：替换占位符
            result = self.template_string
            result = result.replace("{problem}", problem)
            result = result.replace("{code}", code)
            return result

@dataclass
class XMLPrompt:
    problem: str
    code: str
    original_filename: str = ""

def match_file_to_prompt(original_filename: str, prompt_list: List[XMLPrompt]) -> Optional[XMLPrompt]:
    """
    根据文件名匹配对应的 XMLPrompt。
    
    :param original_filename: 学生文件的原始名称 (例如 'pa6p1.c')
    :param prompt_list: XMLPrompt 列表
    :return: 匹配的 XMLPrompt，或 None（如果未找到）
    """
    filename_lower = original_filename.lower()
    for prompt in prompt_list:
        if prompt.original_filename.lower() == filename_lower:
            return prompt
    return None

@dataclass
class MainLoader:
    excel_path: Path = Path("gc_CS111-30010973-2025FA_svdownload_2025-10-25-22-57-45.csv")
    files_path: Path = Path("./gradebook_CS111-30010973-2025FA_PA20_620Submission_2025-10-25-23-40-43")
    prompt_path: Path = Path("./prompt.md")
    output_path: Path = Path("./feedback_output")
    grade_list: Dict = field(default_factory=dict)
    parser: PromptXMLParser = field(default=None)
    client: OpenAI = field(default=None)
    prompt_list: List[XMLPrompt] = field(default_factory=list)

    def __post_init__(self):
        self.grade_list = GradeList.load_from_csv_as_dict(
            filepath=str(self.excel_path),
            key_field="Username",
            encoding='utf-8-sig'
        )
        prompt_string = ""
        try:
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                prompt_string = f.read()
        except Exception as e:
            print(f"警告：无法读取提示文件 {self.prompt_path}: {e}")
            prompt_string = "{problem}\n\n{code}"

        self.parser = PromptXMLParser(prompt_string)
        self.client = OpenAI(
            # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
            api_key="sk-9b155a5f0d8849bdb1957500a34f644e",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        # 创建输出目录
        self.output_path.mkdir(parents=True, exist_ok=True)

    def set_prompt_list(self, prompts: List[XMLPrompt]):
        """设置 XMLPrompt 列表"""
        self.prompt_list = prompts

    def get_all_students(self) -> List[Student]:
        """
        获取所有学生及其提交记录。
        
        :return: Student 对象列表
        """
        students = []
        txt_files = list(self.files_path.glob("*.txt"))
        for txt_file in txt_files:
            try:
                record = SubmissionRecord.load_from_txt(filepath=txt_file)
                record_dict = record.to_dict()
                student = Student(record_dict, father_path=str(txt_file.parent))
                students.append(student)
            except Exception as e:
                print(f"警告: 无法加载学生记录 {txt_file}: {e}")
        return students

    def get_feedback_from_qwen(self, problem_description: str, student_code: str, 
                                system_prompt: str = None) -> Tuple[str, str]:
        """
        调用 Qwen API 获取对学生代码的反馈。
        
        :param problem_description: 问题描述
        :param student_code: 学生提交的代码
        :param system_prompt: 系统提示词（可选）
        :return: (反馈文本, 建议分数) 的元组
        """
        if system_prompt is None:
            system_prompt = """你是一名 C 语言编程课程的资深助教，你的职责是评阅学生代码。
请对提交的代码进行以下方面的深入分析：
1. 总体评价：代码是否完成了题目要求？
2. 正确性分析：代码的逻辑是否正确？是否有 bug？
3. 代码质量：代码风格、效率、注释情况如何？
4. 改进建议：哪些地方可以改进？
5. 建议分数：根据完成度、正确性、代码质量，给出建议分数（满分100分）。

请用中文回答，并以"建议分数：XX/100"的格式明确指出建议分数。"""
        
        user_message = f"""题目描述：
{problem_description}

学生代码：
```c
{student_code}
```

请对这份代码提交进行详细评阅。"""
        
        try:
            response = self.client.chat.completions.create(
                model="qwen3-max",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=2000,
                stream=False  # 显式禁用流式，确保返回完整响应
            )
            
            # 提取反馈内容
            feedback = ""
            if hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    feedback = choice.message.content
            
            # 从反馈中提取分数
            score = self._extract_score_from_feedback(feedback)
            
            return feedback, score
        except Exception as e:
            import traceback
            error_msg = f"调用 Qwen API 时出错: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return error_msg, "0"
    
    def _extract_score_from_feedback(self, feedback: str) -> str:
        """
        从反馈文本中提取建议分数。
        
        :param feedback: 反馈文本
        :return: 分数字符串（例如"85"或"建议分数：85/100"）
        """
        import re
        
        # 尝试匹配 "建议分数：XX/100" 或 "建议分数：XX" 或 "建议分数:XX"
        patterns = [
            r'建议分数[：:]\s*(\d+)\s*/\s*100',
            r'建议分数[：:]\s*(\d+)',
            r'分数[：:]\s*(\d+)\s*/\s*100',
            r'分数[：:]\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, feedback)
            if match:
                score = match.group(1)
                return f"{score}/100"
        
        # 如果找不到具体的分数，返回默认值
        return "待评阅"

    def generate_feedback_markdown(self, student: Student, assignment: AssignmentBase, 
                                    prompt: XMLPrompt, feedback: str, score: str) -> str:
        """
        生成反馈 Markdown 文本。
        
        :param student: Student 对象
        :param assignment: AssignmentBase 对象
        :param prompt: XMLPrompt 对象
        :param feedback: AI 反馈文本
        :param score: 建议分数
        :return: Markdown 格式的反馈
        """
        md_content = f"""# 代码反馈报告

## 学生信息
- **学号**: {student.student_id}
- **姓名**: {student.name}
- **文件**: {assignment.orig_name}
- **建议分数**: {score}
- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 题目描述
{prompt.problem}

## 学生代码
```c
{assignment.data}
```

## 评阅意见

{feedback}

---
*本反馈由 Qwen AI 自动生成。*
"""
        return md_content

    def process_all_submissions(self, limit: int = None):
        """
        处理所有学生提交，生成反馈 MD 文件。
        
        :param limit: 处理的学生数限制（用于测试）。如果为 None，处理所有学生。
        """
        students = self.get_all_students()
        print(f"找到 {len(students)} 个学生。")
        
        if limit:
            students = students[:limit]
            print(f"限制处理到前 {limit} 个学生。")
        
        for student_idx, student in enumerate(students):
            if(student_idx<26):
                continue
            print(f"\n处理学生 [{student_idx+1}/{len(students)}]: {student.name} ({student.student_id})")
            
            for homework_idx, assignment in enumerate(student.homeworks):
                print(f"  处理作业 {homework_idx+1}: {assignment.orig_name}")
                
                # 匹配 prompt
                matched_prompt = match_file_to_prompt(assignment.orig_name, self.prompt_list)
                if matched_prompt is None:
                    print(f"    警告: 未找到匹配的 prompt，跳过此文件。")
                    continue
                
                # 调用 Qwen API 获取反馈
                print(f"    正在调用 Qwen API 获取反馈...")
                feedback, score = self.get_feedback_from_qwen(
                    matched_prompt.problem,
                    assignment.data
                )
                
                # 生成 Markdown
                md_content = self.generate_feedback_markdown(
                    student, assignment, matched_prompt, feedback, score
                )
                
                # 生成输出文件名
                safe_student_id = re.sub(r'[\\/:*?"<>|]', '_', str(student.student_id or "unknown"))
                safe_filename = re.sub(r'[\\/:*?"<>|]', '_', str(assignment.orig_name or "file"))
                output_filename = f"{safe_student_id}_{safe_filename[:-2]}_feedback.md"
                output_path = self.output_path / output_filename
                
                # 写入文件
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(md_content)
                    print(f"    已生成反馈文件: {output_filename} (分数: {score})")
                except Exception as e:
                    print(f"    错误: 无法写入文件 {output_path}: {e}")
        
        print(f"\n完成！反馈文件已保存到 {self.output_path}")

# @dataclass
# class QwenHelper:
    

if __name__ == "__main__":
    XMLPromptList: List[XMLPrompt] = []
    XMLPromptList.append(XMLPrompt(
        problem="""
        Part I: Calculating the minimum, maximum, and average of a list of numbers
        In this part of the assignment, you will write a program that finds the minimum, maximum and
        average of a list of numbers, which can be quite useful, for example, after an exam when the
        instructor provides the statistical results of the exam to students. The numbers are integers and
        stored in an array whose size is fixed and defined by a constant called N, in the same way as in
        the example on p. 164 of the text. Your program should prompt the user to input N numbers
        and read them into an array with a for loop. In the second for loop, your program should
        calculate the minimum, maximum and the average of the N numbers and print out the results
        after exiting the second for loop. (You could do everything in one for loop, but for
        simplicity, implement this program with two for loops.) Note that the average of N integers is
        not necessarily an integer, and so you will have to print out the average with the %f format
        specifier. Read p. 147 of the text to learn how to use the casting operation in C to generate a
        float from an integer division. Submit the program as pa6p1.
        """,
        code="",
        original_filename="pa6p1.c"
        ))
    XMLPromptList.append(XMLPrompt(
        problem="""
        Sorting is an important operation used in numerous computer algorithms. It refers to the
        process of rearranging a set of numbers into ascending (or descending order). Many algorithms
        exist to solve the sorting problem but bubble sort is perhaps the easiest to understand, although it
        is not the most efficient. The pseudocode below defines how bubble sort works.
        i = N;
        sorted = false;
        while ((i > 1) && (!sorted)) {
        sorted = true;
        for(j=1; j<i; j++) {
        if(a[j-1] > a[j]) {
        temp = a[j-1];
        a[j-1] = a[j];
        a[j] = temp;
        sorted = false;
        }
        }
        i--;
        }
        Based on the pseudocode above, write a program that implements bubble sort. As in Part I, your
        program should prompt the user to input N integer values and store them in an integer array.
        Then the program should proceed to sort the N numbers into the ascending (increasing) order by
        following the algorithm in the pseudocode above. Finally, the program should print out the
        sorted array of numbers. Once your program works, make sure that it is properly documented
        and name it as pa6p2.c.
        """,
        code="",
        original_filename="pa6p2.c"
        ))
    
    main_loader = MainLoader()
    main_loader.set_prompt_list(XMLPromptList)
    
    # 处理所有学生提交并生成反馈
    main_loader.process_all_submissions()