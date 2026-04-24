# 第一步：创建 SQLite Cloud 账户和数据库

这一步创建云数据库，约需 5 分钟。

---

## 1.1 注册 SQLite Cloud 账户

1. 打开浏览器访问：**https://sqlitecloud.io**
2. 点击右上角 **"Sign Up"** 或 **"Get Started Free"**
3. 选择注册方式（邮箱 / Google / GitHub）
4. 输入邮箱和密码，点击 **"Create Account"**
5. 验证邮箱（点击收到的邮件中的链接）
6. 登录账户

---

## 1.2 创建工作区

登录后，您会看到欢迎页面：

1. 点击 **"Create your workspace"**
2. 选择 **"SQLite Cloud"**（第一个选项 - 推荐）
3. 点击 **"Next"**
4. 输入工作区名称，例如：`reddit-dashboard`
5. 点击 **"Create"**

---

## 1.3 创建数据库

在工作区首页：

1. 点击 **"Create Database"** 或 **"New Database"** 按钮
2. 输入数据库名称：`reddit-monitor` （或自定义名字）
3. 选择地理位置（建议选择离您最近的）：
   - 🗽 US East (美国东部) - 如果您在美国
   - 🌍 EU Central (欧洲中部) - 如果您在欧洲
   - 🌏 Asia Pacific (亚太) - 如果您在亚洲
4. 点击 **"Create Database"**

等待几秒钟，数据库会被创建。

---

## 1.4 获取连接字符串

数据库创建完成后：

1. 点击进入新创建的数据库
2. 在左侧菜单找到 **"Connection"** 或 **"Credentials"** 标签页
3. 您会看到不同的连接方式：
   - **Connection String**（最常用）
   - **Database URL**
   - **CLI Connection**

4. 复制 **Connection String**，格式应该是：

```
sqlitecloud://user:password@host.sqlitecloud.io:8860/database_name
```

或

```
sqlitecloud://token@host.sqlitecloud.io:8860/database_name
```

⚠️ **重要**：
- 🔒 不要分享这个连接字符串
- 💾 保存到安全的地方
- ✏️ 接下来的步骤会用到

---

## 1.5 （可选）测试连接

如果您想在浏览器中测试数据库是否正常：

1. 点击 **"SQL Editor"** 或 **"Query"** 标签页
2. 运行一个简单的查询：

```sql
SELECT 1 as test;
```

如果看到 `1`，说明数据库正常工作。

---

## 常见问题

**Q: 免费层的限制是什么？**  
A: SQLite Cloud 免费层通常包括：
- 1 个数据库
- 有限的存储空间（通常 1GB 足够）
- 有限的 API 调用次数
- 查看具体限制：https://sqlitecloud.io/pricing

**Q: 我的连接字符串是什么格式？**  
A: 应该类似这样：
```
sqlitecloud://user:password@host.sqlitecloud.io:8860/reddit_monitor
```

**Q: 密码中有特殊字符怎么办？**  
A: URL 编码特殊字符：
- `@` → `%40`
- `:` → `%3A`
- 其他字符查看：https://www.urlencoder.org/

**Q: 我遗忘了连接字符串怎么办？**  
A: 回到 SQLite Cloud 控制台，点击数据库的 "Connection" 标签页重新复制。

---

## 完成后

✅ SQLite Cloud 账户已创建  
✅ 数据库已创建  
✅ 连接字符串已复制

**接下来：** 进行第二步 - 本地配置和迁移

