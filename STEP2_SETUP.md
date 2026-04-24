# 第二步：本地配置和迁移

完成这一步后，您的本地数据会同步到 SQLite Cloud。

## 2.1 获取 SQLite Cloud 连接字符串

1. 在 SQLite Cloud 控制台，选择您创建的数据库
2. 点击 **"Connection"** 或 **"Credentials"** 标签页
3. 找到 **Connection String** 或 **Database URL**
4. 复制整个字符串（格式如下）：

```
sqlitecloud://user:password@host.sqlitecloud.io/database_name
```

⚠️ **重要**：保存好这个字符串，接下来会用到。

---

## 2.2 配置本地环境变量

### 方式 A：编辑 .env 文件（推荐）

在项目目录打开终端，运行以下命令：

```bash
# 用您的实际连接字符串替换下面的内容
echo 'SQLITE_CLOUD_URL=sqlitecloud://user:password@host.sqlitecloud.io/database_name' >> .env
```

**或者手动编辑：**

1. 打开项目根目录的 `.env` 文件
2. 添加一行：

```env
SQLITE_CLOUD_URL=sqlitecloud://user:password@host.sqlitecloud.io/database_name
```

3. 保存文件

### 方式 B：直接在终端设置（临时）

```bash
export SQLITE_CLOUD_URL='sqlitecloud://user:password@host.sqlitecloud.io/database_name'
```

⚠️ 注意：这样设置仅在当前终端会话有效，关闭终端后会失效。

---

## 2.3 安装 SQLite Cloud Python 客户端

在终端运行：

```bash
pip install sqlitecloud
```

验证安装：

```bash
python3 -c "import sqlitecloud; print('✅ sqlitecloud installed successfully')"
```

---

## 2.4 运行迁移脚本

这一步会把本地数据库中的所有数据导入到 SQLite Cloud：

```bash
python3 migrate_to_cloud.py
```

您会看到类似的输出：

```
============================================================
📊 MIGRATE TO SQLITE CLOUD
============================================================

[1] 连接本地数据库...
✅ 连接成功

[2] 连接 SQLite Cloud...
✅ 连接成功

[3] 在云数据库创建表...
✅ 表创建完成

[4] 迁移 posts 表...
✅ 迁移了 186 条帖子

[5] 迁移 analysis 表...
✅ 迁移了 32 条分析

[6] 迁移 subreddits 表...
✅ 迁移了 7 个频道

[7] 验证迁移...
✅ 云数据库现有：
   - 186 条帖子
   - 32 条分析

============================================================
✅ 迁移完成！
============================================================
```

### 如果迁移失败

**错误 1：SQLITE_CLOUD_URL not set**
```
解决：检查 .env 文件是否正确保存，或者确保环境变量已导出
export SQLITE_CLOUD_URL='sqlitecloud://...'
```

**错误 2：连接失败**
```
解决：检查连接字符串是否正确（特别是密码中的特殊字符）
```

**错误 3：sqlitecloud not installed**
```
解决：运行 pip install sqlitecloud
```

---

## 2.5 验证迁移成功

运行诊断脚本验证：

```bash
python3 diagnose.py
```

您应该看到：

```
✅ 已有频道：
   - bambulab
   - EufyMakeOfficial
   - snapmaker
   - 3Dprinting
   - prusa3d
   - ender3
   - functionalprint

✅ 数据统计（按日期）:
   2026-04-24: 186 条帖子，32 条已分析
   2026-04-23: 234 条帖子，234 条已分析
   ...
```

---

## 2.6 测试本地连接

启动本地应用，点击"开始爬取"：

```bash
python3 -m streamlit run app.py
```

在浏览器打开 `http://localhost:8501`

1. 点击右上角 **"开始爬取"** 按钮
2. 等待爬取和分析完成
3. 检查新增的数据

**查看实时数据库日志：**

可以在 SQLite Cloud 控制台查看实时的数据写入日志，验证数据是否真的上传了。

---

## 完成后

✅ 本地数据已迁移到 SQLite Cloud  
✅ 本地应用可以正常爬取和保存数据到云  
✅ 已为下一步（配置 Streamlit Cloud）做好准备

**继续第三步：** 在 Streamlit Cloud 中配置 Secrets

