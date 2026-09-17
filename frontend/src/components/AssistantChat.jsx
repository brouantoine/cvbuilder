import { useEffect, useRef, useState } from "react";
import { cvsApi } from "../api/client";

/**
 * Dialogue guidé de création de CV : le conseiller pose une question à la
 * fois, garde les réponses, et signale la fin (done) — le parent enchaîne
 * alors sur la photo puis l'organisation des informations.
 */
export function AssistantChat({ messages, setMessages, done, onDone }) {
  const [input, setInput] = useState("");
  const [waiting, setWaiting] = useState(false);
  const [error, setError] = useState("");
  const listRef = useRef(null);
  const startedRef = useRef(false);

  // Première question : demandée au montage si la conversation est vide.
  useEffect(() => {
    if (startedRef.current || messages.length > 0) return;
    startedRef.current = true;
    setWaiting(true);
    cvsApi
      .assistantChat([])
      .then((res) => {
        setMessages([{ role: "assistant", content: res.reply }]);
        if (res.done) onDone();
      })
      .catch((err) => setError(err?.detail || "Assistant indisponible. Réessaie."))
      .finally(() => setWaiting(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Défilement automatique vers le dernier message.
  useEffect(() => {
    const node = listRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages, waiting]);

  const send = async () => {
    const content = input.trim();
    if (!content || waiting || done) return;
    setError("");
    setInput("");
    const next = [...messages, { role: "user", content }];
    setMessages(next);
    setWaiting(true);
    try {
      const res = await cvsApi.assistantChat(next);
      setMessages([...next, { role: "assistant", content: res.reply }]);
      if (res.done) onDone();
    } catch (err) {
      setError(err?.detail || "Réponse impossible. Réessaie.");
    } finally {
      setWaiting(false);
    }
  };

  const onKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  };

  return (
    <div className="assistant-chat">
      <div className="chat-messages" ref={listRef}>
        {messages.map((message, index) => (
          <div key={index} className={`chat-bubble ${message.role === "assistant" ? "ai" : "me"}`}>
            {message.content}
          </div>
        ))}
        {waiting && <div className="chat-bubble ai typing">…</div>}
      </div>
      {error && <p className="form-error global">{error}</p>}
      {!done && (
        <div className="chat-input-row">
          <textarea
            rows={2}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ta réponse… (Entrée pour envoyer)"
            disabled={waiting}
          />
          <button type="button" className="btn btn-primary" onClick={send} disabled={waiting || !input.trim()}>
            Envoyer
          </button>
        </div>
      )}
    </div>
  );
}
