# Amanda — Assistente Virtual com Personalidade

Uma assistente virtual com personalidade única, carismática e envolvente. Protótipo de conversação por texto com IA.

## Sobre

Amanda é uma companheira digital projetada para acompanhar o usuário no dia a dia — com personalidade, calor humano e imersão total. Ela conversa de forma natural, acolhe, brinca, e faz a pessoa se sentir especial.

## Stack

- **Frontend:** React
- **IA/LLM:** Claude (Anthropic API)
- **Futuro:** Speech-to-Text (Whisper), Text-to-Speech (ElevenLabs), Avatar 2D animado (Rive), App Mobile (Flutter)

## Roadmap

- [x] Protótipo de conversação por texto
- [x] Personalidade e sistema de prompt
- [ ] Integração com voz (STT + TTS)
- [ ] Avatar 2D animado com lip-sync
- [ ] Memória persistente entre sessões
- [ ] App mobile (Android/iOS)
- [ ] Wake word ("Oi, Amanda")

## Como rodar localmente

```bash
# 1. Instala as dependências
npm install

# 2. Copia o .env de exemplo e preenche com sua API key
cp .env.example .env

# 3. Cria o arquivo src/prompt.js com a personalidade da Amanda
# (esse arquivo não vai pro GitHub por segurança)

# 4. Roda o projeto
npm run dev
```

## Estrutura

```
amanda-project/
├── .env.example      ← template das variáveis (vai pro GitHub)
├── .env              ← suas chaves reais (NÃO vai pro GitHub)
├── .gitignore
├── index.html
├── package.json
├── vite.config.js
├── README.md
└── src/
    ├── main.jsx      ← entry point
    ├── App.jsx       ← interface + lógica
    └── prompt.js     ← personalidade da Amanda (NÃO vai pro GitHub)
```

## Licença

Projeto privado — todos os direitos reservados.
