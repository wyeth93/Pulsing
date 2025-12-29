# Documentation

This directory contains the documentation for Pulsing, built with MkDocs and Material theme.

## Setup

### Using uv (Recommended)

Install documentation dependencies using uv:

```bash
cd docs
uv sync
```

### Using pip

Install documentation dependencies:

```bash
pip install -r docs/requirements.txt
```

Or install from pyproject.toml:

```bash
pip install -e docs
```

## Building Documentation

**Important**: All commands should be run from the `docs/` directory.

### Development Server

Start the development server with live reload:

```bash
cd docs
make serve
# or
uv run mkdocs serve
```

The documentation will be available at `http://127.0.0.1:8000`

### Build Static Site

Build the documentation as a static site:

```bash
cd docs
make build
# or
uv run mkdocs build
```

The output will be in the `site/` directory.

### Check Links

Check for broken links in the documentation:

```bash
cd docs
make check-links
```

### Clean Build Artifacts

Remove build artifacts:

```bash
cd docs
make clean
```

### Deploy

Deploy to GitHub Pages (from `docs/` directory):

```bash
cd docs
mkdocs gh-deploy
```

## Documentation Structure

The documentation source files are located in the `src/` directory:

- `src/index.md` / `src/index.zh.md` - Home page (English/Chinese)
- `src/quick_start.md` / `src/quick_start.zh.md` - Quick start guide
- `src/architecture.md` / `src/architecture.zh.md` - Architecture overview
- `src/api_reference.md` / `src/api_reference.zh.md` - API reference
- `src/guides/` - User guides
- `src/design/` - Design documents

Navigation is manually configured in `mkdocs.yml` using the `nav` section. The `i18n` plugin automatically handles language-specific navigation for both English and Chinese versions.

## Internationalization

The documentation supports both English and Chinese using the `mkdocs-static-i18n` plugin, which provides:

- **Automatic Language Detection**: Detects user's browser language preference
- **Manual Language Switching**: Language switcher in the navigation
- **Chinese Search Support**: Uses `jieba` for Chinese word segmentation
- **Material Theme Localization**: Chinese interface for Material theme
- **URL-based Language Routing**: `/en/` for English, `/zh/` for Chinese

### Language File Naming

Documents use the `.zh.md` suffix for Chinese versions:
- `index.md` - English version
- `index.zh.md` - Chinese version

Both versions are automatically detected and served at their respective language paths.

## Features

- **Material Theme**: Modern, responsive design
- **Manual Navigation**: Navigation is manually configured in `mkdocs.yml`
- **Internationalization**: Full support for English and Chinese with `mkdocs-static-i18n`
- **Code Highlighting**: Syntax highlighting with Pygments
- **API Documentation**: Automatic API docs with mkdocstrings
- **Link Checking**: Built-in link validation
- **Search**: Full-text search functionality with Chinese support (jieba)
