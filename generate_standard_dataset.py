import json
import os
import random
import sys

# --- 配置区 ---

# 1. 固定的系统提示词 (按你要求修改)
FIXED_SYSTEM_PROMPT = "你是一个专门负责数据分类分级的AI，请准确分类下列字段。"

# 2. 提问模板库 (保持多样性，防止过拟合)
# 路径询问模板
PATH_TEMPLATES = [
    "请判断“{node}”在健康医疗数据规范中的完整分类路径。",
    "字段“{node}”应该归属到规范的哪个位置？",
    "依据标准，“{node}”属于什么分类？",
    "请告诉我“{node}”对应的完整标准层级。",
    "遇到数据元“{node}”，我该如何对其进行标准化分类？",
    "输出“{node}”在数据规范中的层级结构。",
    "分类任务：{node}",
    "请将“{node}”映射到标准分类树中。"
]

# 结构询问模板
STRUCTURE_TEMPLATES = [
    "在标准规范中，“{node}”这个分类下具体包含哪些细分项？",
    "列举出“{node}”包含的所有子分类。",
    "“{node}”的下级数据元都有什么？",
    "请展开“{node}”分类的详细列表。",
    "数据规范定义中，“{node}”覆盖了哪些具体内容？"
]

# 多选题模板
MCQ_TEMPLATES = [
    "关于字段分类，以下哪个路径是标准规范中实际存在的？\n{options}",
    "请从下列选项中选出符合《健康医疗数据规范》的正确分类：\n{options}",
    "数据治理考核：下面哪一项是合法的标准路径？\n{options}",
    "排除干扰项，指出下列唯一的正确分类路径：\n{options}",
    "判别下列数据分类的真伪，并返回正确的那一项：\n{options}"
]

# ----------------------------------------

def generate_dataset_by_target(input_file, target_count_str):
    # 1. 参数检查
    if not os.path.exists(input_file):
        print(f"错误: 找不到输入文件 '{input_file}'")
        return
    try:
        target_total = int(target_count_str)
        if target_total < 1: raise ValueError
    except:
        print("错误: 目标生成数量必须是正整数。")
        return

    # 2. 读取数据
    lines = []
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        print("错误: 标准文件为空。")
        return

    # 3. 构建树结构 (用于生成结构题)
    all_categories = lines
    tree = {}
    for line in lines:
        parts = line.split('-')
        if len(parts) > 1:
            parent = "-".join(parts[:-1])
            child = parts[-1]
            if parent not in tree: tree[parent] = []
            tree[parent].append(child)

    # 4. 开始生成
    generated_data = []
    print(f"目标生成数量: {target_total} 条")
    print(f"正在生成中，请稍候...")

    while len(generated_data) < target_total:
        
        # --- 策略 A: 路径认知 (Path) ---
        for line in lines:
            parts = line.split('-')
            last_node = parts[-1]
            
            # 随机抽模板
            query = random.choice(PATH_TEMPLATES).format(node=last_node)
            
            generated_data.append({
                "system": FIXED_SYSTEM_PROMPT,
                "query": query,
                "response": line,
                "type": "standard_path"
            })

        # --- 策略 B: 结构认知 (Structure) ---
        for parent, children in tree.items():
            parent_name = parent.split('-')[-1]
            children_str = "、".join(children)
            
            query = random.choice(STRUCTURE_TEMPLATES).format(node=parent_name)
            
            generated_data.append({
                "system": FIXED_SYSTEM_PROMPT,
                "query": query,
                "response": f"包含以下细分项：{children_str}",
                "type": "standard_structure"
            })

        # --- 策略 C: 多选题 (MCQ) ---
        for line in lines:
            correct_answer = line
            candidates = [l for l in all_categories if l != correct_answer]
            # 随机抽3个错误选项
            if len(candidates) >= 3:
                wrong_options = random.sample(candidates, k=3)
            else:
                wrong_options = candidates
            
            options = wrong_options + [correct_answer]
            random.shuffle(options)
            
            # 格式化选项
            option_lines = []
            labels = ['A', 'B', 'C', 'D']
            for idx, opt in enumerate(options):
                option_lines.append(f"{labels[idx]}. {opt}")
            option_str = "\n".join(option_lines)
            
            query = random.choice(MCQ_TEMPLATES).format(options=option_str)
            
            generated_data.append({
                "system": FIXED_SYSTEM_PROMPT,
                "query": query,
                "response": correct_answer,
                "type": "standard_multiple_choice"
            })
            
    # 5. 后处理：打乱并截断
    random.shuffle(generated_data) # 先打乱，保证截断后的数据分布均匀
    final_dataset = generated_data[:target_total] # 精确截断到指定数量

    # 6. 输出文件
    file_dir, file_name = os.path.split(input_file)
    base_name = os.path.splitext(file_name)[0]
    output_file = os.path.join(file_dir, f"{base_name}_target_{target_total}.jsonl")

    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in final_dataset:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print("=" * 40)
    print(f"生成完成！")
    print(f"标准输入: {input_file}")
    print(f"实际生成: {len(final_dataset)} 条")
    print(f"系统提示: {FIXED_SYSTEM_PROMPT}")
    print(f"输出文件: {output_file}")
    print("=" * 40)
    print("建议接下来的操作:")
    print(f"cat {output_file} >> 你的业务数据.jsonl")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("\n参数错误。用法:")
        print("python generate_by_count.py <txt文件路径> <目标生成总数>")
        print("示例: python generate_by_count.py standard.txt 6000")
    else:
        generate_dataset_by_target(sys.argv[1], sys.argv[2])
