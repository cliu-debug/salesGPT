# 贡献指南

感谢您有兴趣为 AI销售助手 做出贡献！

## 📋 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发指南](#开发指南)
- [提交规范](#提交规范)
- [代码风格](#代码风格)

## 行为准则

本项目采用贡献者公约作为行为准则。参与此项目即表示您同意遵守其条款。

## 如何贡献

### 报告Bug

如果您发现了bug，请通过 [GitHub Issues](https://github.com/your-repo/opc/issues) 提交，包含：

1. **Bug描述** - 清晰简洁地描述bug
2. **复现步骤** - 详细的复现步骤
3. **期望行为** - 您期望发生什么
4. **实际行为** - 实际发生了什么
5. **截图** - 如果适用，添加截图
6. **环境** - 操作系统、Python版本等

### 建议新功能

我们欢迎新功能建议！请通过 Issues 提交：

1. **功能描述** - 清晰描述您希望的功能
2. **使用场景** - 为什么需要这个功能
3. **实现思路** - 如果有实现想法，请分享

### 提交代码

1. **Fork仓库**
   ```bash
   git clone https://github.com/your-username/opc.git
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **编写代码**
   - 遵循代码风格指南
   - 添加必要的测试
   - 更新相关文档

4. **提交更改**
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```

5. **推送分支**
   ```bash
   git push origin feature/amazing-feature
   ```

6. **创建Pull Request**
   - 在GitHub上创建PR
   - 填写PR模板
   - 等待代码审查

## 开发指南

### 环境搭建

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖

# 前端
cd frontend
npm install
```

### 运行测试

```bash
# 后端测试
cd backend
pytest tests/ -v --cov=app

# 前端测试
cd frontend
npm run test
```

### 代码检查

```bash
# Python代码检查
flake8 app/
black app/
isort app/

# TypeScript代码检查
cd frontend
npm run lint
```

## 提交规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

### 提交格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type类型

| 类型 | 说明 |
|------|------|
| feat | 新功能 |
| fix | Bug修复 |
| docs | 文档更新 |
| style | 代码格式（不影响功能） |
| refactor | 重构 |
| perf | 性能优化 |
| test | 测试相关 |
| chore | 构建/工具相关 |
| ci | CI/CD相关 |

### 示例

```
feat(customer): 添加客户批量导入功能

- 支持Excel文件上传
- 自动解析客户数据
- 批量创建客户记录

Closes #123
```

## 代码风格

### Python

- 遵循 [PEP 8](https://pep8.org/) 规范
- 使用 [Black](https://github.com/psf/black) 格式化
- 使用 [isort](https://github.com/PyCQA/isort) 排序导入
- 类型注解优先

```python
# 好的示例
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db)
) -> Customer:
    """获取客户信息"""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    return result.scalar_one_or_none()
```

### TypeScript/Vue

- 遵循 [Vue风格指南](https://vuejs.org/style-guide/)
- 使用 ESLint + Prettier

```typescript
// 好的示例
interface Customer {
  id: number
  name: string
  email: string
}

export const useCustomerStore = defineStore('customer', {
  state: () => ({
    customers: [] as Customer[]
  }),
  actions: {
    async fetchCustomers() {
      const response = await api.getCustomers()
      this.customers = response.data
    }
  }
})
```

## 分支策略

```
main        # 主分支，稳定版本
├── develop # 开发分支
│   ├── feature/xxx  # 功能分支
│   ├── bugfix/xxx   # Bug修复分支
│   └── refactor/xxx # 重构分支
```

## 版本发布

我们使用 [语义化版本](https://semver.org/lang/zh-CN/)：

- `MAJOR.MINOR.PATCH`
- 例如：`1.0.0`

## 问题？

如果您有任何问题，请：

1. 查看 [FAQ](docs/FAQ.md)
2. 搜索 [Issues](https://github.com/your-repo/opc/issues)
3. 创建新的 Issue

---

再次感谢您的贡献！🎉
