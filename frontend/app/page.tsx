"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkBreaks from "remark-breaks";
import {
  ArrowUp, Building2, CalendarDays, Check, FilePlus2, FileText, Globe,
  HeartPulse, Loader2, LogIn, LogOut, Plane, Plus, X,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const WEB_MARKER = "not official Acme Corp policy";
const TOKEN_KEY = "acme_hr_token";

type Employee = { id: string; name: string; email: string; role: string; department: string; status: string };
type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  awaitingConfirmation?: boolean;
};

const SUGGESTIONS = [
  { icon: CalendarDays, text: "How many leaves do I have left?" },
  { icon: Plane, text: "Can I work from abroad for a few weeks?" },
  { icon: FilePlus2, text: "I need casual leave on 30 October" },
  { icon: HeartPulse, text: "What does the health insurance cover?" },
];

const md: Components = {
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-5">{children}</ol>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  code: ({ children }) => (
    <code className="rounded bg-zinc-100 px-1 py-0.5 text-[12px] font-medium">{children}</code>
  ),
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noreferrer" className="underline underline-offset-2">
      {children}
    </a>
  ),
};

function Logo() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-900 text-white">
        <Building2 size={18} />
      </div>
      <div>
        <p className="text-sm font-bold tracking-tight">Acme Corp</p>
        <p className="text-xs font-light text-zinc-500">HR Assistant</p>
      </div>
    </div>
  );
}

function SourceChip({ source }: { source: string }) {
  if (source.startsWith("http")) {
    return (
      <a
        href={source}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-1.5 rounded-md bg-zinc-100 px-2 py-1 text-[11px] text-zinc-600 hover:bg-zinc-200"
      >
        <Globe size={12} /> {new URL(source).hostname.replace("www.", "")}
      </a>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-zinc-100 px-2 py-1 text-[11px] text-zinc-600">
      <FileText size={12} /> {source}
    </span>
  );
}

function FullScreenLoader() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center text-center font-sans">
      <Loader2 size={22} className="animate-spin text-zinc-400" />
      <p className="mt-4 text-sm font-semibold">Connecting to the server</p>
      <p className="mt-1 text-xs font-light text-zinc-500">If it was asleep, this can take up to a minute.</p>
    </div>
  );
}

