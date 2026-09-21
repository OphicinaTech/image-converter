# PixelFlow — Image Converter

Aplicação web local para conversão recursiva de imagens PNG para WebP ou AVIF, preservando dimensões, metadados suportados e a estrutura original de diretórios.

A interface foi construída com **HTML, CSS e JavaScript nativos**, servida por **FastAPI**. Não há Streamlit, React ou outro framework frontend pesado.

## O que faz

- Seleciona uma pasta local pelo navegador.
- Procura arquivos `.png` em todas as subpastas.
- Ignora a pasta `convertidas` para evitar reconversões.
- Converte para WebP ou AVIF.
- Não redimensiona as imagens.
- Preserva ICC, EXIF e XMP quando suportados pelo encoder.
- Cria automaticamente:

```text
<entrada>/convertidas/YYYY-MM-DD_HH-MM-SS/
```

- Mantém toda a estrutura de subpastas.
- Exibe progresso e erros na interface.
- Processa os arquivos localmente no computador do usuário; o servidor recebe cada imagem apenas durante a conversão e não mantém cópias.

## Exemplo

Entrada:

```text
C:\Users\guilh\Downloads\fotos\
├── produto.png
├── produtos\
│   ├── camisa.png
│   └── tenis.png
└── banners\
    └── home.png
```

Saída:

```text
C:\Users\guilh\Downloads\fotos\convertidas\2026-09-21_09-34-22\
├── produto.webp
├── produtos\
│   ├── camisa.webp
│   └── tenis.webp
└── banners\
    └── home.webp
```

> No Windows, `:` não pode aparecer em nomes de pastas. Por isso o timestamp usa `HH-MM-SS`, e não `HH:MM:SS`.

## Requisitos

- Windows, macOS ou Linux.
- Python 3.13.
- Chrome ou Edge para a seleção e escrita de pastas locais.

## Instalação — Windows

Crie um ambiente virtual limpo:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

Execute os testes:

```powershell
pytest
```

Inicie a aplicação:

```powershell
uvicorn src.image_converter.main:app --reload
```

Abra no navegador:

```text
http://127.0.0.1:8000
```

## Dependências

### Runtime

- **FastAPI** — API HTTP e servidor da aplicação.
- **Uvicorn** — ASGI server.
- **Jinja2** — renderização do HTML.
- **Pillow** — leitura e conversão das imagens.

### Desenvolvimento

- **pytest** — testes automatizados.
- **httpx** — suporte para testes HTTP.

As dependências de teste ficam em `requirements-dev.txt`, evitando instalar ferramentas desnecessárias para quem só quer executar a aplicação.

## Qualidade e formatos

### WebP

A opção WebP usa codificação **lossless**, com `quality=100`, `method=6` e `exact=True`. Essa é a opção indicada quando a prioridade é preservar os pixels sem perda de qualidade.

### AVIF

A opção AVIF usa `quality=100` e `4:4:4`, priorizando alta qualidade. Entretanto, `quality=100` não deve ser interpretado como garantia de equivalência pixel-a-pixel com um PNG original. Para preservação estritamente lossless, utilize WebP Lossless.

## Arquitetura

```text
Browser
   │
   │ File System Access API
   ▼
HTML / CSS / JavaScript
   │
   │ POST /api/convert
   ▼
FastAPI
   │
   ▼
Image Converter Service
   │
   ▼
Pillow
   │
   ▼
WebP / AVIF
   │
   │ Blob retornado ao navegador
   ▼
Pasta local selecionada pelo usuário
```

O backend não recebe um caminho `C:\...` e não acessa arbitrariamente o filesystem do usuário. O navegador concede acesso à pasta explicitamente e grava os resultados nela.

## Estrutura

```text
image-converter/
├── src/
│   └── image_converter/
│       ├── __init__.py
│       ├── converter.py
│       └── main.py
├── static/
│   ├── app.js
│   └── styles.css
├── templates/
│   └── index.html
├── tests/
│   └── test_converter.py
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── .gitignore
```

## Próximas extensões naturais

A arquitetura permite adicionar posteriormente:

- JPG/JPEG, TIFF, BMP e GIF como entrada.
- Escolha de qualidade.
- WebP lossy/lossless.
- Processamento paralelo controlado.
- Relatório de tamanho antes/depois.
- Estimativa de economia de espaço.
- Cancelamento de execução.
- Drag & drop.
- CLI para automação.
- Presets de conversão.
