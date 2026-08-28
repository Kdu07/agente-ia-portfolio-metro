"""Entrada por voz: transcrição via Azure Speech.

Decisão de arquitetura: o backend **emite um token de curta duração** e o
navegador fala direto com o Azure Speech. O áudio não passa pelo
middleware.

Por que não a Web Speech API do navegador, que seria gratuita e sem
infraestrutura: ela envia o áudio a servidores de terceiros fora do
tenant do parceiro. Como a camada de PII saiu do escopo, o argumento de
confidencialidade da solução passa a se apoiar inteiramente em "nada sai
do perímetro Microsoft" — e o microfone seria o primeiro furo nesse
argumento.

Por que não trafegar o áudio pelo middleware: perderia a transcrição
parcial em tempo real, que é o que faz o microfone parecer instantâneo, e
dobraria a banda por sessão sem ganho de controle — o destino final é o
mesmo tenant de qualquer forma.

O texto transcrito volta ao app e entra no `/chat` como qualquer
mensagem: as guardas valem igualmente para o que foi ditado, e a
interação é registrada com `Canal.VOZ`.
"""
