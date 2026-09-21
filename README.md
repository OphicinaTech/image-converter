# PixelFlow — Image Converter

Aplicação web local para conversão recursiva de imagens PNG, WebP e AVIF para WebP ou AVIF, preservando metadados suportados e a estrutura original de diretórios.

A interface foi construída com **HTML, CSS e JavaScript nativos**, servida por **FastAPI**. Não há Streamlit, React ou outro framework frontend pesado.

## O que faz

- Seleciona uma pasta local pelo navegador.
- Procura arquivos `.png`, `.webp` e `.avif` em todas as subpastas.
- Ignora a pasta `convertidas` para evitar reconversões.
- Converte até 5 imagens em paralelo.
- Oferece presets **Original** (lossless), **Compacto** (lossy) e **Mobile** (redimensiona o lado maior para 1600px).
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

Reconverter WebP lossless em WebP/AVIF lossless **não** leva o arquivo de MB para KB. A compressão sem perda já extraiu a redundância; o tamanho restante é o conteúdo da imagem.

Para chegar em KB, use **Compacto** ou **Mobile**. Mobile reduz resolução e aplica lossy — é o único caminho realista para fotos de dezenas de megabytes.

### Original (lossless)

WebP lossless (`quality=100`, `method=4`, `exact=True`). AVIF em `quality=100` e `4:4:4`. AVIF em qualidade 100 não é garantia pixel-a-pixel; para isso use WebP + Original.

`method=4` é bem mais rápido que `method=6`, com arquivos lossless um pouco maiores.

### Compacto

Lossy de alta qualidade, **sem** redimensionar. Bom para web quando a resolução original precisa ser mantida.

### Mobile

O lado maior é limitado a **1600px** (LANCZOS) e a imagem é reencodada em lossy. Este preset é o indicado para uso em celular e para sair da faixa de MB.

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
- Qualidade e lado máximo configuráveis.
- Relatório de tamanho antes/depois.
- Cancelamento de execução.
- Drag & drop.
- CLI para automação.
