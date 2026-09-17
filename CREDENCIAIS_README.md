# Credenciais de Serviços Externos

## Google Drive (opcional - para executor próprio RAG)

### Como obter o arquivo de credenciais:

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto ou selecione um existente
3. Ative a API Google Drive
4. Crie uma conta de serviço:
   - IAM & Admin > Service Accounts > Create Service Account
5. Dê permissões à conta de serviço:
   - Google Drive API > Service Account Roles > Editor
6. Crie uma chave JSON:
   - Service Account > Keys > Add Key > Create JSON
7. Baixe o arquivo JSON e coloque em `src/middleware/credenciais/conta-de-servico.json`

### Importante:
- Este arquivo contém credenciais sensíveis
- Nunca commitar este arquivo no Git
- O diretório já está no .gitignore

## Nota:
Se você não for usar o executor próprio (RAG), este arquivo não é necessário.
Basta configurar `EXECUTOR=copilot` no .env.
