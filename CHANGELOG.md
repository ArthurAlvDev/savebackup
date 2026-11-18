# Changelog

Todas as mudanças relevantes deste projeto são registradas aqui.
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não publicado]

## [2.2.1] - 2026-11-18

### Segurança
- FTPS passa a usar contexto TLS padrão, com validação de certificado e hostname.
- WebDAV exige `https://` para hosts fora da rede local; `http://` continua aceito em `localhost` e faixas privadas.
- Download do rclone confere o SHA-256 do arquivo contra a lista oficial publicada em `downloads.rclone.org` e não instala nada se a verificação falhar.
- Nomes de remoto e pasta do rclone são validados e não podem ser interpretados como opções de linha de comando.
- Workflow do GitHub Actions com permissão de escrita apenas no job de build e actions fixadas por commit SHA.
- `requirements.txt` fixa a versão do PyInstaller usada no build.

### Adicionado
- Seis testes de validação de segurança (URL WebDAV e argumentos do rclone).

## [2.2.0] - 2026-11-18

### Adicionado
- Rodapé com crédito **Made by OlacDev**, link para `https://olacdev.com/`, versão e licença.
- Instância única: uma segunda execução restaura e traz a janela existente para frente, em vez de abrir outra cópia com agendamentos concorrentes.
- Limpeza automática de arquivos `.zip.part` órfãos, deixados por backups interrompidos.
- Opção `--version` na linha de comando.
- Metadados de versão, empresa e descrição embutidos no executável.
- Suíte de testes automatizados (`tests/`) e pipeline de build no GitHub Actions.
- Licença MIT, guia de contribuição e este changelog.

### Alterado
- Título da janela agora exibe a versão: `Save Backup 2.2.0`.
- Script de build passa a usar `SaveBackup.spec`, rodando os testes antes de compilar.

## [2.1.0] - 2026-11-15

### Adicionado
- Arquitetura modular em camadas (`config`, `core`, `i18n`, `platform`, `storage`, `ui`).
- Internacionalização com 6 idiomas e fallback resiliente.
- Provedores de destino: Rclone, pasta de nuvem local, FTP/FTPS, WebDAV e rede SMB.
- Compactação atômica com proteção contra auto-inclusão de destinos.

## [2.0.0] - 2026-10-14

### Adicionado
- Primeira versão reescrita: backup local multi-destino, bandeja do sistema e início automático com o Windows.
