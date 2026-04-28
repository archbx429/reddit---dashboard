# SQLite Cloud 设置指南

这个指南将帮助您设置云数据库，使本地和 Streamlit Cloud 能够共享同一个数据库。

## 步骤 1：创建 SQLite Cloud 账户

1. 访问 **https://sqlitecloud.io**
2. 点击 "Get Started Free" 注册账户
3. 验证邮箱后登录

## 步骤 2：创建数据库

1. 在 SQLite Cloud 仪表板中，点击 "Create Database"
2. 选择一个数据库名称（例如 `reddit-dashboard`）
3. 选择地区（建议选择离您最近的）
4. 点击 "Create"

## 步骤 3：获取连接字符串

1. 进入刚创建的数据库
2. 点击 "Connection" 或 "Credentials"
3. 复制 **Connection String**（格式：`sqlitecloud://user:password@host/database`）
4. 保存这个字符串

## 步骤 4：配置本地环境

### 方案 A：使用 .env 文件（本地开发）

在项目根目录创建或编辑 `.env` 文件：

```env
GEMINI_API_KEY=your_gemini_api_key
SQLITE_CLOUD_URL=sqlitecloud://user:password@host/database
```

然后安装依赖并测试：

```bash
pip install sqlitecloud
python3 diagnose.py
```

### 方案 B：继续使用本地 SQLite（推荐先测试）

保持不设置 `SQLITE_CLOUD_URL`，系统会自动使用本地 `reddit_monitor.db`。

## 步骤 5：配置 Streamlit Cloud

### 在 Streamlit Cloud 中设置 Secrets：

1. 登录 **https://share.streamlit.io**
2. 进入您的应用 "reddit-dashboard-pocolab"
3. 点击右上角 "..."，选择 "Settings"
4. 在左侧菜单选择 "Secrets"
5. 添加以下内容（替换为您的连接字符串）：

```toml
SQLITE_CLOUD_URL = "sqlitecloud://user:password@host/database"
GEMINI_API_KEY = "your_gemini_api_key"
```

6. 点击 "Save"
7. Streamlit 会自动重新部署应用

## 步骤 6：测试

### 本地测试：

```bash
# 如果设置了 SQLITE_CLOUD_URL，会连接云数据库
# 否则使用本地 SQLite
python3 diagnose.py
```

### 网站测试：

1. 点击本地网站的"开始爬取"按钮
2. 等待爬取和分析完成
3. 访问 Streamlit Cloud 上的应用
4. 刷新页面，应该会看到新数据

## 故障排除

### 问题 1：连接字符串格式错误
**症状**：应用启动时出错
**解决**：确保格式正确：`sqlitecloud://user:password@host/database`

### 问题 2：在 Streamlit Cloud 中看不到数据
**症状**：显示 "暂无数据"
**解决**：
1. 检查 Streamlit Cloud 的 Secrets 是否正确设置
2. 在本地运行 `diagnose.py` 确保云数据库正常工作
3. 点击"开始爬取"在本地添加数据，然后检查 Streamlit Cloud

### 问题 3：本地连接云数据库很慢
**症状**：查询响应慢
**解决**：这是正常的网络延迟，通常不会成为问题。可以考虑使用本地缓存。

## 迁移现有数据

如果您想将本地数据库中的数据迁移到云数据库：

```python
# 待完成：自动迁移脚本
```

## 常见问题

**Q: 我应该删除本地 reddit_monitor.db 吗？**  
A: 不必须。如果设置了 `SQLITE_CLOUD_URL`，系统会优先使用云数据库。

**Q: 本地和云数据库会同步吗？**  
A: 不会。使用云数据库后，所有的写操作都会保存到云。本地数据库只在不设置 `SQLITE_CLOUD_URL` 时使用。

**Q: 数据安全吗？**  
A: SQLite Cloud 提供企业级的安全性和备份。建议定期查看他们的安全文档。

**Q: 免费层有限制吗？**  
A: 是的，SQLite Cloud 免费层通常有流量和存储限制。查看他们的定价页面了解详情。
