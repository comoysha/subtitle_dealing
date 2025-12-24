# subtitle_dealing

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

输入: input_video
输出: burn_video

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
run_auto_video_srt_pipeline.sh
