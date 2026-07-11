# 更新日志

## 2026-07-11

### 新增功能

#### 1. 无简历模式：AI 自动生成简历 + 技术栈分析 + 学习路线
- 新增"我没有简历"勾选框，勾选后显示 AI 生成简历功能
- 根据 JD 自动生成匹配的简历（包含基本信息、个人优势、技能清单、工作经历、项目经验、教育背景）
- 自动分析岗位所需技术栈，标注掌握程度（精通/熟练/了解）
- 自动规划学习路线，包含具体学习主题、推荐资源、预计时间
- 面试小贴士和匹配度分析
- 新增后端接口 /api/generate-resume（新增 GEN_RESUME_PROMPT 和 generate_resume_and_tech() 函数）

#### 2. 选填个人信息
- 生成简历时可选填：姓名、目标岗位、已有技能、工作经验、教育背景、补充说明
- 填写了的部分基于真实信息，未填写的由 AI 自动生成最优内容
- 全部留空则 AI 全自动生成

#### 3. 简历下载（PDF）
- 生成的简历支持一键下载为 PDF 文件
- 使用 pdf2 库生成，自动调用系统中文字体
- 简历限制在一页 A4 纸以内
- 新增后端接口 /api/download-resume

#### 4. JD 输入统一为文字+图片混合模式
- 移除原来的"文字输入 / 截图上传"模式切换
- 统一为一个输入框，支持同时输入文字和粘贴图片
- 图片通过 Ctrl+V 粘贴，显示为缩略图，可删除
- 文字和图片 OCR 结果自动合并为完整 JD 内容
- 新增 uild_jd_content() 函数统一处理

### 问题修复

#### 1. 修复 Tesseract OCR 未安装导致截图识别失败
- **问题**：系统未安装 Tesseract OCR，截图上传后返回 400 错误
- **解决**：改用 EasyOCR 纯 Python 库进行 OCR 识别，无需额外安装系统依赖
- **影响文件**：ackend/main.py、equirements.txt、Dockerfile

#### 2. 修复 DeepSeek API 不支持图片输入
- **问题**：尝试用 DeepSeek 视觉能力识别图片，返回 unknown variant 'image_url' 错误
- **解决**：回退到 EasyOCR 方案，稳定可靠

#### 3. 修复 levelClass 函数空值保护
- **问题**：技术栈标签渲染时 	.level 可能为 undefined，导致 includes 调用报错
- **解决**：添加 (level || "").toLowerCase() 空值保护

### 技术改进

- OCR 方案：从 pytesseract（需系统安装）→ DeepSeek 视觉（不兼容）→ **EasyOCR**（纯 Python，最终方案）
- PDF 生成：从 python-docx（Word 格式）→ **pdf2**（PDF 格式，一页限制）
- 字体：PDF 使用系统自带 SimSun（宋体）中文字体
- 移除 Dockerfile 中的 Tesseract 安装步骤，简化部署