// ---------------- Login ----------------
function LoginScreen({ onSignIn }: { onSignIn: (token: string, emp: Employee) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [accounts, setAccounts] = useState<Employee[]>([]);

  useEffect(() => {
    fetch(`${API}/demo-accounts`)
      .then((r) => r.json())
      .then(setAccounts)
      .catch(() => {});
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await fetch(`${API}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (res.status === 401) throw new Error("Invalid email or password");
      if (!res.ok) throw new Error("Couldn't reach the server");
      const data = await res.json();
      onSignIn(data.token, data.employee);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-6 py-12 font-sans">
      <div className="w-full max-w-md">
        <Logo />
        <h1 className="mt-10 text-2xl font-bold tracking-tight">Sign in</h1>
        <p className="mt-1 text-sm font-light text-zinc-500">
          Ask about company policies, check your records, or request leave.
        </p>

        <form onSubmit={submit} className="mt-8 space-y-4">
          <div>
            <label className="text-xs font-semibold text-zinc-600">Work email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-1.5 w-full rounded-lg border border-zinc-200 bg-white px-3.5 py-2.5 text-sm font-light outline-none transition focus:border-zinc-400"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-zinc-600">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="mt-1.5 w-full rounded-lg border border-zinc-200 bg-white px-3.5 py-2.5 text-sm font-light outline-none transition focus:border-zinc-400"
            />
          </div>
          {error && <p className="text-xs font-medium text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={busy}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-zinc-900 py-2.5 text-sm font-semibold text-white transition hover:bg-zinc-700 disabled:opacity-50"
          >
            {busy ? <Loader2 size={16} className="animate-spin" /> : <LogIn size={16} />}
            Sign in
          </button>
        </form>

        {accounts.length > 0 && (
          <div className="mt-10 rounded-xl border border-zinc-200 bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400">Demo accounts</p>
            <p className="mt-1 text-xs font-light text-zinc-500">
              Click an account to fill it in. Password for all: <span className="font-semibold">demo123</span>
            </p>
            <div className="mt-3 space-y-1">
              {accounts.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => {
                    setEmail(a.email);
                    setPassword("demo123");
                  }}
                  className="flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left transition hover:bg-zinc-50"
                >
                  <div>
                    <p className="text-sm font-semibold">{a.name}</p>
                    <p className="text-xs font-light text-zinc-500">{a.role}</p>
                  </div>
                  {a.status === "probation" && (
                    <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                      Probation
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        <p className="mt-6 text-center text-[11px] font-light text-zinc-400">
          Demo for a fictional company. All policies and employee records are made up.
        </p>
      </div>
    </div>
  );
}

// ---------------- Chat ----------------
function ChatApp({ token, me, onSignOut }: { token: string; me: Employee; onSignOut: () => void }) {
  const [threadId, setThreadId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const initials = me.name.split(" ").map((p) => p[0]).join("");

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function startNewChat() {
    setThreadId(crypto.randomUUID());
    setMessages([]);
    setInput("");
  }

  async function send(text: string) {
    const message = text.trim();
    if (!message || loading) return;

    setInput("");
    setMessages((prev) => [
      ...prev.map((m) => ({ ...m, awaitingConfirmation: false })),
      { role: "user", content: message },
    ]);
    setLoading(true);

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ thread_id: threadId, message }),
      });
      if (res.status === 401) {
        onSignOut(); // token expire ho gaya
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources,
          awaitingConfirmation: data.awaiting_confirmation,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong while contacting the server. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-screen font-sans">
      {/* Sidebar */}
      <aside className="hidden w-72 flex-col border-r border-zinc-200 bg-white md:flex">
        <div className="px-6 py-6">
          <Logo />
        </div>
        <div className="px-4">
          <button
            onClick={startNewChat}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-zinc-200 py-2 text-sm font-medium transition hover:bg-zinc-50"
          >
            <Plus size={16} /> New chat
          </button>
        </div>

        <div className="flex-1" />

        <div className="border-t border-zinc-200 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-zinc-100 text-xs font-bold">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">{me.name}</p>
              <p className="truncate text-xs font-light text-zinc-500">{me.role}</p>
            </div>
            <button
              onClick={onSignOut}
              title="Sign out"
              className="rounded-lg p-2 text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-900"
            >
              <LogOut size={16} />
            </button>
          </div>
          {me.status === "probation" && (
            <span className="mt-3 inline-block rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700">
              On probation
            </span>
          )}
        </div>
      </aside>

      {/* Main */}
      <main className="flex flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-zinc-200 bg-white px-6 py-4">
          <div>
            <h1 className="text-base font-bold tracking-tight">Hi, {me.name.split(" ")[0]}</h1>
            <p className="text-xs font-light text-zinc-500">Company policies, your HR records and leave requests</p>
          </div>
          <div className="flex items-center gap-1 md:hidden">
            <button onClick={startNewChat} title="New chat" className="rounded-lg p-2 text-zinc-500 hover:bg-zinc-100">
              <Plus size={18} />
            </button>
            <button onClick={onSignOut} title="Sign out" className="rounded-lg p-2 text-zinc-500 hover:bg-zinc-100">
              <LogOut size={18} />
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl px-6 py-8">
            {messages.length === 0 && (
              <div className="pt-16 text-center">
                <h2 className="text-2xl font-bold tracking-tight">How can I help today?</h2>
                <p className="mt-2 text-sm font-light text-zinc-500">
                  Ask about company policies, check your records, or request leave.
                </p>
                <div className="mt-10 grid gap-3 sm:grid-cols-2">
                  {SUGGESTIONS.map(({ icon: Icon, text }) => (
                    <button
                      key={text}
                      onClick={() => send(text)}
                      className="flex items-center gap-3 rounded-xl border border-zinc-200 bg-white p-4 text-left text-sm transition hover:border-zinc-300 hover:shadow-sm"
                    >
                      <Icon size={18} className="shrink-0 text-zinc-400" />
                      <span className="font-medium">{text}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-6">
              {messages.map((m, i) =>
                m.role === "user" ? (
                  <div key={i} className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl rounded-br-md bg-zinc-900 px-4 py-2.5 text-sm text-white">
                      {m.content}
                    </div>
                  </div>
                ) : (
                  <div key={i} className="max-w-[90%]">
                    {m.content.includes(WEB_MARKER) && (
                      <span className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-sky-50 px-2.5 py-1 text-[11px] font-medium text-sky-700">
                        <Globe size={12} /> From the web
                      </span>
                    )}
                    <div className="rounded-2xl rounded-bl-md border border-zinc-200 bg-white px-4 py-3 text-sm leading-relaxed">
                      <ReactMarkdown remarkPlugins={[remarkBreaks]} components={md}>
                        {m.content}
                      </ReactMarkdown>
                    </div>

                    {m.sources && m.sources.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {m.sources.map((s) => (
                          <SourceChip key={s} source={s} />
                        ))}
                      </div>
                    )}

                    {m.awaitingConfirmation && (
                      <div className="mt-3 flex gap-2">
                        <button
                          onClick={() => send("yes")}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-700"
                        >
                          <Check size={16} /> Confirm
                        </button>
                        <button
                          onClick={() => send("no")}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-200 bg-white px-4 py-2 text-sm font-medium transition hover:bg-zinc-50"
                        >
                          <X size={16} /> Cancel
                        </button>
                      </div>
                    )}
                  </div>
                )
              )}
            </div>

            {loading && (
              <div className="mt-6 flex items-center gap-2 text-sm font-light text-zinc-500">
                <Loader2 size={16} className="animate-spin" /> Thinking...
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        <div className="border-t border-zinc-200 bg-white">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="mx-auto flex max-w-3xl items-center gap-2 px-6 py-4"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about policies, your leave balance, or request leave..."
              className="flex-1 rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm font-light outline-none transition focus:border-zinc-400 focus:bg-white"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="flex h-11 w-11 items-center justify-center rounded-xl bg-zinc-900 text-white transition disabled:opacity-30"
            >
              <ArrowUp size={18} />
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}

// ---------------- Root ----------------
export default function Home() {
  const [auth, setAuth] = useState<"checking" | "signed_out" | "signed_in">("checking");
  const [token, setToken] = useState("");
  const [me, setMe] = useState<Employee | null>(null);

  // Page load pe: saved token valid hai to seedha chat kholo
  useEffect(() => {
    const saved = localStorage.getItem(TOKEN_KEY);
    if (!saved) {
      setAuth("signed_out");
      return;
    }
    fetch(`${API}/me`, { headers: { Authorization: `Bearer ${saved}` } })
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((emp: Employee) => {
        setToken(saved);
        setMe(emp);
        setAuth("signed_in");
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        setAuth("signed_out");
      });
  }, []);

  function signIn(newToken: string, emp: Employee) {
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
    setMe(emp);
    setAuth("signed_in");
  }

  function signOut() {
    localStorage.removeItem(TOKEN_KEY);
    setToken("");
    setMe(null);
    setAuth("signed_out");
  }

  if (auth === "checking") return <FullScreenLoader />;
  if (auth === "signed_out" || !me) return <LoginScreen onSignIn={signIn} />;
  return <ChatApp key={me.id} token={token} me={me} onSignOut={signOut} />;
}