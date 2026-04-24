# 第三步：配置 Streamlit Cloud

这一步让 Streamlit Cloud 上的应用能够连接到 SQLite Cloud，约需 3 分钟。

---

## 3.1 访问 Streamlit Cloud 仪表板

1. 打开 **https://share.streamlit.io**
2. 使用您的 GitHub 账户登录（如果还没登录）
3. 您应该看到已部署的应用列表

---

## 3.2 找到您的应用

在应用列表中找到 **"reddit-dashboard-pocolab"**（或您的应用名称）

点击应用名称进入应用详情页面。

---

## 3.3 打开应用设置

在应用详情页面右上角，点击 **"..."**（三个点）菜单

从下拉菜单选择 **"Settings"**

---

## 3.4 进入 Secrets 管理

在左侧菜单找到 **"Secrets"** 选项

点击打开 Secrets 页面

---

## 3.5 添加环境变量

在 Secrets 编辑框中，添加您的配置。编辑框应该看起来像这样：

```toml
# 现有的设置（可能已有）
GEMINI_API_KEY = "your_existing_key_here"

# 添加新的行：
SQLITE_CLOUD_URL = "sqlitecloud://user:password@host.sqlitecloud.io:8860/reddit_monitor"
```

### 具体步骤：

1. 在现有内容的后面添加新行
2. 输入：`SQLITE_CLOUD_URL = "`
3. 粘贴您从第一步复制的连接字符串
4. 添加末尾的 `"`

结果应该看起来像：

```toml
GEMINI_API_KEY = "AIzaSyD..."
SQLITE_CLOUD_URL = "sqlitecloud://user:pass@host.sqlitecloud.io:8860/reddit_monitor"
```

⚠️ **注意：**
- 确保连接字符串用双引号包围
- 不要添加 `export` 或 `echo` 命令
- 只是纯文本配置

---

## 3.6 保存设置

1. 检查内容是否正确
2. 点击 **"Save"** 按钮
3. 页面会提示"Secrets saved"

---

## 3.7 等待应用重新部署

保存后，Streamlit Cloud 会自动：

1. 获取最新的代码
2. 重新启动应用
3. 应用使用新的环境变量

这通常需要 **30 秒 - 2 分钟**。

您可以在页面上看到部署状态（通常显示"Running" 或一个进度条）。

---

## 3.8 验证配置成功

部署完成后，打开您的应用：

**https://reddit-dashboard-pocolab.streamlit.app/**

### 检查项：

1. ✅ 应用是否正常加载？
2. ✅ 能否看到 4.24 的 186 条数据？
3. ✅ 点击"开始爬取"是否能添加新数据？

---

## 常见问题

### Q: 应用显示错误或加载失败

**A:** 检查：
1. Secrets 是否正确保存
2. 连接字符串是否正确复制
3. 等待应用完全重新部署（可能需要 1-2 分钟）
4. 刷新浏览器

### Q: 我看不到任何数据

**A:** 可能原因：
1. 迁移脚本没有成功运行（回到第二步）
2. Streamlit Cloud 的部署还未完成
3. 连接字符串不正确

**解决步骤：**
```bash
# 本地验证是否连接正常
python3 diagnose.py
```

### Q: 在 Streamlit 中修改 Secrets 后需要重新部署吗？

**A:** 不需要，Streamlit 会自动重新部署。刷新页面即可看到新配置的效果。

### Q: 连接字符串中的密码包含特殊字符怎么办？

**A:** 如果密码中有 `@` 或 `:` 等特殊字符，需要 URL 编码：
- `@` → `%40`
- `:` → `%3A`
- `/` → `%2F`

或者在 SQLite Cloud 中重置密码为更简单的字符。

### Q: 本地应用和 Streamlit Cloud 使用同一个数据库吗？

**A:** 是的！两者都连接到同一个 SQLite Cloud 数据库，数据会实时同步。

---

## 测试完整流程

1. **本地爬取数据**
   ```bash
   python3 -m streamlit run app.py
   ```
   点击"开始爬取"，添加新数据

2. **检查 Streamlit Cloud**
   打开 https://reddit-dashboard-pocolab.streamlit.app/
   刷新页面，应该看到新数据

3. ✅ 如果两边数据同步，说明配置成功！

---

## 完成后

✅ Streamlit Cloud 已连接到 SQLite Cloud  
✅ 本地和云应用使用同一个数据库  
✅ 数据会实时同步  

**现在您已完成所有配置！** 

接下来：
- 在本地爬取数据时，Streamlit Cloud 会自动更新
- 不再需要手动提交 GitHub
- 真正的实时数据同步

