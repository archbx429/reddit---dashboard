# ☁️ SQLite Cloud 快速配置指南

**总耗时：10 分钟**

---

## 🚀 三步快速开始

### 第一步：SQLite Cloud 账户和数据库（5分钟）

```
1. 访问 https://sqlitecloud.io → Sign Up
2. 创建工作区
3. 创建数据库（名字：reddit-monitor）
4. 复制 Connection String
   格式：sqlitecloud://user:password@host.sqlitecloud.io:8860/reddit_monitor
```

📌 **保存好连接字符串，接下来会用到！**

详细步骤→ [STEP1_SETUP.md](STEP1_SETUP.md)

---

### 第二步：本地配置和数据迁移（2分钟）

```bash
# 1. 编辑 .env 文件，添加连接字符串：
echo 'SQLITE_CLOUD_URL=sqlitecloud://user:password@host.sqlitecloud.io:8860/reddit_monitor' >> .env

# 2. 安装依赖
pip install sqlitecloud

# 3. 运行迁移脚本（将本地数据导入云）
python3 migrate_to_cloud.py

# 4. 验证
python3 diagnose.py
```

✅ **看到 "✅ 迁移完成" 就成功了！**

详细步骤→ [STEP2_SETUP.md](STEP2_SETUP.md)

---

### 第三步：Streamlit Cloud 配置（3分钟）

```
1. 访问 https://share.streamlit.io
2. 找到应用 "reddit-dashboard-pocolab"
3. 点击右上角 "..." → "Settings"
4. 选择左侧 "Secrets"
5. 添加环境变量：
   SQLITE_CLOUD_URL = "sqlitecloud://user:password@host.sqlitecloud.io:8860/reddit_monitor"
6. 点击 "Save"
7. 等待应用自动重新部署（1-2分钟）
```

✅ **应用重新部署后，访问网址查看数据！**

详细步骤→ [STEP3_SETUP.md](STEP3_SETUP.md)

---

## ✨ 完成后的效果

| 操作 | 结果 |
|------|------|
| 本地点击"爬取" | 数据保存到 SQLite Cloud ⛅ |
| Streamlit Cloud 更新 | 自动显示最新数据 ✅ |
| 不需要手动提交 | GitHub 提交已过时 🚀 |
| 数据实时同步 | 本地和云应用同步 🔄 |

---

## 🔧 故障排除

### 问题：迁移失败
```
解决：
1. 检查 .env 文件是否保存：cat .env | grep SQLITE
2. 重新导出变量：export SQLITE_CLOUD_URL="..."
3. 重新运行：python3 migrate_to_cloud.py
```

### 问题：Streamlit Cloud 仍显示旧数据
```
解决：
1. 确认 Secrets 已保存
2. 等待应用重新部署（查看部署状态）
3. 强制刷新浏览器：Ctrl+Shift+R (Windows) 或 Cmd+Shift+R (Mac)
```

### 问题：本地无法连接云数据库
```
解决：
1. 验证连接字符串格式：echo $SQLITE_CLOUD_URL
2. 检查密码中是否有特殊字符需要 URL 编码
3. 运行诊断：python3 diagnose.py
```

---

## 📋 检查清单

- [ ] SQLite Cloud 账户已创建
- [ ] 数据库已创建
- [ ] 连接字符串已复制
- [ ] .env 文件已更新
- [ ] sqlitecloud 已安装（`pip list | grep sqlitecloud`）
- [ ] 数据迁移脚本成功运行
- [ ] Streamlit Cloud Secrets 已配置
- [ ] 应用已重新部署
- [ ] 本地和云应用都能看到数据

---

## 📚 详细文档

- [STEP1_SETUP.md](STEP1_SETUP.md) - SQLite Cloud 账户和数据库创建
- [STEP2_SETUP.md](STEP2_SETUP.md) - 本地配置和数据迁移
- [STEP3_SETUP.md](STEP3_SETUP.md) - Streamlit Cloud 配置
- [SETUP_CLOUD_DB.md](SETUP_CLOUD_DB.md) - 完整的技术参考

---

## 🆘 需要帮助？

如果遇到问题，请运行诊断脚本：

```bash
python3 diagnose.py
```

这会显示：
- ✅ 数据库连接状态
- ✅ 可用的日期和数据
- ✅ 配置是否正确

然后告诉我诊断输出，我会帮您解决！

---

## 💡 提示

1. **连接字符串很重要** - 妥善保管，不要提交到 Git
2. **Secrets 是安全的** - Streamlit Cloud 会加密存储
3. **第一次配置后就自动了** - 之后只需点击"爬取"按钮

祝配置顺利！🎉
