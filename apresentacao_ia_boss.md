**COMBAT GODS**
**Documento de Apresentação — Sistema de IA Adaptativa do Boss Final**

---

**VISÃO GERAL**

Combat Gods é um jogo de ação e plataforma 2D onde o jogador enfrenta bosses progressivamente mais difíceis. O boss final, **Morthak — Bringer of Death**, possui um sistema de inteligência artificial em duas camadas que aprende e se adapta ao estilo de jogo do jogador em tempo real, tornando cada confronto único.

---

**O QUE É IA ADAPTATIVA**

A maioria dos jogos utiliza IA reativa: o inimigo apenas responde ao que está acontecendo no momento. No Combat Gods, o boss final vai além disso. Ele observa o comportamento do jogador ao longo de toda a luta e modifica seus padrões de ataque de acordo com o que aprendeu.

Isso significa que um jogador que sempre esquiva para a esquerda vai encontrar magias caindo mais à esquerda. Um jogador que depende muito de projéteis vai ver o boss ficar mais agressivo e se mover mais rápido. Cada sessão de luta é diferente.

---

**MÉTRICAS COLETADAS DURANTE O COMBATE**

O sistema registra continuamente:

• Quantidade de projéteis mágicos disparados pelo jogador
• Quantidade de raios divinos utilizados
• Quantidade de poções consumidas
• Número de esquivas para a esquerda
• Número de esquivas para a direita
• Tempo total em combate corpo a corpo
• Tempo total mantido à distância

Esses dados alimentam as quatro adaptações descritas abaixo.

---

**AS QUATRO ADAPTAÇÕES**

**1. Modo Anti-Ranged**

Ativado quando o jogador dispara 8 ou mais projéteis.

O boss reconhece que está sendo combatido à distância e responde de forma inteligente: aumenta a velocidade de caminhada em 20%, passa a lançar magias com o dobro de frequência e pressiona o jogador para o combate corpo a corpo.

Mensagem exibida na tela: **ADAPTAÇÃO CONCLUÍDA**

**2. Previsão de Movimento**

O boss aprende a antecipar para onde o jogador vai se mover.

Inicialmente, as magias caem exatamente onde o jogador está. A cada magia que erra, o sistema aumenta o nível de antecipação:

• 1ª magia que erra: antecipa 0.25 segundos de movimento
• 2ª magia que erra: antecipa 0.35 segundos
• 3ª magia que erra: antecipa 0.45 segundos
• 4ª magia em diante: antecipa 0.55 segundos

O resultado prático é que fugir em linha reta para o mesmo lado deixa de funcionar ao longo da luta.

Mensagem exibida na tela: **PREVISÃO APRIMORADA**

**3. Viés de Esquiva**

O boss analisa o padrão de esquivas do jogador.

Se mais de 70% das esquivas foram feitas em uma única direção (após pelo menos 5 esquivas registradas), todas as magias e explosões de magia do boss passam a ser deslocadas nessa direção, cobrindo o lado preferido do jogador.

Mensagem exibida na tela: **PADRÃO DETECTADO**

**4. Resistência a Stun**

O Raio Divino é a habilidade mais poderosa do jogador, capaz de paralisar o boss. Mas o boss desenvolve resistência a cada uso:

• 1º raio: paralisa por 3.0 segundos
• 2º raio: paralisa por 2.0 segundos
• 3º raio: paralisa por 1.0 segundo
• 4º raio em diante: paralisa por apenas 0.5 segundos

Usar o raio repetidamente como estratégia dominante torna o raio cada vez menos eficaz.

Mensagem exibida na tela: **RESISTÊNCIA DESENVOLVIDA**

---

**AS TRÊS FASES DE HP**

Além das adaptações comportamentais, o boss escala automaticamente conforme perde vida:

**Fase 1 (acima de 66% de vida)**
Comportamento padrão. O boss usa seus padrões base.

**Fase 2 (33% a 66% de vida)**
Velocidade aumenta em 15%. Intervalo entre magias reduzido em 15%. O boss fica visivelmente mais agressivo.

Mensagem exibida na tela: **ANALISANDO PADRÕES...**

**Fase 3 (abaixo de 33% de vida)**
Velocidade aumenta em 25%. Intervalo entre magias reduzido em 25%. Intervalo entre explosões de magia reduzido em 25%. Fase mais perigosa da luta.

Mensagem exibida na tela: **RESISTÊNCIA DESENVOLVIDA**

---

**FEEDBACK VISUAL**

Todas as adaptações são comunicadas ao jogador em tempo real através de mensagens exibidas na parte superior da tela, abaixo da barra de vida do boss. As mensagens aparecem em roxo, com efeito de fade, para que o jogador saiba que o boss está aprendendo.

Isso cria um elemento de tensão narrativa: o jogador vê que o inimigo está reagindo às suas escolhas.

---

**HABILIDADES DO JOGADOR AFETADAS**

O sistema considera três habilidades especiais do jogador como gatilhos de adaptação:

• **Projétil Mágico (tecla F):** cada disparo aproxima o boss do Modo Anti-Ranged
• **Raio Divino (tecla Q):** cada uso reduz a duração do próximo stun
• **Esquiva (tecla Shift):** padrão de direção é monitorado para o viés de magia

---

**RESULTADO PARA O JOGADOR**

O sistema foi projetado para que nenhuma estratégia única funcione indefinidamente. O jogador que sempre faz a mesma coisa encontrará um boss progressivamente mais difícil de vencer com aquela abordagem. Isso incentiva criatividade, adaptação e domínio das mecânicas do jogo.

A IA não é mais forte que o jogador. Ela é mais **inteligente** sobre o jogador.
