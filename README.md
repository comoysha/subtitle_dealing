# subtitle_dealing

## 流程 1: B 站 AI 字幕 JSON 下载方法
把 B 站 AI 字幕 JSON（`body[].content`）提取为纯文本 `.txt`。
- 先不开启字幕
- 打开浏览器开发者模式
- 打开字幕
- 查看新增的请求的返回结果,复制成 json 文件

### 目录约定

- 输入目录：`bilibili_subtitle_json_downloaded/`（放 `.json`）
- 输出目录：`json_subtitle_to_txt/`（生成同名 `.txt`）

### 使用方法

在项目根目录运行：

```bash
# 处理 subtitle_json/ 下所有 .json
python3 extract_bilibili_ai_subtitles.py

# 指定某一个文件（可以只写文件名，会从 subtitle_json/ 里找）
python3 extract_bilibili_ai_subtitles.py '大鹏-罗永浩的十字路口.json'

# 也可以传入完整/相对路径
python3 extract_bilibili_ai_subtitles.py subtitle_json/'大鹏-罗永浩的十字路口.json'

# 自定义输入/输出目录
python3 extract_bilibili_ai_subtitles.py --in-dir subtitle_json --out-dir output_txt
```

输出示例：`output_txt/大鹏-罗永浩的十字路口.txt`

### 可以运行脚本
run_extract_bilibili_ai_subtitles.sh

## 流程 2: 给视频配字幕并烧录

### 1. 将视频转为 MP3 音频

脚本 `video_to_mp3_batch.sh` 会把 `input_video/` 下的文件批量转为 `output_audio/` 下的 mp3，并把处理过的视频移动到 `input_video/已处理/`。

```bash
chmod +x video_to_mp3_batch.sh
./video_to_mp3_batch.sh
```

### 2. 音频转写为 SRT（OpenRouter）

脚本 `transcribe_audio_to_srt_openrouter.py` 调用 OpenRouter 的模型，把音频转写并翻译为中文 SRT 字幕。

在项目根目录创建 `.env` 并配置：

```bash
OPENROUTER_API_KEY=你的key
```

常用示例：

```bash
# 批量处理 output_audio/ 下的音频
python3 transcribe_audio_to_srt_openrouter.py --input-dir output_audio --output-dir ai_srt --insecure

# 只处理单个音频文件
python3 transcribe_audio_to_srt_openrouter.py --input-file "output_audio/a.mp3" --insecure 

# 覆盖已有 srt
python3 transcribe_audio_to_srt_openrouter.py --input-dir output_audio --output-dir ai_srt --force --insecure
```

### 3. 烧录硬字幕到视频

脚本 `burn_in_subtitles.py` 使用 `ffmpeg` 将 `.srt` 字幕烧录到视频中，生成带硬字幕的新视频文件（默认输出为原视频同目录下的 `*_hardsub.<原扩展名>`）。

```bash
python3 burn_in_subtitles.py --video "input_video/已处理/a.mp4" --srt "ai_srt/a.srt"  --out "burn_video/a_hardsub.mp4"

# 覆盖已存在的输出文件
python3 burn_in_subtitles.py --video "a.mp4" --srt "a.srt" --force
```


### $. 一键自动流程(多个视频并行)

把视频放在 /Users/xiayue/subtitle_dealing/input_video 里, 脚本 `auto_video_srt_pipeline.py` 会自动完成：视频提取 mp3 → OpenRouter 转写生成 SRT → 硬字幕烧录输出到 `burn_video/`。

```bash
python3 auto_video_srt_pipeline.py

# 覆盖已有 SRT / 输出视频
python3 auto_video_srt_pipeline.py --force

# 输出 srt 文件就停止,不向后继续生成烧录视频
python3 auto_video_srt_pipeline.py --stop-after-srt

# 指定并行任务数(不指定默认=4)
python3 auto_video_srt_pipeline.py --jobs 3
```

### 可以运行脚本
video_to_mp3_batch.sh

## 流程 3: srt 转 txt

convert_srt_to_txt.py
run_convert_srt_to_txt.sh

输入:download_srt
输出:download_srt/converted_txt

## 流程 4: 下载 youtube 的 srt
download_youtube_srt.py
run_download_youtube_srt.py
如果视频也要就加 --with-video

先在youtube_url.csv里一行放一个视频链接,保存的 srt 会放在download_srt