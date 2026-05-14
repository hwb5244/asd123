# 📊 数据持久化说明

## 概述

本系统采用本地文件存储方式进行数据持久化，确保数据不会因程序重启或休眠而丢失。

## 📁 数据存储结构

### 1. 开奖号码数据库

```
lottery_data_v2.csv
├── 期号 (索引)
├── 第1位 - 第20位 (20个开奖号码)
```

**特点：**
- CSV格式，易于备份和迁移
- 自动排序，按期号升序排列
- 首次运行时自动创建，包含预置数据

### 2. 相随号池

```
follow_pools/{period}_follow_pool.json
├── n_period: 基础期号
├── n_plus_1: 目标期号
├── n_nums: 基础期开奖号码
├── follow_details: 每个号码的相随详情
├── follow_pool: 最终相随号池
├── generated_at: 生成时间
├── data_version: 生成时的数据量版本
└── analysis_period: 分析周期(80期)
```

**特点：**
- 一旦生成即永久锁定
- 不会因新增开奖数据而改变
- 支持数据完整性校验

### 3. 预测记录

```
predictions/{period}_prediction.json
predictions/{period}_prediction1.json
predictions/{period}_prediction2.json
├── period: 期号
├── core_pool: 核心池号码
├── combinations: 生成的组合
├── generated_at: 生成时间
└── ...其他预测参数
```

### 4. 核心池

```
core_pool/core_pool_{period}.json
├── period: 期号
├── core_pool: 核心池号码列表
└── generated_at: 生成时间
```

## 🔒 数据保护机制

### 1. 自动锁定机制
- 相随号池生成后自动锁定
- 历史记录不会被覆盖
- 提供"强制重新生成"选项（如需更新）

### 2. 数据完整性校验
- 自动检测原始数据是否被修改
- 显示校验状态提示
- 确保预测结果的可追溯性

### 3. 版本记录
- 记录生成时的数据版本
- 记录分析周期参数
- 便于回溯和审计

## 🛡️ 数据备份建议

### 定期备份
建议定期备份以下文件/目录：

```bash
# 创建备份
tar -czvf backup_$(date +%Y%m%d).tar.gz \
  lottery_data_v2.csv \
  follow_pools/ \
  predictions/

# 或者复制到备份目录
cp lottery_data_v2.csv backup/
cp -r follow_pools/ backup/
cp -r predictions/ backup/
```

### 备份频率
- 每日备份：适用于频繁更新数据
- 每周备份：适用于定期更新数据
- 重要操作前备份：如批量修改、删除数据前

## 🔄 数据迁移

### 迁移步骤
1. 停止运行中的应用
2. 复制以下文件/目录到新位置：
   - `lottery_data_v2.csv`
   - `follow_pools/`
   - `predictions/`
   - `core_pool/`
3. 启动新位置的应用
4. 验证数据是否正确加载

### 注意事项
- 确保目标环境已安装所有依赖
- 确保文件权限正确（读写权限）
- 迁移后建议验证数据完整性

## 📝 数据恢复

### 从备份恢复
```bash
# 停止应用
# 解压备份
tar -xzvf backup_YYYYMMDD.tar.gz

# 或者从备份目录复制
cp backup/lottery_data_v2.csv .
cp -r backup/follow_pools/ .
cp -r backup/predictions/ .

# 启动应用
streamlit run 未命名.py
```

### 从预置数据恢复
如果数据库文件损坏或丢失，程序会自动使用内置的预置数据重新创建数据库。

## ⚠️ 注意事项

1. **不要手动修改数据文件**：所有数据操作请通过应用界面进行
2. **定期检查数据完整性**：使用Tab 4的数据校验功能
3. **保持足够的磁盘空间**：数据会随着时间增长
4. **谨慎删除数据**：删除后无法恢复（除非有备份）

## 📊 数据恢复测试建议

定期进行数据恢复测试，确保备份有效：

1. 创建测试备份
2. 模拟数据丢失（重命名或删除数据文件）
3. 从备份恢复
4. 验证数据是否完整恢复
5. 记录测试结果

---

*保持数据安全是系统稳定运行的关键！*
