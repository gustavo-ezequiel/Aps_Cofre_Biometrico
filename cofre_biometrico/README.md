# Cofre Biométrico – Sistema de Identificação e Autenticação Biométrica

APS 5º/6º semestre de Ciência da Computação (UNIP), disciplina PIVC.
O sistema faz reconhecimento facial em tempo real para controlar o acesso a um cofre com 3 níveis de segurança.

## Como rodar

1. Instale o **Python 3.10 ou superior** (no Windows, marque "Add Python to PATH").
2. No terminal, dentro da pasta do projeto, rode:
   ```
   pip install -r requirements.txt
   python main.py
   ```
3. Cadastre pelo menos 2 pessoas (opção 2) e teste o acesso (opção 1).

Para usar o **MySQL do XAMPP**, siga estes passos:
- inicie o MySQL no painel do XAMPP;
- em `config.py`, troque `DB_ENGINE = "sqlite"` por `DB_ENGINE = "mysql"`;
- o banco e as tabelas são criados automaticamente (ou rode `sql/schema_mysql.sql` no phpMyAdmin).

## Regras de acesso

| Nível do usuário | Pode abrir as áreas |
|---|---|
| 1 – Permissão geral | 1 |
| 2 – Diretor de divisão | 1 e 2 |
| 3 – Ministro do Meio Ambiente | 1, 2 e 3 |

O acesso é concedido quando **nível do usuário ≥ nível da área**.

## Conteúdo do cofre (3 tabelas no banco)

Quando o acesso é concedido, o sistema abre a tabela da área escolhida. O conteúdo aparece no terminal e numa janela.

| Área | Tabela | Conteúdo |
|---|---|---|
| 1 | `nivel1_baixa_periculosidade` | Baixa periculosidade ambiental (bicarbonato de sódio, ácido cítrico, sal…) |
| 2 | `nivel2_periculosidade_moderada` | Periculosidade moderada a elevada (hipoclorito, amônia, formaldeído…) |
| 3 | `nivel3_periculosidade_extrema` | Periculosidade ambiental extrema (dioxinas, PCBs, metilmercúrio, TBT) |

As tabelas são recriadas automaticamente toda vez que o programa inicia, a partir do arquivo `dados_cofre.py`. Para mudar o conteúdo, edite esse arquivo e rode o programa de novo. Alterações feitas direto no phpMyAdmin são sobrescritas.

## As 5 fases do processamento de imagens no código

| Fase | Onde está (`processamento.py`) | O que faz |
|---|---|---|
| 1. Aquisição | `Camera`, `carregar_imagem` | Captura da webcam em tempo real; opcionalmente lê fotos de arquivo (scanner/câmera) |
| 2. Pré-processamento | `pre_processar`, `avaliar_qualidade` | Converte para tons de cinza, aplica filtro Gaussiano (ruído) e equalização CLAHE (iluminação); rejeita imagem escura ou borrada |
| 3. Segmentação | `detectar_rostos`, `detectar_olhos` | Detector Viola-Jones (Haar cascade) isola o rosto e os olhos |
| 4. Representação e descrição | `extrair_rosto` + LBP | Recorta, alinha pelos olhos, redimensiona para 200×200 e equaliza; o LBPH descreve o rosto como histogramas de padrões binários locais (grade 8×8) |
| 5. Reconhecimento e interpretação | `Reconhecedor`, `ProvaDeVida`, `main.verificar_acesso` | Compara os histogramas (distância), confirma por vários quadros seguidos, verifica a piscada e decide pelo nível de permissão |

## Funções extras (contam na nota de "qualidade do sistema")

- **Prova de vida**: exige uma piscada, o que impede abrir o cofre com foto impressa ou com foto na tela do celular.
- **Confirmação por votação**: a decisão só sai depois de 8 quadros seguidos com a mesma identidade, o que reduz falsos positivos.
- **Uma pessoa por vez**: se houver mais de um rosto na câmera, a verificação não prossegue.
- **Bloqueio do terminal**: após 3 negações seguidas, o terminal fica bloqueado por 60 s.
- **Foto do intruso**: todo acesso negado salva uma foto em `dados/intrusos/`.
- **Log de auditoria**: cada tentativa fica registrada no banco com data/hora, área, usuário, motivo e distância.
- **Relatórios**: relatório em HTML (estatísticas, usuários e histórico com fotos) e exportação para CSV/Excel.
- **Controle de qualidade no cadastro**: amostras escuras, estouradas ou borradas são descartadas.
- **Cadastro por pasta de imagens**: aceita fotos de scanner ou câmera, com aumento de dados por espelhamento.
- **Gestão de usuários**: listar, alterar nível e desativar sem apagar o histórico.

## Estrutura

```
main.py            menu, cadastro, verificação de acesso
processamento.py   pipeline das 5 fases (OpenCV)
banco.py           SQLite ou MySQL (usuarios, acessos)
relatorios.py      relatório HTML e CSV
config.py          parâmetros (câmera, limiar, banco, segurança)
modelos/           classificadores Haar (incluídos porque o OpenCV 5 não traz mais)
sql/               script do banco para MySQL/XAMPP
dados/             criado ao rodar: rostos, modelo treinado, intrusos, relatórios
```

## Ajuste fino (calibração)

O LBPH devolve uma **distância**: quanto menor, mais parecido. `LIMIAR_LBPH` (padrão 65) é o máximo aceito.
- Se pessoas cadastradas estão sendo **recusadas**, aumente o valor para 70–80, ou recadastre num ambiente com boa luz.
- Se um **desconhecido é aceito**, diminua o valor para 50–55.

Para calibrar, faça várias tentativas e observe a coluna "Distância" do relatório HTML. Esses números também servem como resultados de teste na dissertação.

Se a prova de vida atrapalhar a demonstração (óculos com reflexo, pouca luz), desligue com `PROVA_DE_VIDA = False`.
