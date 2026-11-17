# Auto Highlight Clips

Sistema automático para transformar vídeos longos do YouTube em clips verticais prontos para TikTok e Instagram Reels.

## O que ele faz

1. Baixa o vídeo do YouTube (`yt-dlp`)
2. Transcreve com timestamps (`faster-whisper`)
3. Detecta os melhores highlights com IA (LLM)
4. Corta em formato 9:16
5. Adiciona legendas queimadas no vídeo
6. Exporta clips prontos para postar

Você só precisa baixar os arquivos finais e agendar no painel das redes sociais.

## Requisitos

- Python 3.10+
- FFmpeg instalado no sistema
- (Opcional) GPU NVIDIA para Whisper mais rápido

## Instalação rápida

```bash
git clone https://github.com/jefersonfx1/auto-highlight-clips.git
cd auto-highlight-clips
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Como usar

### Processar um vídeo

```bash
python main.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --clips 5
```

### Opções principais

- `--url` : Link do YouTube (obrigatório)
- `--clips` : Quantidade de clips desejados (padrão: 5)
- `--min-duration` : Duração mínima do clip em segundos (padrão: 20)
- `--max-duration` : Duração máxima do clip em segundos (padrão: 55)
- `--language` : Idioma da transcrição (padrão: pt)
- `--output` : Pasta de saída (padrão: ./output)

### Exemplo completo

```bash
python main.py \
  --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --clips 6 \
  --min-duration 25 \
  --max-duration 50 \
  --language pt \
  --output ./meus_clips
```

## Saída

Na pasta `output/` você encontrará:

- `clip_01.mp4`, `clip_02.mp4`... → vídeos prontos (9:16 + legenda)
- `clips_info.json` → informações de cada clip (timestamps, título sugerido, score)

## Rodando 24h / Servidor

Recomendado: **Oracle Cloud Always Free** (melhor free tier atual).

Também funciona bem em:
- Seu próprio PC
- VPS barato
- Docker

### Docker (opcional)

```bash
docker build -t auto-clips .
docker run -v $(pwd)/output:/app/output auto-clips --url "SEU_LINK"
```

## Configuração do LLM

Por padrão o sistema tenta usar **Ollama** local (gratuito e privado).

Se não tiver Ollama, você pode usar Groq (free tier generoso) ou OpenAI.

Configure no arquivo `.env`:

```env
LLM_PROVIDER=ollama          # ollama | groq | openai
OLLAMA_MODEL=llama3.1:8b
GROQ_API_KEY=sua_chave
OPENAI_API_KEY=sua_chave
```

## Próximos passos sugeridos

- Monitorar canal automaticamente
- Notificação no Telegram quando os clips estiverem prontos
- Templates de legenda personalizados
- Face tracking mais avançado

---

Feito para ser simples, barato e funcional.
