# DeepSeek API Test

**版本号：0.2.0**  
**作者：Gwaanl**

DeepSeek API Test 是一个用于对多个语言模型接口进行自动化测试和性能评估的项目。项目通过 Flask 构建 Web 前端，并利用 APScheduler 定时触发测试任务。测试结果会保存到 SQLite 数据库中，同时支持将测试结果导出为图片，便于留档或报告展示。
![test_results_20250212_225605](https://github.com/user-attachments/assets/416f1ce8-f9d8-4033-9117-c94dc229b32d)
在网页界面上点击这几个按钮能够进行列的显示和隐藏
![Uploading image.png…]()

**DeepSeek Api Test 由 Gwaanl 构建，源代码遵循 MIT 协议**

---

## 目录

- [项目特点](#项目特点)
- [项目结构](#项目结构)
- [安装依赖](#安装依赖)
- [配置说明](#配置说明)
- [运行项目](#运行项目)
- [API 接口说明](#api-接口说明)
- [使用说明](#使用说明)
- [导出结果](#导出结果)
- [常见问题](#常见问题)
- [License](#license)

---

## 项目特点

- **多轮自动测试**：支持对指定的多个语言模型接口依次进行三轮测试。
- **实时进度展示**：在 Web 页面上实时显示测试进度、已完成和未完成的模型列表。
- **历史记录管理**：测试结果会保存在 SQLite 数据库中，可通过历史记录页面查看以往测试记录及详情。
- **结果导出**：测试结束后自动将三轮测试结果及汇总表格合并为一张图片，方便存档或报告使用。
- **定时任务**：内置 APScheduler 定时任务支持定期自动执行测试任务。
- **自定义提示词**：支持通过接口实时更新模型测试时使用的提示词。

---

## 项目结构

为了便于后续管理和修改，本项目将原有代码拆分为多个模块，推荐的目录结构如下：

```
DeepSeek/
├─ app.py                # 项目入口，Flask 应用及路由定义
├─ config.py             # Flask 和 APScheduler 的配置
├─ db_utils.py           # 数据库初始化及测试记录的读写操作
├─ test_runner.py        # 测试核心逻辑，包括单轮/多轮测试、后台线程及调度任务
├─ utils.py              # 辅助工具函数，如日志配置、HTML 表格生成、图片导出等
├─ models_config.py      # 模型相关配置（接口地址、API Key、展示名称等）
└─ requirements.txt      # 第三方库依赖列表
```

每个模块的主要作用说明如下：

- **app.py**：  
  - 初始化 Flask 应用及 APScheduler。
  - 定义前端页面与 API 接口（启动测试、更新提示词、查看进度、历史记录等）。
  - 启动后自动打开浏览器访问首页。

- **config.py**：  
  - 定义 Flask 和 APScheduler 的基本配置，如 `SCHEDULER_API_ENABLED`。

- **db_utils.py**：  
  - 提供数据库初始化、保存测试记录、读取最新或历史测试记录的函数。

- **test_runner.py**：  
  - 实现模型测试的核心逻辑，包括对单个模型的请求、超时处理、结果统计等。
  - 支持单轮和多轮测试，计算 tokens/s 等指标，并生成 HTML 表格。
  - 内置后台线程函数 `background_test_runner` 及调度任务 `scheduled_job`。

- **utils.py**：  
  - 配置统一的日志系统。
  - 提供 HTML 表格生成、数据离群值检测、图片导出等工具函数。

- **models_config.py**：  
  - 存放各个模型的配置参数（接口 URL、API Key、显示名称等）。
  - 定义待测试的模型列表 `MODELS_TO_TEST`。

- **requirements.txt**：  
  - 列出项目所需的第三方 Python 包及其版本（如 Flask、flask-apscheduler、pandas、requests、imgkit 等）。

---

## 安装依赖

1. **克隆或下载项目代码**

2. **安装 Python 依赖**  
   使用 pip 安装所需依赖（建议使用虚拟环境）：
   ```bash
   pip install -r requirements.txt
   ```
   
3. **安装 wkhtmltopdf 工具**  
   项目中使用 [imgkit](https://github.com/jarrekk/imgkit) 将 HTML 导出为图片，需要安装 [wkhtmltopdf](https://wkhtmltopdf.org/)：
   - Windows 用户请下载安装包，并将安装目录添加到系统 PATH 中。
   - macOS 用户可使用 Homebrew 安装：
     ```bash
     brew install wkhtmltopdf
     ```
   - Linux 用户请根据发行版使用对应包管理器安装。

---

## 配置说明

1. **修改模型配置**  
   在 `models_config.py` 文件中，根据实际情况配置你的模型接口信息：
   - `MODELS_CONFIG` 中每个模型包含：
     - `display_name`：模型展示名称。
     - `url`：模型接口地址。
     - `api_key`：接口调用的 API Key。
     - 可选字段 `payload_model`：若请求 payload 中需要使用与配置 key 不一致的模型名称，可指定该字段。
   - `MODELS_TO_TEST` 数组中列出待测试模型的 key。

2. **其他配置**  
   - 若需要调整 APScheduler 调度策略，可在 `config.py` 或 `test_runner.py` 中进行修改。
   - 默认提示词存放在 `test_runner.py` 中变量 `custom_prompt`，可通过 API 更新。

---

## 运行项目

在项目根目录下执行以下命令启动 Flask 应用：

```bash
python app.py
```

启动后程序会自动打开默认浏览器，访问地址为 [http://127.0.0.1:5000](http://127.0.0.1:5000)。

---

## API 接口说明

项目提供以下主要接口，支持前端交互及调试：

- **`GET /`**  
  首页，显示最新一次测试结果。若无测试记录，则显示提示信息，并支持手动启动测试。

- **`GET /start_test?timeout=300`**  
  手动启动一次测试任务。可通过 `timeout` 参数设置超时时间（单位：秒）。  
  **返回**：测试启动状态提示字符串。

- **`GET /update_prompt?prompt=新的提示词`**  
  更新模型测试时使用的提示词。  
  **返回**：提示词更新状态信息。

- **`GET /test_progress`**  
  获取当前测试任务的进度信息，包括当前轮次、已完成和未完成模型列表等。  
  **返回**：JSON 格式进度信息。

- **`GET /history`**  
  显示所有测试历史记录的列表，包含记录 ID、测试开始与结束时间，并提供详情链接。

- **`GET /result/<int:record_id>`**  
  查看指定测试记录的详细结果，包括每轮测试数据和最终汇总表格。

---

## 使用说明

1. **手动发起测试**  
   - 在首页填写“超时时间（秒）”和“自定义提示词”，点击“立即执行一轮测试”按钮，后台会依次对配置中待测试的模型进行三轮测试。
   - 测试过程中，页面下方的进度条会实时显示当前进度、当前轮次以及已完成/未完成模型列表。

2. **更新提示词**  
   - 在首页输入框中修改提示词后点击“更新提示词”按钮，即可通过 `/update_prompt` 接口更新全局提示词。

3. **查看测试进度**  
   - 页面会自动每隔 2 秒轮询 `/test_progress` 接口，并更新页面显示当前测试进度。

4. **查看历史记录和详情**  
   - 点击首页底部“查看历史记录”链接，进入历史记录页面，可查看以往测试记录。
   - 点击具体记录的“查看详情”链接，查看某一次测试的各轮数据和最终汇总表格。

---

## 导出结果

- 每次完整测试结束后，后台会自动调用 `export_tables_to_image` 函数，将三轮测试结果和汇总表格合并为一张长图，保存在 `output` 文件夹中。
- 导出的图片默认隐藏了响应中的原始 JSON、Content 和 Reasoning 信息，方便展示核心指标。

---

## 常见问题

1. **API 请求失败或超时**  
   - 检查模型配置中的 `url` 和 `api_key` 是否正确。
   - 调整请求 `timeout` 参数，确保网络延迟在合理范围内。

2. **图片导出失败**  
   - 请确保已经正确安装 `wkhtmltopdf`，并且工具在系统 PATH 中可访问。
   - 可尝试使用命令行直接调用 `wkhtmltopdf` 检查是否正常工作。

3. **测试任务长时间无响应**  
   - 检查服务器资源情况，必要时可增加测试任务的超时时间或优化网络请求策略。
   - 查看 `test.log` 日志文件，获取详细错误信息以便排查问题。

---

## License

本项目源代码遵循 **MIT License** 协议。

---

## 联系方式

如有任何疑问或建议，请联系作者：**Gwaanl**
