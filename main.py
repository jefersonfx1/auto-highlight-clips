#!/usr/bin/env python3
"""
Auto Highlight Clips
YouTube → Highlights com IA → Clips verticais com legenda prontos para TikTok/Reels
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

load_dotenv()

# ====================== CONFIG ======================
DEFAULT_CLIPS = 5
DEFAULT_MIN_DURATION = 20
DEFAULT_MAX_DURATION = 55
DEFAULT_LANGUAGE = "pt"
OUTPUT_DIR = Path("output")
TEMP_DIR = Path("temp")

# ====================================================

def run(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    print(f"\n▶ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=False)


def download_video(url: str, output_path: Path) -> Path:
    """Baixa o melhor vídeo disponível com yt-dlp"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "yt-dlp",
        "-f", "bv*[height<=1080]+ba/b[height<=1080]",
        "--merge-output-format", "mp4",
        "-o", str(output_path),
        "--no-playlist",
        url,
    ]
    run(cmd)
    return output_path


def transcribe(video_path: Path, language: str = "pt") -> List[Dict[str, Any]]:
    """Transcreve o vídeo com faster-whisper e retorna segmentos com timestamps"""
    from faster_whisper import WhisperModel

    print("\n🎤 Transcrevendo áudio...")
    model_size = "medium"  # small / medium / large-v3
    device = "cuda" if os.system("nvidia-smi") == 0 else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    segments, info = model.transcribe(
        str(video_path),
        language=language,
        word_timestamps=True,
        vad_filter=True,
    )

    result = []
    for seg in segments:
        result.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })

    print(f"✅ Transcrição concluída ({len(result)} segmentos)")
    return result


def select_highlights(
    segments: List[Dict],
    num_clips: int,
    min_dur: float,
    max_dur: float,
) -> List[Dict]:
    """Usa LLM para escolher os melhores trechos"""
    print("\n🤖 Selecionando highlights com IA...")

    # Junta o texto com timestamps para o LLM
    transcript_text = "\n".join(
        f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in segments
    )

    prompt = f"""Você é um editor especializado em conteúdo viral para TikTok e Instagram Reels.

Abaixo está a transcrição de um vídeo com timestamps.

Sua tarefa: escolher os {num_clips} melhores trechos para clips curtos.

Regras:
- Cada clip deve ter entre {min_dur} e {max_dur} segundos
- Prefira momentos com humor, revelação, frase impactante, emoção ou valor
- Evite trechos que começam ou terminam no meio de uma frase
- Distribua os clips ao longo do vídeo (não pegue só o início)
- Retorne APENAS um JSON válido no formato:

[
  {{
    "start": 12.5,
    "end": 45.0,
    "title": "Título curto e chamativo",
    "reason": "Por que esse trecho é bom"
  }}
]

Transcrição:
{transcript_text[:12000]}
"""

    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "ollama":
        import requests
        model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "format": "json"},
            timeout=180,
        )
        content = resp.json().get("response", "[]")
    elif provider == "groq":
        from openai import OpenAI
        client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )
        resp = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        content = resp.choices[0].message.content
    else:  # openai
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        content = resp.choices[0].message.content

    try:
        data = json.loads(content)
        if isinstance(data, dict) and "clips" in data:
            clips = data["clips"]
        elif isinstance(data, list):
            clips = data
        else:
            clips = list(data.values())[0] if data else []
    except Exception as e:
        print(f"Erro ao parsear resposta do LLM: {e}")
        print(content[:500])
        # Fallback simples: pega trechos espaçados
        clips = []
        step = max(1, len(segments) // (num_clips + 1))
        for i in range(num_clips):
            idx = min((i + 1) * step, len(segments) - 1)
            s = segments[idx]
            clips.append({
                "start": s["start"],
                "end": min(s["start"] + 35, segments[-1]["end"]),
                "title": f"Clip {i+1}",
                "reason": "fallback",
            })

    print(f"✅ {len(clips)} highlights selecionados")
    return clips


def create_vertical_clip(
    video_path: Path,
    start: float,
    end: float,
    output_path: Path,
    title: str = "",
):
    """Cria clip vertical 9:16 com legenda simples queimada"""
    duration = end - start

    # Filtro básico: corta + reframe central + legenda
    # Para face tracking mais avançado pode-se melhorar depois
    vf = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,"
        f"drawtext=text='{title.replace(chr(39), '')}':"
        f"fontsize=48:fontcolor=white:borderw=3:bordercolor=black:"
        f"x=(w-text_w)/2:y=h*0.12:enable='between(t,0,3)'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(video_path),
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ]
    run(cmd)


def main():
    parser = argparse.ArgumentParser(description="Auto Highlight Clips")
    parser.add_argument("--url", required=True, help="Link do YouTube")
    parser.add_argument("--clips", type=int, default=DEFAULT_CLIPS)
    parser.add_argument("--min-duration", type=float, default=DEFAULT_MIN_DURATION)
    parser.add_argument("--max-duration", type=float, default=DEFAULT_MAX_DURATION)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    parser.add_argument("--output", default=str(OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)

    video_file = TEMP_DIR / "source.mp4"

    # 1. Download
    print("\n📥 Baixando vídeo...")
    download_video(args.url, video_file)

    # 2. Transcrição
    segments = transcribe(video_file, args.language)

    # 3. Seleção de highlights
    highlights = select_highlights(
        segments, args.clips, args.min_duration, args.max_duration
    )

    # 4. Geração dos clips
    print("\n🎬 Gerando clips...")
    clips_info = []
    for i, h in enumerate(highlights, 1):
        out_path = output_dir / f"clip_{i:02d}.mp4"
        create_vertical_clip(
            video_file,
            h["start"],
            h["end"],
            out_path,
            title=h.get("title", f"Clip {i}"),
        )
        clips_info.append({
            "file": str(out_path.name),
            "start": h["start"],
            "end": h["end"],
            "title": h.get("title", ""),
            "reason": h.get("reason", ""),
        })
        print(f"  ✅ {out_path.name}")

    # 5. Salva metadados
    info_path = output_dir / "clips_info.json"
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(clips_info, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Pronto! Clips salvos em: {output_dir.resolve()}")
    print(f"📋 Metadados: {info_path}")


if __name__ == "__main__":
    main()
