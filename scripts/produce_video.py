"""MAIS DD Workbench demo 動画 全自動制作 pipeline (action-then-narration timing model)。

4 段 orchestrator:
  1. AivisSpeech HTTP API (Style-Bert-VITS2、 まお おちついた speaker_id=888753763) で 16 scene raw narration WAV 生成
  2. Playwright (Chromium、 1920x1080) で uvicorn live demo flow を navigate + WebM 録画 + 各 scene action_elapsed 計測
  3. action_elapsed + settle buffer を lead-in silence にして per-scene padded WAV build (narration が settled page 上で 流れる timing 保証)
  4. ffmpeg で WebM + narration WAV → MP4 最終合成 (SRT 字幕 burn-in + 末尾 credit overlay + tpad で video 末尾 frame clone)

precondition (起動済 / install 済 verify):
  - uvicorn http://127.0.0.1:8001/health = 200
  - AivisSpeech engine http://127.0.0.1:10101/version = 200
    起動: `.vendor/aivis-engine/Windows-x64/run.exe --host 127.0.0.1 --port 10101`
  - ffmpeg (PATH 上、 `winget install Gyan.FFmpeg`)
  - playwright + chromium (`pip install -r requirements-video.txt && playwright install chromium`)

run:
  PYTHONIOENCODING=utf-8 python -m scripts.produce_video
  → out_video/mais_dd_workbench_demo.mp4 (約 110 秒、 1080p、 約 7 MB)

env var (override 可):
  SPEAKER_ID=<int>     default 888753763 (まお おちついた)
  PITCH_SCALE=<float>  default 0.0、 ±0.03 が natural 域 (Style-Bert-VITS2 model 制限)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests

# ─── config ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "out_video"
TEMP_DIR = OUTPUT_DIR / "_temp"
UVICORN_URL = "http://127.0.0.1:8001"
ENGINE_URL = "http://127.0.0.1:10101"  # AivisSpeech-Engine standalone
SPEAKER_ID = int(os.environ.get("SPEAKER_ID", "888753763"))  # まお おちついた (cross-PJ 統一)

LEAD_IN_SEC = 0.4   # legacy (--narration-only mode の fallback)
TRAIL_OUT_SEC = 0.4  # narration 終了から次 scene までの最低 silence
SETTLE_BUFFER_SEC = 0.3  # action 完了 (networkidle) 後 narration 開始 までの buffer

# pitchScale: AivisSpeech (Style-Bert-VITS2) は ±0.03 が natural 域、 超過で音割れ artifact
# default 0.0 (まお おちついた の素 AI prosody を保持)
PITCH_SCALE = float(os.environ.get("PITCH_SCALE", "0.0"))

VIEWPORT = {"width": 1920, "height": 1080}


# ─── scene definitions (id, duration_sec, action, narration_text) ────
# scene_duration は narration_duration + 0.8s 以上の literal margin で接続部 重なり防止

@dataclass
class Scene:
    id: str
    duration: float
    action: Callable
    narration: str


def _scenes_factory() -> list[Scene]:
    """Playwright page を受け取り navigation を行う lambda 群を構築 (T2 DD 自動化 demo)。

    pre-condition (script invocation 前):
      - uvicorn (port 8000) 起動済
      - AivisSpeech (port 10101) 起動済
      - 対象 DDP (DDP-Fn-mP3hsIKw 映像制作 multi-pattern) の ingestion + jp_patterns 検出 完了済
        (UI ingest button 経由でも事前 pre-warm でも可、 動画では既 ingested state literal 閲覧)
    """
    # 動画 demo target: DDP-Fn-mP3hsIKw (映像制作 / family_governance + nominee_shareholder)
    DEMO_DDP = "DDP-Fn-mP3hsIKw"

    def s1(p):
        p.goto(f"{UVICORN_URL}/")
        p.wait_for_load_state("networkidle")

    def s2(p):
        # 統計 4 stat (-50% / 週→日 / 300+ / 7-layer) を表示する section へ scroll
        p.evaluate("window.scrollTo({top: 600, behavior: 'smooth'})")

    def s3(p):
        # 本番 scale table section へ scroll (PoC vs 本番の 4 軸比較)
        p.evaluate("window.scrollTo({top: 1100, behavior: 'smooth'})")

    def s4(p):
        # mock-signin form 入力 + ログイン
        p.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        p.wait_for_timeout(500)
        p.locator("input[name='user_id']").fill("takada")
        p.locator("button:has-text('担当者ログイン')").click()
        p.wait_for_url("**/dd-projects")
        p.wait_for_load_state("networkidle")

    def s5(p):
        # dd-projects 一覧 hold
        p.wait_for_load_state("networkidle")

    def s6(p):
        # 映像制作 案件 (multi-pattern) を click
        p.locator(f"a[href='/dd-project/{DEMO_DDP}']").click()
        p.wait_for_url(f"**/dd-project/{DEMO_DDP}")
        p.wait_for_load_state("networkidle")

    def s7(p):
        # ingestion 実行 (pre-warmed なら既 ingested、 未なら button click)
        # 動画では already-ingested state を期待、 button があれば click
        if p.locator("button:has-text('ingestion 実行')").count() > 0:
            p.locator("button:has-text('ingestion 実行')").click()
            p.wait_for_load_state("networkidle")
        else:
            p.wait_for_load_state("networkidle")

    def s8(p):
        # chunks + jp_hits 統計 card を hold
        p.evaluate("window.scrollTo({top: 200, behavior: 'smooth'})")

    def s9(p):
        # jp-patterns link click
        p.locator(f"a[href='/dd-project/{DEMO_DDP}/jp-patterns']").first.click()
        p.wait_for_url(f"**/dd-project/{DEMO_DDP}/jp-patterns")
        p.wait_for_load_state("networkidle")

    def s10(p):
        # 質問票 link
        p.goto(f"{UVICORN_URL}/dd-project/{DEMO_DDP}/questionnaire?category=legal")
        p.wait_for_load_state("networkidle")

    def s11(p):
        # 1 質問の AI 回答生成 button click (legal 系の Change of Control 質問が含まれる)
        # 1 番目 の literal 「AI 回答生成」 button をクリック
        # AI pipeline 処理は MockProvider でも 5-stage + Vault encrypt 等で 30-60s かかる、 timeout 延長
        p.locator("button:has-text('AI 回答生成')").first.click(timeout=90000)
        p.wait_for_url(f"**/dd-project/{DEMO_DDP}/questionnaire**", timeout=90000)
        p.wait_for_load_state("networkidle", timeout=60000)

    def s12(p):
        # ✓ mark 確認 (回答済 表示)
        p.evaluate("window.scrollTo({top: 200, behavior: 'smooth'})")

    def s13(p):
        # 監査ログ
        p.locator("nav a:has-text('監査ログ')").click()
        p.wait_for_url("**/audit-log")
        p.wait_for_load_state("networkidle")

    def s14(p):
        # audit hold + table scroll
        p.evaluate("window.scrollTo({top: 100, behavior: 'smooth'})")

    def s15(p):
        # signout → landing 本番 scale section
        p.locator("nav form button:has-text('ログアウト')").click()
        p.wait_for_url(f"{UVICORN_URL}/")
        p.wait_for_load_state("networkidle")
        p.evaluate("window.scrollTo({top: 1100, behavior: 'smooth'})")

    def s16(p):
        # landing top scroll、 closing
        p.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")

    return [
        # narration text 2 回目 audit (2026-05-13): 単語間空白除去 + 過剰読点削減
        # (世間事例: RE-NO 氏 「読点入れすぎは不自然」 + ナトリウム氏 「自分で読み上げ verify」 と整合)
        # duration は auto-sync logic が actual WAV + margin に literal 上書きするため初期値は低め可
        Scene("S1", 6.0, s1, "マイス。中堅企業デューデリジェンス自動化のエーアイです。"),
        Scene("S2", 8.0, s2, "デューデリジェンス工数を50パーセント削減。数週間を数日に短縮します。"),
        Scene("S3", 8.5, s3, "本番運用では、同じAIが500件以上の書類も処理します。"),
        Scene("S4", 5.0, s4, "担当者としてログインします。"),
        Scene("S5", 5.5, s5, "合成案件5件が表示されます。"),
        Scene("S6", 5.5, s6, "映像制作業界の案件を選びます。"),
        Scene("S7", 8.0, s7, "データルームの書類8件をAIが細かく分解します。"),
        Scene("S8", 10.0, s8, "71個の文章ブロックを抽出して、要注意サインを自動検出します。"),
        Scene("S9", 7.0, s9, "同族経営と名義株の兆候が検出されました。"),
        Scene("S10", 7.5, s10, "次に、300項目の法務質問リストを表示します。"),
        Scene("S11", 7.0, s11, "経営権移動条項についてAIが自動回答します。"),
        Scene("S12", 9.0, s12, "元の書類のどこに書いてあるかまで表示。該当度ラベル付きです。"),
        Scene("S13", 8.0, s13, "全ての操作履歴が改ざん不能なログに記録されます。"),
        Scene("S14", 7.0, s14, "中身が見えないAIではなく、監査可能な仕組みです。"),
        Scene("S15", 8.5, s15, "PoCで機能完成。設備だけ拡張で本番へ移行できます。"),
        Scene("S16", 5.0, s16, "全機能動作確認済です。"),
    ]


SCENES = _scenes_factory()


# ─── helpers ──────────────────────────────────────────────────────────

def info(msg: str) -> None:
    print(f"[produce_video] {msg}", flush=True)


def check_preconditions() -> None:
    """uvicorn / AivisSpeech / ffmpeg / playwright + chromium の起動確認。"""
    errors = []

    try:
        r = requests.get(f"{UVICORN_URL}/health", timeout=3)
        assert r.status_code == 200
        info(f"OK uvicorn live ({UVICORN_URL}/health = 200)")
    except Exception as e:
        errors.append(f"uvicorn 起動不能: {UVICORN_URL} ({e}). 別 shell で uvicorn を起動してください")

    try:
        r = requests.get(f"{ENGINE_URL}/version", timeout=3)
        assert r.status_code == 200
        info(f"OK AivisSpeech engine live ({ENGINE_URL}/version = {r.text.strip()})")
    except Exception as e:
        hint = ".vendor/aivis-engine/Windows-x64/run.exe --host 127.0.0.1 --port 10101 で起動してください"
        errors.append(f"AivisSpeech engine 起動不能: {ENGINE_URL} ({e}). {hint}")

    if shutil.which("ffmpeg") is None:
        errors.append("ffmpeg が PATH に不在。 `winget install Gyan.FFmpeg` で install してください")
    else:
        info(f"OK ffmpeg ({shutil.which('ffmpeg')})")

    try:
        from playwright.sync_api import sync_playwright  # noqa
        info("OK playwright (Python binding)")
    except ImportError:
        errors.append("playwright 未 install。 `pip install -r requirements-video.txt` を実行してください")

    if errors:
        info("==== precondition error ====")
        for e in errors:
            info(f"  - {e}")
        sys.exit(1)


def aivis_synthesize(text: str) -> bytes:
    """AivisSpeech HTTP API で WAV bytes 生成 (Style-Bert-VITS2、 素 AI prosody)。"""
    q = requests.post(
        f"{ENGINE_URL}/audio_query",
        params={"text": text, "speaker": SPEAKER_ID},
        timeout=15,
    )
    q.raise_for_status()
    q_json = q.json()
    if PITCH_SCALE != 0.0:
        q_json["pitchScale"] = PITCH_SCALE
    s = requests.post(
        f"{ENGINE_URL}/synthesis",
        params={"speaker": SPEAKER_ID},
        json=q_json,
        timeout=60,
    )
    s.raise_for_status()
    return s.content


def ffprobe_duration(path: Path) -> float:
    """ffprobe で WAV/WebM の長さ秒を取得。"""
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    )
    return float(out.decode().strip())


def make_padded_wav(scene: Scene, raw_wav_path: Path, out_path: Path, lead_in_sec: float | None = None) -> None:
    """raw WAV を scene.duration に合わせて lead-in + trail-out silence で sandwich pad。"""
    lead = LEAD_IN_SEC if lead_in_sec is None else lead_in_sec
    raw_dur = ffprobe_duration(raw_wav_path)
    if raw_dur > scene.duration - lead - TRAIL_OUT_SEC:
        info(f"  WARN [{scene.id}] narration {raw_dur:.2f}s が scene {scene.duration:.1f}s (lead={lead:.2f}s) に対し tight、 trail_out 縮小")

    # adelay で先頭 silence、 apad で末尾 silence を scene.duration まで延長
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(raw_wav_path),
            "-af", f"adelay={int(lead * 1000)}|{int(lead * 1000)},apad=whole_dur={scene.duration}",
            "-ar", "24000", "-ac", "1",
            str(out_path),
        ],
        check=True,
    )


def concat_narration(scene_padded_wavs: list[Path], out_path: Path) -> None:
    """全 scene padded WAV を concat demuxer で 1 本に結合。"""
    concat_list = TEMP_DIR / "concat_audio.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in scene_padded_wavs),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(out_path),
        ],
        check=True,
    )


def record_demo() -> Path:
    """Playwright で demo flow を録画、 WebM path 返却。"""
    from playwright.sync_api import sync_playwright

    info("Playwright Chromium 起動中... (action-then-narration timing mode)")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--hide-scrollbars"],
        )
        context = browser.new_context(
            viewport=VIEWPORT,
            record_video_dir=str(TEMP_DIR),
            record_video_size=VIEWPORT,
        )
        page = context.new_page()

        for scene in SCENES:
            raw_dur = getattr(scene, "raw_duration", 0.0)
            info(f"  [{scene.id}] action: {scene.narration[:30]}... (narration_raw={raw_dur:.2f}s)")
            t0 = time.time()
            scene.action(page)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            scene.action_elapsed = time.time() - t0
            narration_window_sec = raw_dur + SETTLE_BUFFER_SEC + TRAIL_OUT_SEC
            info(f"    action_elapsed={scene.action_elapsed:.2f}s, narration_window={narration_window_sec:.2f}s")
            page.wait_for_timeout(int(narration_window_sec * 1000))

        context.close()
        browser.close()

    webms = sorted(TEMP_DIR.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    if not webms:
        raise RuntimeError(f"WebM が {TEMP_DIR} に生成されなかった")
    return webms[-1]


def _fmt_srt_time(t: float) -> str:
    """SRT timestamp 形式 (HH:MM:SS,mmm)。"""
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def generate_srt(out_path: Path) -> None:
    """narration を SRT に literal 出力。 action_elapsed set 済なら action-aware lead 使用。"""
    lines: list[str] = []
    cum = 0.0
    for i, scene in enumerate(SCENES, 1):
        action_elapsed = getattr(scene, "action_elapsed", None)
        lead = (action_elapsed + SETTLE_BUFFER_SEC) if action_elapsed is not None else LEAD_IN_SEC
        start = cum + lead
        end = cum + scene.duration - TRAIL_OUT_SEC
        cum += scene.duration
        lines.append(f"{i}\n{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}\n{scene.narration}\n")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def compose_final(webm: Path, narration: Path, out_mp4: Path) -> None:
    """WebM + narration WAV → MP4 (1080p / H.264 / AAC) + 字幕 burn-in + 末尾クレジット overlay。

    drawtext escape 戦略:
      - クレジット text は textfile 経由で読込 (shell escape 回避、 日本語 + 記号安全)
      - fontfile は forward-slash path + 単 backslash で colon escape (`C\:/Windows/...`)
      - enable は narration 長 - 7s で末尾 7 秒間 overlay (動的計算で video 長変動に literal 追従)
    字幕 burn-in:
      - SRT を generate_srt() で出力 → ffmpeg subtitles filter で literal 焼き込み
      - 配置 = MarginV 120 (末尾クレジット overlay より上、 重なり防止)
    """
    # 1) クレジット text を textfile 経由で読み込ませる (UTF-8、 BOM なし)
    credit_path = TEMP_DIR / "credit.txt"
    credit_path.write_text(
        "MAIS DD Workbench (PoC) / AivisSpeech: まお おちついた / 合成データ only",
        encoding="utf-8",
    )

    # 2) SRT 字幕生成 (cumulative 時刻 + lead/trail silence 反映)
    srt_path = TEMP_DIR / "narration.srt"
    generate_srt(srt_path)

    # 3) fontfile path を ffmpeg filter 構文に safe な形式へ
    #    Windows 標準 Yu Gothic Medium (常駐、 install 不要)、 forward-slash + `C\:/...`
    fontfile_escaped = "C\\:/Windows/Fonts/YuGothM.ttc"
    textfile_escaped = credit_path.as_posix().replace(":", "\\:")
    srt_escaped = srt_path.as_posix().replace(":", "\\:")

    # 4) 末尾 7 秒間 overlay (narration 長 - 7 から終端まで、 narration が canonical 長)
    narration_dur = ffprobe_duration(narration)
    video_dur = ffprobe_duration(webm)
    enable_from = max(0.0, narration_dur - 7.0)
    pad_sec = max(0.0, narration_dur - video_dur + 0.2)
    tpad_filter = f"tpad=stop_mode=clone:stop_duration={pad_sec:.2f}" if pad_sec > 0.01 else None

    # 5) 字幕 (subtitles filter で SRT を burn-in、 Yu Gothic UI Bold、 最下部配置)
    #    ASS default PlayResY=288、 1080p frame への scale factor = 1080/288 = 3.75x
    #    MarginV=30 → 30 × 3.75 = 112px from bottom = literal 最下部寄り
    #    (PlayResY override は force_style で honored 不安定、 default 維持で MarginV のみで制御が確実)
    subtitles_filter = (
        f"subtitles='{srt_escaped}':"
        "force_style='FontName=Yu Gothic UI Semibold,"
        "Fontsize=22,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,"
        "BackColour=&H80000000&,BorderStyle=1,Outline=2,Shadow=1,"
        "MarginV=30,Alignment=2'"
    )

    drawtext_filter = (
        f"drawtext=fontfile='{fontfile_escaped}':"
        f"textfile='{textfile_escaped}':"
        "fontcolor=white:fontsize=26:"
        "x=(w-text_w)/2:y=h-th-40:"
        "box=1:boxcolor=black@0.75:boxborderw=14:"
        f"enable='gte(t,{enable_from:.2f})'"
    )

    # chain: tpad (video extend if shorter) → subtitles 先 → drawtext (credit 上 layer)
    vf_parts = [f for f in (tpad_filter, subtitles_filter, drawtext_filter) if f]
    vf_chain = ",".join(vf_parts)
    if tpad_filter:
        info(f"  tpad: video {video_dur:.2f}s → narration {narration_dur:.2f}s (clone {pad_sec:.2f}s 末尾 frame)")

    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(webm),
            "-i", str(narration),
            "-vf", vf_chain,
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-metadata", f"comment=AivisSpeech:speaker_id={SPEAKER_ID} / MAIS DD Workbench PoC / synthetic data only",
            str(out_mp4),
        ],
        check=True,
    )


# ─── main orchestrator ───────────────────────────────────────────────

def main() -> int:
    narration_only = "--narration-only" in sys.argv
    info("=== MAIS DD Workbench demo video pipeline (action-then-narration model) ===")
    if narration_only:
        info("(--narration-only mode: AivisSpeech synthesis のみ実行、 Playwright + ffmpeg compose skip)")
    OUTPUT_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)

    info("\n[0/3] precondition check")
    if narration_only:
        # TTS engine だけ verify (uvicorn / Playwright skip、 ffmpeg は concat に必要)
        try:
            r = requests.get(f"{ENGINE_URL}/version", timeout=3)
            assert r.status_code == 200
            info(f"OK AivisSpeech engine live ({ENGINE_URL}/version = {r.text.strip()})")
        except Exception as e:
            info(f"AivisSpeech engine 起動不能: {ENGINE_URL} ({e})")
            sys.exit(1)
        if shutil.which("ffmpeg") is None:
            info("ffmpeg が PATH に不在")
            sys.exit(1)
        info(f"OK ffmpeg ({shutil.which('ffmpeg')})")
    else:
        check_preconditions()

    info(f"\n[1/4] AivisSpeech で {len(SCENES)} scene の raw narration WAV 生成 (padding は phase 3 で)")
    for scene in SCENES:
        raw = TEMP_DIR / f"{scene.id}_raw.wav"
        wav_bytes = aivis_synthesize(scene.narration)
        raw.write_bytes(wav_bytes)
        scene.raw_duration = ffprobe_duration(raw)
        info(f"  [{scene.id}] raw_duration={scene.raw_duration:.2f}s ({scene.narration[:25]}...)")

    if narration_only:
        info("\n[narration-only fallback] padded WAV を legacy fixed lead で build")
        padded_wavs: list[Path] = []
        for scene in SCENES:
            raw = TEMP_DIR / f"{scene.id}_raw.wav"
            padded = TEMP_DIR / f"{scene.id}_padded.wav"
            scene.duration = round(scene.raw_duration + LEAD_IN_SEC + TRAIL_OUT_SEC + 0.3, 1)
            make_padded_wav(scene, raw, padded)
            padded_wavs.append(padded)
        narration_wav = TEMP_DIR / "narration_full.wav"
        concat_narration(padded_wavs, narration_wav)
        listen_path = OUTPUT_DIR / "narration_only_preview.wav"
        shutil.copy(narration_wav, listen_path)
        return 0

    info(f"\n[2/4] Playwright で demo flow 録画 (action-then-narration model、 scene.action_elapsed 計測)")
    webm = record_demo()
    video_dur = ffprobe_duration(webm)
    info(f"  WebM: {webm.name} = {video_dur:.2f}s")
    info(f"  action_elapsed per scene (settled state 到達 wall-clock):")
    for scene in SCENES:
        info(f"    [{scene.id}] action_elapsed={scene.action_elapsed:.2f}s")

    info(f"\n[3/4] padded WAV build (lead_in = action_elapsed + {SETTLE_BUFFER_SEC}s settle buffer)")
    padded_wavs: list[Path] = []
    for scene in SCENES:
        raw = TEMP_DIR / f"{scene.id}_raw.wav"
        padded = TEMP_DIR / f"{scene.id}_padded.wav"
        lead = scene.action_elapsed + SETTLE_BUFFER_SEC
        scene.duration = round(lead + scene.raw_duration + TRAIL_OUT_SEC, 2)
        make_padded_wav(scene, raw, padded, lead_in_sec=lead)
        padded_wavs.append(padded)
        info(f"  [{scene.id}] lead={lead:.2f}s + raw={scene.raw_duration:.2f}s + trail={TRAIL_OUT_SEC}s = scene.duration={scene.duration}s")

    narration_wav = TEMP_DIR / "narration_full.wav"
    concat_narration(padded_wavs, narration_wav)
    total_audio = ffprobe_duration(narration_wav)
    info(f"  narration 結合完了: {narration_wav.name} = {total_audio:.2f}s (video {video_dur:.2f}s と 同期想定)")

    info("\n[4/4] ffmpeg で MP4 最終合成 + 末尾クレジット overlay + SRT burn-in")
    out_mp4 = OUTPUT_DIR / "mais_dd_workbench_demo.mp4"
    compose_final(webm, narration_wav, out_mp4)
    final_dur = ffprobe_duration(out_mp4)
    size_mb = out_mp4.stat().st_size / 1024 / 1024
    info(f"  完成: {out_mp4} = {final_dur:.2f}s / {size_mb:.1f} MB")

    info("\n=== Done ===")
    info(f"動画 = {out_mp4.relative_to(BASE_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
