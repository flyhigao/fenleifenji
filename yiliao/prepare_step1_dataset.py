import csv
import json
import sys
import os
import re

# ================= 配置区 =================

# 第一步专用的 System Prompt (翻译/解析模式)
SYSTEM_PROMPT = (
    "你是一个医疗数据治理领域的元数据解析专家。"
    "你的任务是根据数据库表名和字段名（可能是拼音首字母、英文缩写或混合编码），"
    "结合医疗业务上下文，精准推断并输出其对应的中文业务含义（字段注释）。"
    "直接输出中文含义即可，无需解释。"
)

def detect_encoding(file_path):
    """
    自动检测文件编码
    """
    encodings_to_try = ['utf-8', 'gb18030', 'gbk', 'gb2312', 'utf-8-sig']
    for enc in encodings_to_try:
        try:
            with open(file_path, mode='r', encoding=enc) as f:
                f.read(4096)
            return enc
        except:
            continue
    return None

def clean_description(text):
    """
    清洗 Desc 字段的逻辑
    """
    if not text:
        return ""
    
    # 1. 基础去噪：去除已知的垃圾字符
    text = text.replace("#|#|", "").replace("\r", "").replace("\n", "").replace("\t", "")
    
    # 2. 去除多余空格
    text = text.strip()
    
    # 3. 如果内容是 "NULL", "null", "无", "nan" 等无意义词，视为无效
    if text.lower() in ["null", "nan", "none", ""]:
        return ""
    
    # 4. 正则清洗：只保留中英文、数字、和常用标点(逗号分号括号)
    # 这里的逻辑是：把非这些字符的东西替换为空格，或者直接保留。
    # 为了保险，我们只过滤掉一些极其怪异的控制字符，保留业务语义符号
    # [^\u4e00-\u9fa5a-zA-Z0-9,，;；()（）\-_] 
    # 意思：除了中文、英文、数字、逗号、分号、括号、横杠下划线以外的字符，都干掉
    # (这一步视情况而定，如果你的数据里有 %, $ 等符号，可能需要保留)
    
    # 这里我们采用一个宽松策略：只要长度大于0，且不全是特殊符号
    if len(text) == 0:
        return ""

    return text

def process_csv(input_file_path):
    if not os.path.exists(input_file_path):
        print(f"错误: 找不到文件 {input_file_path}")
        return

    # 1. 检测编码
    print("正在检测编码...")
    encoding = detect_encoding(input_file_path)
    if not encoding:
        print("错误: 无法识别文件编码")
        return
    print(f"-> 编码: {encoding}")

    file_dir, file_name = os.path.split(input_file_path)
    
    # 2. 准备输出文件名
    # 输出1: 训练集 (有Desc)
    train_output_path = os.path.join(file_dir, f"{file_name}.jsonl")
    # 输出2: 待预测集 (无Desc)
    null_output_path = os.path.join(file_dir, f"{file_name}descnull.json")

    train_data = []
    null_data = []

    try:
        with open(input_file_path, mode='r', encoding=encoding, newline='') as csvfile:
            # 假设 CSV 是逗号分隔
            reader = csv.DictReader(csvfile, delimiter=',')
            
            if not reader.fieldnames:
                print("错误: CSV 文件表头读取失败")
                return

            print(f"-> 识别列名: {reader.fieldnames}")

            total_count = 0
            
            for row in reader:
                total_count += 1
                
                # 提取原始字段
                uri = row.get('uri', '').strip()     # 表名
                name = row.get('name', '').strip()   # 字段名
                raw_nickname = row.get('nickname', '') # 原始注释
                
                # 清洗注释
                cleaned_desc = clean_description(raw_nickname)
                
                # 构造 Query (这是模型输入)
                query_content = f"tablename:{uri}; colname:{name}"

                if cleaned_desc:
                    # --- 情况A: 有有效 Desc -> 生成训练集 ---
                    record = {
                        "system": SYSTEM_PROMPT,
                        "query": query_content,
                        "response": cleaned_desc
                    }
                    train_data.append(record)
                else:
                    # --- 情况B: 无有效 Desc -> 生成待补全集 ---
                    # 这里保存 raw_data 是为了方便后续 Step 2 回填
                    # 同时也保存 query 方便直接推理
                    record = {
                        "query": query_content,
                        "raw_data": row  # 保留原始行数据，方便后续人工核对或回填
                    }
                    null_data.append(record)

        # 3. 写入文件
        
        # 写入训练集 (.jsonl)
        with open(train_output_path, 'w', encoding='utf-8') as f:
            for item in train_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        # 写入待预测集 (.json - 也可以是 jsonl，这里用 jsonl 方便追加)
        with open(null_output_path, 'w', encoding='utf-8') as f:
            for item in null_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        print("-" * 40)
        print(f"处理完成！总扫描行数: {total_count}")
        print(f"\n[1] 生成训练集 (用于Step1微调): {len(train_data)} 条")
        print(f"    路径: {train_output_path}")
        print(f"    (包含有注释的数据，教模型学习 '表名+字段名 -> 中文含义')")
        
        print(f"\n[2] 生成待补全集 (用于Step2推理): {len(null_data)} 条")
        print(f"    路径: {null_output_path}")
        print(f"    (包含无注释的数据，稍后用微调后的模型来预测它们的含义)")
        print("-" * 40)

    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python prepare_step1_dataset.py <csv文件名>")
    else:
        process_csv(sys.argv[1])
