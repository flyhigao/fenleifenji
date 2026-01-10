import csv
import json
import sys
import os
import random

# ================= 配置区 =================

# 最终微调的 System Prompt (双模态逻辑)
# 针对业务数据，我们需要教会模型：没注释时自己推，有注释时听注释的
FINAL_SYSTEM_PROMPT = (
    "你是一个医疗数据治理专家。请根据输入信息完成数据分类。"
    "如果输入中缺失字段注释（Desc），请先进行【语义解析】（推断其具体的业务含义），再依据《健康医疗数据规范》判断【标准分类】；"
    "如果输入中已包含字段注释（Desc），请忽略表名和字段名的语义干扰，直接基于该注释判断【标准分类】。"
    "输出格式严格遵守：'语义解析:xxx; 标准分类:xxx' 或 '标准分类:xxx'"
)

def detect_encoding(file_path):
    """
    自动检测文件编码，优先尝试中文编码
    """
    encodings = ['gb18030', 'gbk', 'utf-8', 'utf-8-sig', 'gb2312']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                f.read(4096)
            return enc
        except:
            continue
    return 'utf-8' # 保底

def load_predicted_descs(file_path):
    """
    加载 Step 2 生成的补全文件，建立映射字典
    Key: tablename:xxx; colname:xxx
    Value: predicted_desc
    """
    mapping = {}
    if not os.path.exists(file_path):
        print(f"警告: 找不到补全文件 {file_path}")
        return mapping
    
    print(f"正在加载补全数据: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            try:
                record = json.loads(line)
                # 兼容 query 字段，同时也兼容 raw_data 组合的情况
                q = record.get('query', '').strip()
                desc = record.get('predicted_desc', '').strip()
                
                # 如果只有 raw_data 没有 query (防御性编程)
                if not q and 'raw_data' in record:
                    uri = record['raw_data'].get('uri', '').strip()
                    name = record['raw_data'].get('name', '').strip()
                    q = f"tablename:{uri}; colname:{name}"

                if q and desc:
                    mapping[q] = desc
            except:
                continue
    print(f"-> 加载了 {len(mapping)} 条补全注释")
    return mapping

def clean_desc(text):
    """简单清洗 Desc"""
    if not text: return ""
    # 去除 Step2 可能残留的 <think> 标签 (以防万一)
    text = text.replace("<think>", "").replace("</think>", "")
    return text.replace("#|#|", "").strip()

def generate_step3_dataset(csv_file, step2_file, standard_file):
    # 1. 准备输出文件
    dir_name, file_name = os.path.split(csv_file)
    output_file = os.path.join(dir_name, "final_train_step3.jsonl")

    # 2. 加载补全字典
    predicted_map = load_predicted_descs(step2_file)

    # 3. 加载标准数据 (Standard Knowledge)
    standard_data = []
    if os.path.exists(standard_file):
        print(f"正在加载标准数据: {standard_file}")
        with open(standard_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        standard_data.append(entry)
                    except:
                        pass
        print(f"-> 加载了 {len(standard_data)} 条标准数据")
    else:
        print("警告: 未找到标准数据文件，将跳过。")

    # 4. 处理业务数据
    business_samples = []
    csv_encoding = detect_encoding(csv_file)
    print(f"正在处理原始 CSV: {csv_file} (编码: {csv_encoding})")

    with open(csv_file, 'r', encoding=csv_encoding, newline='') as f:
        # 你的 CSV 是逗号分隔
        reader = csv.DictReader(f, delimiter=',') 
        
        valid_count = 0
        
        for row in reader:
            # 获取 Label
            p_sign = row.get('personalSign', '').strip()
            b_sign = row.get('businessSign', '').strip()
            label = p_sign if p_sign else b_sign
            
            # 只有有 Label 的数据才对 Step 3 有用
            if not label:
                continue

            # 获取 Key
            uri = row.get('uri', '').strip()
            name = row.get('name', '').strip()
            query_key = f"tablename:{uri}; colname:{name}"

            # 获取 Desc (优先用原生的，没有则查补全字典)
            raw_desc = row.get('nickname', '').strip()
            final_desc = clean_desc(raw_desc)
            
            if not final_desc:
                # 查字典
                if query_key in predicted_map:
                    final_desc = predicted_map[query_key]
            
            # 如果依然没有 Desc，丢弃
            if not final_desc:
                continue

            valid_count += 1

            # --- 构造双模态数据 ---

            # 模式 A: 推理模式 (无 Desc -> 语义解析 + Label)
            record_a = {
                "system": FINAL_SYSTEM_PROMPT,
                "query": query_key, 
                "response": f"语义解析:{final_desc}; 标准分类:{label}"
            }
            business_samples.append(record_a)

            # 模式 B: 判别模式 (有 Desc -> Label)
            record_b = {
                "system": FINAL_SYSTEM_PROMPT,
                "query": f"{query_key}; Desc:{final_desc}",
                "response": f"标准分类:{label}"
            }
            business_samples.append(record_b)

    print(f"-> 有效业务数据行数: {valid_count}")
    print(f"-> 生成双模态样本数: {len(business_samples)} (Mode A + Mode B)")

    # 5. 混合并打乱
    final_dataset = business_samples + standard_data
    random.shuffle(final_dataset)

    # 6. 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in final_dataset:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print("=" * 50)
    print(f"Step 3 数据准备完成！")
    print(f"总数据量: {len(final_dataset)} 条")
    print(f"输出文件: {output_file}")
    print("=" * 50)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("使用方法: python prepare_step3_final.py <原始CSV> <Step2补全文件> <标准数据文件>")
    else:
        generate_step3_dataset(sys.argv[1], sys.argv[2], sys.argv[3])
