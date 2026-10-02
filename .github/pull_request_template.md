## 📋 Descrição das Alterações
Descreva de forma clara e concisa o que este Pull Request introduz (correção de bug, nova funcionalidade, refatoração de pipeline).

## 🎯 Tipo de Mudança
- [ ] 🐛 Correção de bug (bugfix sem quebra de compatibilidade)
- [ ] ✨ Nova funcionalidade (feature sem quebra de contrato de dados)
- [ ] ⚡ Otimização de performance / query SQL / Power Query
- [ ] 🛡️ Reforço de segurança / auditoria / LGPD
- [ ] 📝 Documentação técnica / ADR

## 🧪 Checklist de Qualidade & Testes
- [ ] O código adere aos padrões de estilo do projeto (PEP 8 / SQL Standard).
- [ ] Os testes unitários do extrator (`tests/test_extrator_bancario.py`) foram executados e passaram com sucesso.
- [ ] A suíte de integridade de dados (`tests/test_dashboard_integridade.py`) passou 100%.
- [ ] A suíte de resiliência e gargalos (`tests/test_gargalos_resiliencia.py`) passou 100%.
- [ ] Não há chaves de API, senhas ou tokens expostos no código (variáveis em `.env`).
- [ ] A garantia de idempotência (SHA-256) foi preservada.
