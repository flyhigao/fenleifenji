import csv
import json
import sys
import os

def detect_encoding(file_path):
    """
    自动检测文件编码
    """
    encodings_to_try = ['utf-8', 'gb18030', 'gbk', 'gb2312', 'utf-8-sig']
    for enc in encodings_to_try:
        try:
            with open(file_path, mode='r', encoding=enc) as f:
                f.read(1024)
            return enc
        except:
            continue
    return None

def convert_csv_to_qa_dataset(input_file_path):
    if not os.path.exists(input_file_path):
        print(f"错误: 找不到文件 {input_file_path}")
        return

    # 1. 自动判断编码
    print("正在检测文件编码...")
    encoding = detect_encoding(input_file_path)
    if not encoding:
        print("错误: 无法自动识别文件编码。")
        return
    print(f"-> 检测到编码为: {encoding}")

    file_dir, file_name = os.path.split(input_file_path)
    
    # --- 文件路径定义 ---
    # 1. 正常微调数据 (.jsonl 格式，适合 Swift)
    output_file_path = os.path.join(file_dir, f"{file_name}.jsonl")
    
    # 2. 空/无效数据 (按照要求: 原始名null.json)
    null_file_path = os.path.join(file_dir, f"{file_name}null.json")
    
    output_data = []
    null_data = []
    
    # 系统提示词
    system_prompt = "你是一个医疗数据治理专家。请根据给出的数据库表名、字段名和注释，判断该字段对应的健康医疗数据规范分类。"

    try:
        with open(input_file_path, mode='r', encoding=encoding, newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            
            if reader.fieldnames:
                print(f"-> 识别到的列名: {reader.fieldnames}")

            total_lines = 0
            
            for row in reader:
                total_lines += 1
                
                uri = row.get('uri', '').strip()
                name = row.get('name', '').strip()
                nickname = row.get('nickname', '').strip()
                personal_sign = row.get('personalSign', '').strip()
                business_sign = row.get('businessSign', '').strip()

                # Query
                query_content = f"tablename:{uri}; colname:{name}; Desc:{nickname}"

                has_valid_data = False

                # --- 有效数据处理 ---
                
                # 1. personalSign
                if personal_sign:
                    record = {
                        "system": system_prompt,
                        "query": query_content,
                        "response": personal_sign,
                        "type": "personalSign"
                    }
                    output_data.append(record)
                    has_valid_data = True

                # 2. businessSign
                if business_sign:
                    record = {
                        "system": system_prompt,
                        "query": query_content,
                        "response": business_sign,
                        "type": "businessSign"
                    }
                    output_data.append(record)
                    has_valid_data = True
                
                # --- 无效/空数据处理 ---
                # 如果这一行既没有 personalSign 也没有 businessSign，则存入 null 文件
                if not has_valid_data:
                    null_record = {
                        "query": query_content,
                        "info": "personalSign和businessSign均为空",
                        "raw_data": row
                    }
                    null_data.append(null_record)

        # 写入正常数据集 (.jsonl)
        with open(output_file_path, mode='w', encoding='utf-8') as jsonfile:
            for entry in output_data:
                json_str = json.dumps(entry, ensure_ascii=False)
                jsonfile.write(json_str + '\n')

        # 写入空数据集 (.json)
        # 如果你想每行一个对象(jsonl风格)
        with open(null_file_path, mode='w', encoding='utf-8') as nullfile:
            for entry in null_data:
                json_str = json.dumps(entry, ensure_ascii=False)
                nullfile.write(json_str + '\n')

        print("-" * 30)
        print(f"处理完成！总共扫描原始行数: {total_lines}")
        print(f"\n[1] 有效微调数据: {len(output_data)} 条")
        print(f"    保存位置: {output_file_path}")
        
        print(f"\n[2] 无效/空数据: {len(null_data)} 条")
        if len(null_data) > 0:
            print(f"    保存位置: {null_file_path}")
        else:
            print(f"    (没有生成该文件，因为没有发现空数据)")

    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python convert_final_v5.py <csv文件名>")
    else:
        convert_csv_to_qa_dataset(sys.argv[1])
