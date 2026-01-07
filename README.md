gao@hahapc:~/Documents/fenleifenji$ python convert_data.py dataAssetsDownloadCsv1767599528binhaiziyeHIS.csv
正在检测文件编码...
-> 检测到编码为: gb18030
-> 识别到的列名: ['assetsType', 'dbType', 'name', 'nickname', 'uri', 'personalSign', 'businessSign']
------------------------------
处理完成！总共扫描原始行数: 6084

[1] 有效微调数据: 5892 条
    保存位置: dataAssetsDownloadCsv1767599528binhaiziyeHIS.csv.jsonl

[2] 无效/空数据: 543 条
    保存位置: dataAssetsDownloadCsv1767599528binhaiziyeHIS.csvnull.json




gao@hahapc:~/Documents/fenleifenji$ python generate_standard_dataset.py standard.txt  9000
目标生成数量: 9000 条
正在生成中，请稍候...
========================================
生成完成！
标准输入: standard.txt
实际生成: 9000 条
系统提示: 你是一个专门负责数据分类分级的AI，请准确分类下列字段。
输出文件: standard_target_9000.jsonl
========================================
建议接下来的操作:
cat standard_target_9000.jsonl >> 你的业务数据.jsonl

