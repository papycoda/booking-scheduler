"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { api, WhatsAppConversation, WhatsAppConversationDetail, WhatsAppMessage } from "../../../lib/api";
import { DashboardShell } from "../../../components/DashboardShell";

function formatTime(value?: string | null) {
  if (!value) return "";
  return new Date(value).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export default function WhatsAppInboxPage() {
  const [conversations, setConversations] = useState<WhatsAppConversation[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<WhatsAppConversationDetail | null>(null);
  const [reply, setReply] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadList() {
    const rows = await api.whatsappConversations();
    setConversations(rows);
    if (!selectedId && rows[0]) {
      setSelectedId(rows[0].id);
    }
  }

  async function loadDetail(conversationId: string) {
    if (!conversationId) return;
    const row = await api.whatsappConversation(conversationId);
    setDetail(row);
    setSelectedId(conversationId);
  }

  useEffect(() => {
    setLoading(true);
    loadList()
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load conversations"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    loadDetail(selectedId).catch((err) => setError(err instanceof Error ? err.message : "Could not load conversation"));
  }, [selectedId]);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === selectedId) ?? null,
    [conversations, selectedId],
  );

  async function claimConversation() {
    if (!selectedId) return;
    setError("");
    setMessage("");
    const updated = await api.whatsappClaimConversation(selectedId);
    setConversations((current) => current.map((conversation) => (conversation.id === updated.id ? updated : conversation)));
    await loadDetail(updated.id);
    setMessage("Conversation claimed");
  }

  async function sendReply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedId || !reply.trim()) return;
    setError("");
    setMessage("");
    await api.whatsappReplyConversation(selectedId, { body: reply.trim() });
    setReply("");
    await Promise.all([loadDetail(selectedId), loadList()]);
    setMessage("Reply sent");
  }

  return (
    <DashboardShell title="WhatsApp inbox">
      <section className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <aside className="dashboard-card h-fit p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="section-title">Conversations</h2>
              <p className="bookie-subtitle mt-1">Owner-only inbox for WhatsApp handoffs.</p>
            </div>
            {loading && <span className="text-xs font-semibold text-[#556e61]">Loading</span>}
          </div>

          <div className="mt-4 grid gap-2">
            {conversations.map((conversation) => (
              <button
                key={conversation.id}
                type="button"
                onClick={() => void loadDetail(conversation.id)}
                className={`rounded-2xl border px-4 py-3 text-left transition ${
                  conversation.id === selectedId
                    ? "border-[#0e4731]/20 bg-[#e8efe9] shadow-inner"
                    : "border-line/70 bg-white hover:bg-[#f8faf9]"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-bold text-[#0f2119]">{conversation.customer_name || conversation.customer_phone}</p>
                    <p className="mt-1 text-xs font-medium text-[#556e61]">{conversation.customer_phone}</p>
                  </div>
                  <span className="status-badge">{conversation.status}</span>
                </div>
                <p className="mt-2 line-clamp-2 text-xs text-[#556e61]">{conversation.summary || conversation.state}</p>
                <p className="mt-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d9084]">{formatTime(conversation.last_message_at)}</p>
              </button>
            ))}
            {conversations.length === 0 && <p className="soft-empty">No conversations yet.</p>}
          </div>
        </aside>

        <section className="dashboard-card min-h-[32rem] p-4">
          {detail ? (
            <>
              <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line/70 pb-4">
                <div>
                  <h2 className="section-title">{detail.customer_name || detail.customer_phone}</h2>
                  <p className="bookie-subtitle mt-1">{detail.customer_phone}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
                    <span className="status-badge">{detail.state}</span>
                    <span className="status-badge status-badge-success">{detail.status}</span>
                    {detail.booking_id && <span className="status-badge">Booking linked</span>}
                  </div>
                </div>
                <button type="button" className="secondary-button rounded-xl px-4 py-2 text-sm" onClick={() => void claimConversation()}>
                  Claim
                </button>
              </div>

              <div className="mt-5 grid gap-3 max-h-[24rem] overflow-y-auto pr-2">
                {detail.messages.map((item: WhatsAppMessage) => (
                  <div key={item.id} className={`flex ${item.direction === "inbound" ? "justify-start" : "justify-end"}`}>
                    <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${item.direction === "inbound" ? "bg-[#f8faf9] text-[#0f2119]" : "bg-[#0e4731] text-white"}`}>
                      <p className="whitespace-pre-wrap leading-relaxed">{item.body}</p>
                      <p className="mt-2 text-[10px] font-semibold uppercase tracking-[0.14em] opacity-70">
                        {item.author_type} · {formatTime(item.created_at)}
                      </p>
                    </div>
                  </div>
                ))}
                {detail.messages.length === 0 && <p className="soft-empty">No messages yet.</p>}
              </div>

              <form onSubmit={sendReply} className="mt-5 grid gap-3 border-t border-line/70 pt-4">
                <textarea
                  className="min-h-28 rounded-2xl bg-[#f8faf9]"
                  value={reply}
                  onChange={(event) => setReply(event.target.value)}
                  placeholder="Reply to the customer..."
                />
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-xs font-medium text-[#556e61]">
                    {activeConversation?.status === "human_active" ? "Human handoff is active." : "Claim the conversation before you reply."}
                  </p>
                  <button type="submit" className="rounded-xl bg-[#0e4731] px-4 py-2 text-sm font-semibold text-white">
                    Send reply
                  </button>
                </div>
              </form>
            </>
          ) : (
            <p className="soft-empty">Select a conversation to see the thread.</p>
          )}
          {message && <p className="mt-4 rounded-xl border border-[#0e4731]/15 bg-[#e8efe9] px-4 py-3 text-sm font-semibold text-[#0e4731]">{message}</p>}
          {error && <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</p>}
        </section>
      </section>
    </DashboardShell>
  );
}
