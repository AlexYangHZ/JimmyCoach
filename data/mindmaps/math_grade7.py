"""Mind map data for each math knowledge point (7th grade, book 1).

Each mind map is a tree: {label, children: [{label, children: [...]}]}
"""

MINDMAPS = {
    "ch01_sec01": {
        "label": "正数和负数",
        "children": [
            {"label": "具有相反意义的量", "children": [
                {"label": "零上/零下温度"},
                {"label": "盈利/亏损"},
                {"label": "增长/减少"},
            ]},
            {"label": "正数", "children": [
                {"label": "大于0的数"},
                {"label": "用+号表示（可省略）"},
                {"label": "例：+5, 3.2, 1/2"},
            ]},
            {"label": "负数", "children": [
                {"label": "小于0的数"},
                {"label": "用-号表示"},
                {"label": "例：-3, -0.5"},
            ]},
            {"label": "0的特殊性", "children": [
                {"label": "既不是正数也不是负数"},
                {"label": "正负数的分界点"},
            ]},
            {"label": "实际应用", "children": [
                {"label": "海拔高度表示"},
                {"label": "收支记账"},
                {"label": "允许偏差范围"},
            ]},
        ]
    },
    "ch01_sec02": {
        "label": "有理数及其大小比较",
        "children": [
            {"label": "有理数分类", "children": [
                {"label": "整数：正整数、0、负整数"},
                {"label": "分数：正分数、负分数"},
                {"label": "有限小数和无限循环小数也是分数"},
            ]},
            {"label": "数轴", "children": [
                {"label": "三要素：原点、正方向、单位长度"},
                {"label": "右边的数 > 左边的数"},
            ]},
            {"label": "相反数", "children": [
                {"label": "只有符号不同的两个数"},
                {"label": "0的相反数是0"},
                {"label": "a的相反数是-a"},
            ]},
            {"label": "绝对值", "children": [
                {"label": "数轴上的点到原点的距离"},
                {"label": "|a| ≥ 0"},
                {"label": "正数绝对值=本身，负数绝对值=相反数"},
            ]},
            {"label": "比较大小", "children": [
                {"label": "正数 > 0 > 负数"},
                {"label": "两个负数，绝对值大的反而小"},
            ]},
        ]
    },
    "ch02_sec01": {
        "label": "有理数的加法与减法",
        "children": [
            {"label": "加法法则", "children": [
                {"label": "同号相加：符号不变，绝对值相加"},
                {"label": "异号相加：取绝对值大的符号，绝对值相减"},
                {"label": "互为相反数和为0"},
                {"label": "任何数加0等于本身"},
            ]},
            {"label": "运算律", "children": [
                {"label": "交换律：a+b = b+a"},
                {"label": "结合律：(a+b)+c = a+(b+c)"},
            ]},
            {"label": "减法法则", "children": [
                {"label": "减去一个数 = 加上它的相反数"},
                {"label": "a-b = a+(-b)"},
            ]},
            {"label": "加减混合", "children": [
                {"label": "统一为加法运算"},
                {"label": "运用运算律简化计算"},
            ]},
        ]
    },
    "ch02_sec02": {
        "label": "有理数的乘法与除法",
        "children": [
            {"label": "乘法法则", "children": [
                {"label": "同号得正，异号得负"},
                {"label": "绝对值相乘"},
                {"label": "任何数乘0得0"},
            ]},
            {"label": "倒数", "children": [
                {"label": "乘积为1的两个数互为倒数"},
                {"label": "0没有倒数"},
            ]},
            {"label": "乘法运算律", "children": [
                {"label": "交换律：ab = ba"},
                {"label": "结合律：(ab)c = a(bc)"},
                {"label": "分配律：a(b+c) = ab+ac"},
            ]},
            {"label": "除法法则", "children": [
                {"label": "除以一个数 = 乘它的倒数"},
                {"label": "a÷b = a×(1/b) (b≠0)"},
            ]},
        ]
    },
    "ch02_sec03": {
        "label": "有理数的乘方",
        "children": [
            {"label": "乘方的意义", "children": [
                {"label": "n个相同因数a相乘 → aⁿ"},
                {"label": "a：底数，n：指数"},
                {"label": "aⁿ：幂"},
            ]},
            {"label": "乘方法则", "children": [
                {"label": "正数的任何次幂都是正数"},
                {"label": "负数的奇次幂是负数，偶次幂是正数"},
                {"label": "0的正整数次幂是0"},
            ]},
            {"label": "科学记数法", "children": [
                {"label": "a × 10ⁿ (1 ≤ |a| < 10)"},
            ]},
            {"label": "混合运算顺序", "children": [
                {"label": "先乘方 → 再乘除 → 最后加减"},
                {"label": "有括号先算括号内"},
            ]},
        ]
    },
    "ch03_sec01": {
        "label": "列代数式表示数量关系",
        "children": [
            {"label": "代数式概念", "children": [
                {"label": "用运算符号连接数和字母"},
                {"label": "单独一个数或字母也是代数式"},
            ]},
            {"label": "书写规范", "children": [
                {"label": "数字在前，字母在后"},
                {"label": "乘号省略或写·"},
                {"label": "除号写成分数形式"},
            ]},
            {"label": "列代数式", "children": [
                {"label": "读懂题意找数量关系"},
                {"label": "用字母表示未知量"},
            ]},
        ]
    },
    "ch03_sec02": {
        "label": "代数式的值",
        "children": [
            {"label": "求值步骤", "children": [
                {"label": "① 代入：字母替换为数值"},
                {"label": "② 计算：按运算顺序求值"},
            ]},
            {"label": "注意事项", "children": [
                {"label": "负数代入要加括号"},
                {"label": "分数代入要加括号"},
            ]},
        ]
    },
    "ch04_sec01": {
        "label": "整式",
        "children": [
            {"label": "单项式", "children": [
                {"label": "数字与字母的乘积"},
                {"label": "系数：数字因数"},
                {"label": "次数：所有字母指数之和"},
            ]},
            {"label": "多项式", "children": [
                {"label": "几个单项式的和"},
                {"label": "项：每个单项式"},
                {"label": "次数：最高次项的次数"},
            ]},
            {"label": "整式 = 单项式 + 多项式"},
        ]
    },
    "ch04_sec02": {
        "label": "整式的加法与减法",
        "children": [
            {"label": "同类项", "children": [
                {"label": "字母相同，相同字母指数也相同"},
                {"label": "常数项都是同类项"},
            ]},
            {"label": "合并同类项", "children": [
                {"label": "系数相加，字母部分不变"},
            ]},
            {"label": "去括号法则", "children": [
                {"label": "+号后去括号：各项不变号"},
                {"label": "-号后去括号：各项都变号"},
            ]},
            {"label": "整式加减步骤", "children": [
                {"label": "去括号 → 找同类项 → 合并"},
            ]},
        ]
    },
    "ch05_sec01": {
        "label": "方程",
        "children": [
            {"label": "方程概念", "children": [
                {"label": "含有未知数的等式"},
                {"label": "一元一次方程：一个未知数，次数为1"},
            ]},
            {"label": "等式的性质", "children": [
                {"label": "两边加/减同一个数，等式成立"},
                {"label": "两边乘/除同一个非零数，等式成立"},
            ]},
            {"label": "解方程基础", "children": [
                {"label": "利用等式性质变形"},
                {"label": "目标：x = a 的形式"},
            ]},
        ]
    },
    "ch05_sec02": {
        "label": "解一元一次方程",
        "children": [
            {"label": "一般步骤", "children": [
                {"label": "① 去分母"},
                {"label": "② 去括号"},
                {"label": "③ 移项（过等号变号）"},
                {"label": "④ 合并同类项"},
                {"label": "⑤ 系数化为1"},
            ]},
            {"label": "检验", "children": [
                {"label": "将解代入原方程验证"},
            ]},
        ]
    },
    "ch05_sec03": {
        "label": "实际问题与一元一次方程",
        "children": [
            {"label": "解题步骤", "children": [
                {"label": "① 审题找等量关系"},
                {"label": "② 设未知数"},
                {"label": "③ 列方程"},
                {"label": "④ 解方程"},
                {"label": "⑤ 检验并作答"},
            ]},
            {"label": "常见类型", "children": [
                {"label": "行程问题"},
                {"label": "工程问题"},
                {"label": "利润问题"},
                {"label": "配套问题"},
            ]},
        ]
    },
    "ch06_sec01": {
        "label": "几何图形",
        "children": [
            {"label": "立体图形", "children": [
                {"label": "柱体：圆柱、棱柱"},
                {"label": "锥体：圆锥、棱锥"},
                {"label": "球体"},
            ]},
            {"label": "平面图形", "children": [
                {"label": "点、线、面、体"},
                {"label": "从不同方向看立体图形"},
            ]},
            {"label": "展开图", "children": [
                {"label": "立体图形→平面展开图"},
            ]},
        ]
    },
    "ch06_sec02": {
        "label": "直线、射线、线段",
        "children": [
            {"label": "直线", "children": [
                {"label": "无端点，向两方无限延伸"},
                {"label": "两点确定一条直线"},
            ]},
            {"label": "射线", "children": [
                {"label": "一个端点，向一方无限延伸"},
            ]},
            {"label": "线段", "children": [
                {"label": "两个端点，可度量长度"},
                {"label": "两点之间线段最短"},
                {"label": "中点：将线段分成两等份"},
            ]},
        ]
    },
    "ch06_sec03": {
        "label": "角",
        "children": [
            {"label": "角的概念", "children": [
                {"label": "有公共端点的两条射线"},
                {"label": "顶点、边"},
            ]},
            {"label": "角的度量", "children": [
                {"label": "度(°)、分(′)、秒(″)"},
                {"label": "1°=60′, 1′=60″"},
            ]},
            {"label": "角的分类", "children": [
                {"label": "锐角：0°<α<90°"},
                {"label": "直角：α=90°"},
                {"label": "钝角：90°<α<180°"},
            ]},
            {"label": "角的关系", "children": [
                {"label": "余角：和为90°"},
                {"label": "补角：和为180°"},
                {"label": "角平分线"},
            ]},
        ]
    },
    # Shorter entries for reading/history activities
    "ch01_reading": {
        "label": "用正负数表示允许偏差",
        "children": [
            {"label": "允许偏差的意义", "children": [
                {"label": "产品尺寸不能完全精确"},
                {"label": "在允许范围内即为合格"},
            ]},
            {"label": "表示方法", "children": [
                {"label": "标准值 ± 偏差"},
                {"label": "例：40mm ± 0.05mm"},
            ]},
        ]
    },
    "ch01_history": {
        "label": "漫漫长路识负数",
        "children": [
            {"label": "历史发展", "children": [
                {"label": "中国最早使用负数（《九章算术》）"},
                {"label": "用算筹红黑表示正负"},
            ]},
            {"label": "负数接受过程", "children": [
                {"label": "从拒绝到逐渐接受"},
                {"label": "现实生活的推动"},
            ]},
        ]
    },
}


def get_mindmap(section_id: str) -> dict | None:
    """Return mind map data for a section, or None."""
    return MINDMAPS.get(section_id)
