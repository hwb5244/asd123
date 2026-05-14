# 🎱 快乐8多周期三流派预测系统

基于 Streamlit 构建的快乐8彩票预测系统，支持多周期数据分析、相随号生成、核心池驱动等功能。

## ✨ 功能特性

### 📊 核心功能
- **号码库管理** - 支持新增、修改、删除开奖号码
- **多周期数据分析** - 冷热温号判定、012路统计
- **相随号数据** - 分析号码之间的相随关系和同频组合
- **相随号生成** - 基于历史数据生成相随号池
- **体系全流程标准化执行 SOP** - 完整的8步预测流程
- **动态趋势适配** - V7.1版本优化
- **开奖号对比** - 预测与开奖结果对比
- **命中率数据库** - 记录和分析命中率
- **核心池驱动系统** - V7.2a版本优化

### 🛡️ 数据持久化
- 自动保存开奖数据到 `lottery_data_v2.csv`
- 相随号池自动保存到 `follow_pools/` 目录
- 预测记录自动保存到 `predictions/` 目录
- 数据一旦生成即锁定，不会因新增数据而改变

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Streamlit 1.28.0+

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行程序

```bash
streamlit run app.py
```

### 访问应用

程序启动后，在浏览器中访问：
- 本地：http://localhost:8501
- 网络：http://your-ip:8501

## 📁 项目结构

```
├── app.py                 # 主应用程序
├── requirements.txt       # 依赖列表
├── README.md              # 项目说明
├── .gitignore            # Git忽略配置
├── .streamlit/           # Streamlit配置目录
│   └── config.toml       # Streamlit配置文件
├── lottery_data_v2.csv   # 开奖号码数据库（自动生成）
├── follow_pools/         # 相随号池目录（自动生成）
│   └── {period}_follow_pool.json
├── predictions/          # 预测记录目录（自动生成）
│   └── {period}_prediction.json
└── core_pool/            # 核心池目录（自动生成）
    └── core_pool_{period}.json
```

## 📋 使用说明

### Tab 1 - 号码库管理
- 新增开奖号码：输入期号和20个号码
- 修改历史数据：选择期号后修改
- 删除记录：谨慎删除，建议备份

### Tab 4 - 相随号生成
- 选择已开奖期号，系统自动生成下一期相随号池
- 相随号池一旦生成即永久锁定
- 不会因后续新增数据而改变

### Tab 7 - 开奖号对比
- 对比预测号码与实际开奖号码
- 计算命中率

## 🔧 配置说明

### Streamlit配置 (.streamlit/config.toml)

```toml
[server]
port = 8501
headless = true
maxUploadSize = 200

[theme]
base = "dark"
primaryColor = "#1565c0"
backgroundColor = "#0a1628"
secondaryBackgroundColor = "#1e3a5f"
textColor = "#ffffff"
font = "sans serif"
```

## 📊 数据说明

### 初始数据
程序内置了2025250-2026030期的开奖数据，首次运行时自动创建数据库。

### 数据备份
建议定期备份以下文件/目录：
- `lottery_data_v2.csv`
- `follow_pools/`
- `predictions/`

## 🔒 安全性

- 所有数据本地存储，不上传云端
- 建议设置合适的文件权限
- 定期备份重要数据

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

*⚠️ 免责声明：本系统仅供学习和研究使用，不构成任何投资建议。彩票购买有风险，请理性对待。*
