import { useEffect, useState } from "react";
import QRCodeLib from "qrcode";

/**
 * Desenha o QR do ingresso.
 *
 * Gerado no cliente, e não no servidor: evita uma ida à rede por ingresso na
 * tela, e o ingresso continua aparecendo mesmo se a conexão cair depois que a
 * página carregou — que é justamente a situação da fila da portaria.
 *
 * Fundo claro sempre, inclusive no tema escuro: leitor de QR precisa de
 * contraste entre módulo escuro e fundo claro, e invertê-lo quebra a leitura
 * em vários aparelhos.
 */
export function QRCode({ valor, tamanho = 220 }: { valor: string; tamanho?: number }) {
  const [dataUrl, setDataUrl] = useState("");
  const [erro, setErro] = useState(false);

  useEffect(() => {
    let ativo = true;
    QRCodeLib.toDataURL(valor, {
      width: tamanho,
      margin: 2,
      errorCorrectionLevel: "M",
      color: { dark: "#0c0b0d", light: "#ffffff" },
    })
      .then((url) => ativo && setDataUrl(url))
      .catch(() => ativo && setErro(true));
    return () => {
      ativo = false;
    };
  }, [valor, tamanho]);

  if (erro) {
    return (
      <p className="alert alert--error" style={{ fontSize: "var(--text-sm)" }}>
        Não foi possível gerar o QR. Use o código abaixo na portaria.
      </p>
    );
  }

  return (
    <div className="qr" style={{ width: tamanho, height: tamanho }}>
      {dataUrl && <img src={dataUrl} alt="Código QR do ingresso" width={tamanho} height={tamanho} />}
    </div>
  );
}
