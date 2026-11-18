# Como contribuir

Obrigado pelo interesse. Este projeto é pequeno e mantém regras simples.

## Antes de abrir um pull request

1. Abra uma issue descrevendo o problema ou a proposta.
2. Rode os testes: `python -m unittest discover -s tests -v`.
3. Mantenha o estilo do código existente: módulos em `src/`, texto em português nos comentários, nomes de API em inglês.
4. Toda mudança de comportamento precisa de teste em `tests/`.
5. Se adicionar uma chave de tradução, inclua-a nos seis arquivos de `locales/` — o teste `test_all_locales_have_the_same_keys` falha caso contrário.

## Escopo do projeto

Aceitos: correções de bugs, melhorias de robustez no backup, novos destinos de armazenamento, novos idiomas e melhorias de acessibilidade da interface.

Fora do escopo: instaladores com serviços em segundo plano, telemetria e qualquer recurso que envie dados sem ação explícita do usuário.

## Commits

Mensagens curtas no imperativo, em português ou inglês, por exemplo:

```text
corrige rotação quando o destino está em unidade de rede
add WebDAV test connection
```

## Segurança

Não abra issue pública para vulnerabilidades. Descreva o caso em particular ao mantenedor pelo site [olacdev.com](https://olacdev.com/).
