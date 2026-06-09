# Hellsgame Knight — Prototype v2

Jogo de ação 2D com batalhas contra bosses, desenvolvido em Python com Pygame.

---

## Requisitos

- **Python 3.11 ou superior**
- **Pygame 2.5+**

---

## Instalação

### 1. Clone ou extraia o projeto

Coloque a pasta `hellsgame_knight/` em qualquer lugar do seu computador.

### 2. (Recomendado) Crie um ambiente virtual

```bash
python -m venv venv
```

Ative o ambiente:

- **Windows:**
  ```bash
  venv\Scripts\activate
  ```
- **Linux / macOS:**
  ```bash
  source venv/bin/activate
  ```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

---

## Como executar

Dentro da pasta `hellsgame_knight/`, rode:

```bash
python main.py
```

---

## Estrutura do projeto

```
hellsgame_knight/
│
├── main.py               ← Ponto de entrada — execute este arquivo
├── settings.py           ← Constantes globais e caminhos de assets
├── game.py               ← Orquestrador do loop principal
│
├── player.py             ← Lógica e animações do jogador (Knight)
├── boss.py               ← Boss Minotauro
├── night_boss.py         ← Boss Umbrazoth (arena noturna)
├── enemy.py              ← Inimigos genéricos
│
├── minotaur_arena.py     ← Arena do Minotauro
├── night_arena.py        ← Arena Noturna (Night Town)
│
├── menu.py               ← Menus de pausa, game over e vitória
├── main_menu.py          ← Menu principal e seleção de batalha
├── particles.py          ← Sistema de partículas
├── platforms.py          ← Plataformas de colisão
├── rock_hazard.py        ← Pedras lançadas pelo Minotauro
├── sprite_utils.py       ← Utilitários para carregamento de spritesheets
├── pooling.py            ← Pool de objetos para performance
│
├── requirements.txt      ← Dependências Python
│
└── assets/               ← Todos os sprites, backgrounds e sons
    ├── knight/           ← Spritesheet do jogador
    ├── boss/             ← Sprites do Minotauro
    ├── noite_boss/       ← Sprites do Umbrazoth
    └── arena_noite/      ← Assets da arena noturna
```

---

## Controles

| Tecla         | Ação                  |
|---------------|-----------------------|
| `←` `→`       | Mover                 |
| `SPACE` / `↑` | Pular                 |
| `Z`           | Atacar                |
| `X`           | Dash                  |
| `P`           | Pausar                |
| `ESC`         | Sair / Voltar ao menu |

---

## Batalhas disponíveis

| Arena           | Boss           | Como acessar                    |
|-----------------|----------------|---------------------------------|
| Floresta Demoníaca | Minotauro   | Menu principal → Jogar          |
| Night Town      | Umbrazoth      | Menu principal → Selecionar Batalha |

---

## Ferramentas de desenvolvimento (opcional)

Estes scripts são apenas para desenvolvimento e **não são necessários** para jogar:

- `debug_sprites.py` — Diagnóstico de carregamento de sprites
- `setup_sprites.py` — Medição automática de spritesheets
- `import_monsters.py` — Utilitário de importação de sprites de inimigos

---

## Versão do Python testada

```
Python 3.11 / 3.13 / 3.14
Pygame 2.5+
```

---

## Problemas comuns

**O jogo não abre:**
- Verifique se o Python está instalado: `python --version`
- Verifique se o Pygame foi instalado: `pip install pygame`

**Sprites aparecem como retângulos coloridos:**
- Confirme que a pasta `assets/` está presente dentro de `hellsgame_knight/`
- Não mova os arquivos da pasta `assets/` para fora de `hellsgame_knight/`

**Erro de módulo não encontrado:**
- Execute `python main.py` **de dentro da pasta** `hellsgame_knight/`
- Não execute de fora com `python hellsgame_knight/main.py`
