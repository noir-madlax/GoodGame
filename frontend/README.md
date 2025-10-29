## 导入链接分析 API 契约（草案1）

前端最小集成所需的后端接口定义如下，供后端同学 Review：

### 1) 提交分析任务（去重内置）

- 方法：POST `/api/import/analyze`
- 请求体：

```json
{ "url": "https://www.douyin.com/video/xxxx" }
```

- 返回（之一）：

```json
{ "status": "exists", "analysisId": "123456" }
```

表示该链接先前已分析过，前端应直接跳详情。

- 返回（之二）：

```json
{ "status": "queued", "taskId": "task_abc123" }
```

表示已受理为异步任务。前端会给出 Toast 提示“几分钟后在标记内容与处理页查看”。

- 返回（之三，错误）：

```json
{ "status": "error", "message": "unsupported url" }
```

说明：建议服务端内部完成去重判断（同一 URL 或归一化后等价 URL），若已存在则直接返回 `exists`。

### 2) 任务状态轮询（MVP 可暂不使用）

- 方法：GET `/api/tasks/:taskId`
- 返回：

```json
{ "status": "queued" | "running" | "succeeded" | "failed", "analysisId": "123456", "message": "optional" }
```

前端当前不强依赖该接口；如实现可用于后续增强“完成提示”。

# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/README.md) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default tseslint.config({
  extends: [
    // Remove ...tseslint.configs.recommended and replace with this
    ...tseslint.configs.recommendedTypeChecked,
    // Alternatively, use this for stricter rules
    ...tseslint.configs.strictTypeChecked,
    // Optionally, add this for stylistic rules
    ...tseslint.configs.stylisticTypeChecked,
  ],
  languageOptions: {
    // other options...
    parserOptions: {
      project: ['./tsconfig.node.json', './tsconfig.app.json'],
      tsconfigRootDir: import.meta.dirname,
    },
  },
})
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default tseslint.config({
  plugins: {
    // Add the react-x and react-dom plugins
    'react-x': reactX,
    'react-dom': reactDom,
  },
  rules: {
    // other rules...
    // Enable its recommended typescript rules
    ...reactX.configs['recommended-typescript'].rules,
    ...reactDom.configs.recommended.rules,
  },
})
```
