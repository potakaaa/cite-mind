"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import ReactMarkdown from "react-markdown"
import {
  RiAccountCircleLine,
  RiAddLine,
  RiArrowDownSLine,
  RiArrowRightLine,
  RiAttachment2,
  RiBookOpenLine,
  RiChat1Line,
  RiCheckboxCircleLine,
  RiCloseLine,
  RiEqualizerLine,
  RiErrorWarningLine,
  RiFilePdfLine,
  RiFileTextLine,
  RiFolderLine,
  RiHistoryLine,
  RiLeafLine,
  RiMenuLine,
  RiPulseLine,
  RiSearchLine,
  RiSendPlane2Line,
  RiShieldCheckLine,
  RiStackLine,
  RiSettings3Line,
  RiSparkling2Line,
} from "@remixicon/react"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
const STORAGE_KEY = "cite-mind:conversations"

type TraceEntry = { actor: string; action: string; status: string }
type Message = {
  id: string
  role: "user" | "assistant"
  content: string
  attachments?: string[]
  trace?: TraceEntry[]
  error?: boolean
}
type Conversation = {
  id: string
  title: string
  messages: Message[]
  updatedAt: number
}
type Section =
  | "chat"
  | "library"
  | "projects"
  | "history"
  | "settings"
  | "account"

const navItems: { id: Section; label: string; icon: typeof RiBookOpenLine }[] =
  [
    { id: "chat", label: "New research", icon: RiAddLine },
    { id: "library", label: "Library", icon: RiBookOpenLine },
    { id: "projects", label: "Projects", icon: RiFolderLine },
    { id: "history", label: "History", icon: RiHistoryLine },
  ]

const starterPrompts = [
  {
    title: "Summarize a paper",
    description: "Extract the argument, evidence, and limitations.",
    meta: "Single source",
    prompt: "Summarize this paper: ",
    icon: RiFileTextLine,
  },
  {
    title: "Compare sources",
    description: "Find where two papers agree and diverge.",
    meta: "Source synthesis",
    prompt: "Compare these sources: ",
    icon: RiEqualizerLine,
  },
  {
    title: "Build a literature review",
    description: "Organize themes and identify research gaps.",
    meta: "Deep research",
    prompt: "Build a literature review about: ",
    icon: RiBookOpenLine,
  },
]

function createConversation(): Conversation {
  return {
    id: crypto.randomUUID(),
    title: "Untitled research",
    messages: [],
    updatedAt: Date.now(),
  }
}

export default function Page() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState("")
  const [section, setSection] = useState<Section>("chat")
  const [providers, setProviders] = useState<string[]>([])
  const [provider, setProvider] = useState("")
  const [message, setMessage] = useState("")
  const [files, setFiles] = useState<File[]>([])
  const [pending, setPending] = useState(false)
  const [pendingStage, setPendingStage] = useState(
    "Coordinator is preparing the request"
  )
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    let parsed: Conversation[] = []
    try {
      parsed = stored ? (JSON.parse(stored) as Conversation[]) : []
    } catch {
      localStorage.removeItem(STORAGE_KEY)
    }
    const initial = parsed.length ? parsed : [createConversation()]
    setConversations(initial)
    setActiveId(initial[0].id)
    fetch(`${API_BASE}/api/providers`)
      .then((response) => response.json())
      .then((data: { providers: string[]; default: string }) => {
        setProviders(data.providers.length ? data.providers : [data.default])
        setProvider(data.default)
      })
      .catch(() => {
        setProviders(["ollama"])
        setProvider("ollama")
      })
  }, [])

  useEffect(() => {
    if (conversations.length)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations))
  }, [conversations])

  useEffect(() => {
    if (!pending) return
    const stages = [
      "Coordinator is preparing the request",
      "DocumentReader is reading the supplied context",
      "Synthesizer is drafting the response",
    ]
    let index = 0
    const timer = window.setInterval(() => {
      index = Math.min(index + 1, stages.length - 1)
      setPendingStage(stages[index])
    }, 1200)
    return () => window.clearInterval(timer)
  }, [pending])

  const active = useMemo(
    () =>
      conversations.find((conversation) => conversation.id === activeId) ??
      conversations[0],
    [activeId, conversations]
  )

  function newChat() {
    const next = createConversation()
    setConversations((current) => [next, ...current])
    setActiveId(next.id)
    setSection("chat")
  }

  function updateActive(updater: (conversation: Conversation) => Conversation) {
    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === activeId ? updater(conversation) : conversation
      )
    )
  }

  async function sendMessage() {
    const trimmed = message.trim()
    if (!trimmed || pending || !active) return
    const outgoing: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      attachments: files.map((file) => file.name),
    }
    const history = active.messages.map(({ role, content }) => ({
      role,
      content,
    }))
    updateActive((conversation) => ({
      ...conversation,
      title: conversation.messages.length
        ? conversation.title
        : trimmed.slice(0, 36),
      messages: [...conversation.messages, outgoing],
      updatedAt: Date.now(),
    }))
    setMessage("")
    setPending(true)

    const body = new FormData()
    body.append("message", trimmed)
    body.append("history", JSON.stringify(history))
    if (provider) body.append("provider", provider)
    files.forEach((file) => body.append("attachments", file))

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        body,
      })
      const data = (await response.json()) as {
        answer?: string
        trace?: TraceEntry[]
        attachments?: string[]
        detail?: string
      }
      if (!response.ok)
        throw new Error(data.detail ?? "The request could not be completed.")
      updateActive((conversation) => ({
        ...conversation,
        messages: [
          ...conversation.messages,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: data.answer ?? "",
            trace: data.trace,
          },
        ],
        updatedAt: Date.now(),
      }))
      setFiles([])
    } catch (error) {
      updateActive((conversation) => ({
        ...conversation,
        messages: [
          ...conversation.messages,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content:
              error instanceof Error
                ? error.message
                : "The request could not be completed.",
            error: true,
          },
        ],
        updatedAt: Date.now(),
      }))
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="workspace-shell flex h-svh overflow-hidden bg-background text-foreground">
      <aside className="hidden w-[272px] shrink-0 border-r border-sidebar-border bg-sidebar md:flex">
        <Sidebar
          conversations={conversations}
          activeId={activeId}
          section={section}
          onNewChat={newChat}
          onOpenChat={(id) => {
            setActiveId(id)
            setSection("chat")
          }}
          onSection={setSection}
        />
      </aside>

      <main className="relative flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex h-[72px] shrink-0 items-center justify-between border-b bg-background/75 px-4 backdrop-blur-xl md:px-7">
          <div className="flex min-w-0 items-center gap-3">
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="md:hidden">
                  <RiMenuLine />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-[272px] p-0">
                <SheetTitle className="sr-only">Navigation</SheetTitle>
                <Sidebar
                  conversations={conversations}
                  activeId={activeId}
                  section={section}
                  onNewChat={newChat}
                  onOpenChat={(id) => {
                    setActiveId(id)
                    setSection("chat")
                  }}
                  onSection={setSection}
                />
              </SheetContent>
            </Sheet>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold tracking-[0.2em] text-muted-foreground uppercase">
                {section === "chat" ? "Research workspace" : "Workspace"}
              </p>
              <h1 className="truncate text-lg font-bold tracking-tight md:text-xl">
                {section === "chat"
                  ? (active?.title ?? "Untitled research")
                  : sectionLabel(section)}
              </h1>
            </div>
          </div>
          <div className="hidden items-center gap-2 sm:flex">
            <Badge
              variant="outline"
              className="h-8 gap-2 rounded-full border-primary/15 bg-card/80 px-3 text-[10px] font-semibold tracking-[0.12em] text-muted-foreground uppercase shadow-xs"
            >
              <span className="relative flex size-2">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-50" />
                <span className="relative inline-flex size-2 rounded-full bg-success" />
              </span>
              Workspace ready
            </Badge>
          </div>
        </header>

        {section === "chat" ? (
          <ChatPanel
            active={active}
            files={files}
            pending={pending}
            pendingStage={pendingStage}
            message={message}
            provider={provider}
            providers={providers}
            fileInput={fileInput}
            onFiles={setFiles}
            onMessage={setMessage}
            onProvider={setProvider}
            onSend={sendMessage}
          />
        ) : (
          <Placeholder section={section} conversations={conversations} />
        )}
      </main>
    </div>
  )
}

function Sidebar({
  conversations,
  activeId,
  section,
  onNewChat,
  onOpenChat,
  onSection,
}: {
  conversations: Conversation[]
  activeId: string
  section: Section
  onNewChat: () => void
  onOpenChat: (id: string) => void
  onSection: (section: Section) => void
}) {
  return (
    <div className="flex h-full w-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="p-4 pb-3">
        <div className="mb-6 flex items-center gap-2.5 px-1 pt-1">
          <Logo />
          <div>
            <div className="text-[15px] font-bold tracking-tight">
              Cite Mind
            </div>
            <div className="text-[10px] font-medium tracking-[0.18em] text-muted-foreground uppercase">
              Research copilot
            </div>
          </div>
        </div>
        <Button
          onClick={onNewChat}
          className="h-11 w-full justify-start gap-2 rounded-xl px-3 text-[14px] font-semibold shadow-[0_8px_20px_-12px_var(--primary)]"
        >
          <RiAddLine /> Start new research
        </Button>
      </div>
      <ScrollArea className="min-h-0 flex-1 px-3">
        <div className="space-y-6 pb-4">
          <div>
            <SidebarLabel>Workspace</SidebarLabel>
            <div className="space-y-0.5">
              {navItems.slice(1).map((item) => (
                <SidebarNavButton
                  key={item.id}
                  icon={item.icon}
                  label={item.label}
                  active={section === item.id}
                  onClick={() => onSection(item.id)}
                />
              ))}
            </div>
          </div>
          <div>
            <SidebarLabel>Recent</SidebarLabel>
            <div className="space-y-0.5">
              {conversations.slice(0, 5).map((conversation) => (
                <button
                  key={conversation.id}
                  onClick={() => onOpenChat(conversation.id)}
                  className={cn(
                    "flex w-full items-center gap-2.5 truncate rounded-md px-2.5 py-2 text-left text-[13px] font-medium text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring/40 focus-visible:outline-none",
                    activeId === conversation.id &&
                      section === "chat" &&
                      "bg-sidebar-accent text-sidebar-accent-foreground"
                  )}
                >
                  <RiChat1Line className="size-4 shrink-0" />
                  <span className="truncate">{conversation.title}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </ScrollArea>
      <div className="mx-3 mb-2 rounded-xl border border-primary/10 bg-primary/[0.045] p-3">
        <div className="flex items-center gap-2 text-[11px] font-semibold text-primary">
          <RiShieldCheckLine className="size-4" />
          Private workspace
        </div>
        <p className="mt-1.5 text-[10px] leading-4 text-muted-foreground">
          Your research history stays in this local workspace.
        </p>
      </div>
      <div className="space-y-0.5 border-t border-sidebar-border p-3">
        <SidebarNavButton
          icon={RiSettings3Line}
          label="Settings"
          active={section === "settings"}
          onClick={() => onSection("settings")}
        />
        <SidebarNavButton
          icon={RiAccountCircleLine}
          label="Account"
          active={section === "account"}
          onClick={() => onSection("account")}
        />
      </div>
    </div>
  )
}

function ChatPanel({
  active,
  files,
  pending,
  pendingStage,
  message,
  provider,
  providers,
  fileInput,
  onFiles,
  onMessage,
  onProvider,
  onSend,
}: {
  active?: Conversation
  files: File[]
  pending: boolean
  pendingStage: string
  message: string
  provider: string
  providers: string[]
  fileInput: React.RefObject<HTMLInputElement | null>
  onFiles: (files: File[]) => void
  onMessage: (message: string) => void
  onProvider: (provider: string) => void
  onSend: () => void
}) {
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [active?.messages.length, pending, pendingStage])

  return (
    <>
      <ScrollArea className="min-h-0 flex-1">
        <div className="mx-auto w-full max-w-[1080px] space-y-6 px-4 py-5 md:px-7 md:py-6">
          {!active?.messages.length && <Welcome onSelect={onMessage} />}
          {active?.messages.map((item) =>
            item.role === "user" ? (
              <UserMessage key={item.id} item={item} />
            ) : (
              <AssistantMessage key={item.id} item={item} />
            )
          )}
          {pending && (
            <ReasoningPanel
              trace={[
                {
                  actor: "Coordinator",
                  action: pendingStage,
                  status: "running",
                },
              ]}
              defaultOpen
            />
          )}
          <div ref={bottom} aria-hidden="true" />
        </div>
      </ScrollArea>
      <Composer
        files={files}
        fileInput={fileInput}
        message={message}
        pending={pending}
        provider={provider}
        providers={providers}
        onFiles={onFiles}
        onMessage={onMessage}
        onProvider={onProvider}
        onSend={onSend}
      />
    </>
  )
}

function Welcome({ onSelect }: { onSelect: (prompt: string) => void }) {
  return (
    <section className="relative pt-1">
      <div className="pointer-events-none absolute -top-28 right-0 h-80 w-80 rounded-full bg-primary/10 blur-3xl" />
      <div className="relative grid items-end gap-8 xl:grid-cols-[1fr_260px]">
        <div className="max-w-2xl">
          <Badge
            variant="secondary"
            className="mb-4 h-7 gap-1.5 rounded-full border border-primary/10 bg-primary/8 px-3 text-[10px] tracking-[0.16em] text-primary uppercase shadow-xs"
          >
            <RiSparkling2Line className="size-3" /> Academic research assistant
          </Badge>
          <h2 className="max-w-2xl text-[3rem] leading-[0.93] font-bold tracking-[-0.075em] md:text-[4.6rem]">
            Think deeper.
            <span className="block bg-gradient-to-r from-primary via-primary/85 to-primary/60 bg-clip-text text-transparent">
              Cite smarter.
            </span>
          </h2>
          <p className="mt-4 max-w-xl text-base leading-7 font-medium text-muted-foreground md:text-[17px]">
            Turn scattered sources into grounded insights, clear arguments, and
            research you can stand behind.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-[11px] font-semibold tracking-wide text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <RiShieldCheckLine className="size-3.5 text-primary" />{" "}
              Source-aware
            </span>
            <span className="flex items-center gap-1.5">
              <RiPulseLine className="size-3.5 text-primary" /> Evidence-first
            </span>
            <span className="flex items-center gap-1.5">
              <RiLeafLine className="size-3.5 text-primary" /> Built for focus
            </span>
          </div>
        </div>
        <div className="hidden rounded-[1.35rem] border border-primary/10 bg-card/70 p-3 shadow-[0_24px_65px_-42px_var(--primary)] backdrop-blur-sm xl:block">
          <div className="rounded-xl border bg-background/70 p-3">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-bold tracking-[0.16em] text-muted-foreground uppercase">
                Evidence map
              </span>
              <span className="flex items-center gap-1 text-[9px] font-semibold text-success">
                <span className="size-1.5 rounded-full bg-success" /> Live
              </span>
            </div>
            <div className="mt-4 flex h-20 items-center justify-center">
              <div className="evidence-orbit relative flex size-16 items-center justify-center rounded-full border border-primary/15 bg-primary/6">
                <RiSearchLine className="size-5 text-primary" />
                <span className="absolute -top-2 left-1 size-3 rounded-full border-2 border-card bg-success" />
                <span className="absolute right-0 -bottom-1 size-3.5 rounded-full border-2 border-card bg-primary/70" />
                <span className="absolute top-5 -left-3 size-2.5 rounded-full border-2 border-card bg-primary/35" />
              </div>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <div className="rounded-lg bg-muted/70 p-2">
                <p className="text-base font-bold tracking-tight">24</p>
                <p className="text-[9px] tracking-wide text-muted-foreground uppercase">
                  Sources
                </p>
              </div>
              <div className="rounded-lg bg-muted/70 p-2">
                <p className="text-base font-bold tracking-tight">91%</p>
                <p className="text-[9px] tracking-wide text-muted-foreground uppercase">
                  Coverage
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="mt-7 flex items-center gap-3">
        <span className="text-[10px] font-semibold tracking-[0.18em] text-muted-foreground uppercase">
          Start a workflow
        </span>
        <Separator className="flex-1" />
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        {starterPrompts.map(
          ({ title, description, meta, prompt, icon: Icon }, index) => (
            <button
              key={title}
              onClick={() => onSelect(prompt)}
              className={cn(
                "group relative overflow-hidden rounded-2xl border bg-card/80 p-3.5 text-left shadow-xs transition-all duration-300 hover:-translate-y-1 hover:border-primary/35 hover:shadow-[0_18px_40px_-28px_var(--primary)] focus-visible:border-primary/50 focus-visible:ring-2 focus-visible:ring-primary/20 focus-visible:outline-none",
                index === 0 && "md:col-span-1"
              )}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex size-9 items-center justify-center rounded-xl border border-primary/10 bg-primary/8 text-primary">
                  <Icon className="size-4" />
                </div>
                <RiArrowRightLine className="mt-2 size-4 text-muted-foreground transition-all group-hover:translate-x-1 group-hover:text-primary" />
              </div>
              <p className="mt-4 text-[10px] font-semibold tracking-[0.15em] text-primary uppercase">
                {meta}
              </p>
              <h3 className="mt-2 text-base font-bold">{title}</h3>
              <p className="mt-1 text-xs leading-5 text-muted-foreground md:text-sm">
                {description}
              </p>
            </button>
          )
        )}
      </div>
    </section>
  )
}

function UserMessage({ item }: { item: Message }) {
  return (
    <div className="flex flex-col items-end gap-2">
      <div className="max-w-[88%] rounded-2xl rounded-br-md bg-primary px-4 py-3 text-[15px] leading-6 font-medium text-primary-foreground shadow-sm">
        <p>{item.content}</p>
      </div>
      {item.attachments?.map((attachment) => (
        <AttachmentChip key={attachment} name={attachment} />
      ))}
    </div>
  )
}

function AssistantMessage({ item }: { item: Message }) {
  return (
    <div className="space-y-4">
      {item.trace?.length ? <ReasoningPanel trace={item.trace} /> : null}
      <div className="flex items-start gap-3">
        <Avatar className="mt-0.5 size-8 shadow-sm">
          <AvatarFallback className="bg-primary text-[10px] font-semibold text-primary-foreground">
            CM
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex items-center gap-2">
            <span className="text-base font-bold">Cite Mind</span>
            <Badge
              variant="secondary"
              className="text-[9px] tracking-wider text-muted-foreground uppercase"
            >
              Assistant
            </Badge>
          </div>
          <div
            className={cn(
              "rounded-2xl rounded-tl-md border bg-card p-5 shadow-xs md:p-6",
              item.error && "border-destructive/25 bg-destructive/5"
            )}
          >
            {item.error && (
              <RiErrorWarningLine className="mb-3 size-5 text-destructive" />
            )}
            <div className="research-prose">
              <ReactMarkdown>{item.content}</ReactMarkdown>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function ReasoningPanel({
  trace,
  defaultOpen = false,
}: {
  trace: TraceEntry[]
  defaultOpen?: boolean
}) {
  return (
    <Collapsible
      defaultOpen={defaultOpen}
      className="max-w-[94%] space-y-2 pl-11"
    >
      <div className="flex items-center gap-3">
        <CollapsibleTrigger className="flex items-center gap-1.5 text-[10px] font-semibold tracking-[0.14em] text-muted-foreground uppercase transition-colors hover:text-foreground">
          <RiArrowDownSLine className="size-4" /> Research process
        </CollapsibleTrigger>
        <Separator className="flex-1" />
      </div>
      <CollapsibleContent>
        <div className="space-y-2 rounded-xl border bg-muted/50 p-3.5 font-mono text-[11px] leading-5 text-muted-foreground">
          {trace.map((item, index) => (
            <div key={`${item.actor}-${index}`} className="flex gap-2">
              {item.status === "running" ? (
                <span className="mt-1.5 size-2 shrink-0 animate-pulse rounded-full bg-primary" />
              ) : (
                <RiCheckboxCircleLine className="mt-0.5 size-4 shrink-0 text-success" />
              )}
              <span>
                <strong className="font-semibold text-foreground">
                  [{item.actor}]
                </strong>{" "}
                {item.action}
              </span>
            </div>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

function Composer({
  files,
  fileInput,
  message,
  pending,
  provider,
  providers,
  onFiles,
  onMessage,
  onProvider,
  onSend,
}: {
  files: File[]
  fileInput: React.RefObject<HTMLInputElement | null>
  message: string
  pending: boolean
  provider: string
  providers: string[]
  onFiles: (files: File[]) => void
  onMessage: (message: string) => void
  onProvider: (provider: string) => void
  onSend: () => void
}) {
  return (
    <div className="pointer-events-none shrink-0 bg-gradient-to-t from-background via-background/95 to-transparent px-4 pt-3 pb-3 md:px-6 md:pt-4 md:pb-4">
      <div className="pointer-events-auto mx-auto max-w-[1080px]">
        {files.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {files.map((file) => (
              <AttachmentChip
                key={`${file.name}-${file.size}-${file.lastModified}`}
                name={file.name}
                onRemove={() => onFiles(files.filter((item) => item !== file))}
              />
            ))}
          </div>
        )}
        <div className="rounded-[1.35rem] border border-primary/10 bg-card/95 p-2.5 shadow-[0_18px_55px_-24px_color-mix(in_oklch,var(--foreground),transparent_62%)] backdrop-blur-xl transition-shadow focus-within:shadow-[0_20px_65px_-25px_color-mix(in_oklch,var(--primary),transparent_48%)]">
          <Textarea
            value={message}
            onChange={(event) => onMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault()
                onSend()
              }
            }}
            placeholder="Ask a question, explore a topic, or analyze a source..."
            rows={1}
            className="min-h-11 max-h-36 resize-none border-0 bg-transparent px-3 py-2 text-[17px] leading-7 font-medium shadow-none placeholder:text-muted-foreground/80 focus-visible:ring-0 md:text-lg"
          />
          <div className="flex items-center justify-between gap-3 border-t px-0.5 pt-2.5">
            <div className="flex min-w-0 items-center gap-1.5">
              <input
                ref={fileInput}
                type="file"
                accept=".pdf,.txt,.md"
                multiple
                hidden
                onChange={(event) => {
                  onFiles([...files, ...Array.from(event.target.files ?? [])])
                  event.target.value = ""
                }}
              />
              <Button
                variant="ghost"
                onClick={() => fileInput.current?.click()}
                className="h-10 gap-2 rounded-xl px-3 text-sm text-muted-foreground"
              >
                <RiAttachment2 className="size-5" />
                <span className="hidden sm:inline">Add sources</span>
                <span className="sr-only sm:hidden">Add sources</span>
              </Button>
              <span className="hidden text-xs font-medium tracking-wide text-muted-foreground md:inline">
                PDF, TXT, MD
              </span>
              <Separator orientation="vertical" className="mx-1 h-6" />
              <Select value={provider} onValueChange={onProvider}>
                <SelectTrigger className="h-10 max-w-[170px] rounded-xl border-0 bg-muted/70 px-3 text-sm text-muted-foreground shadow-none">
                  <RiEqualizerLine className="size-4" />
                  <SelectValue placeholder="Provider" />
                </SelectTrigger>
                <SelectContent>
                  {providers.map((item) => (
                    <SelectItem key={item} value={item}>
                      {item}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              disabled={pending || !message.trim()}
              onClick={onSend}
              aria-label="Send research request"
              className="size-11 rounded-full p-0 shadow-sm transition-transform hover:scale-105"
            >
              <RiSendPlane2Line className="size-5" />
            </Button>
          </div>
        </div>
        <p className="mt-2 text-center text-[11px] tracking-wide text-muted-foreground">
          Cite Mind can make mistakes. Verify important information.
        </p>
      </div>
    </div>
  )
}

function Placeholder({
  section,
  conversations,
}: {
  section: Exclude<Section, "chat">
  conversations: Conversation[]
}) {
  const content = {
    library: [
      "Library",
      "Keep your sources close",
      "Upload, organize, and return to the papers shaping your work.",
    ],
    projects: [
      "Projects",
      "Structure your research",
      "Group conversations and source material around a focused question.",
    ],
    history: [
      "History",
      "Pick up where you left off",
      `${conversations.length} conversation${conversations.length === 1 ? "" : "s"} in this workspace.`,
    ],
    settings: [
      "Settings",
      "Tune your workspace",
      "Manage model providers and research preferences.",
    ],
    account: [
      "Account",
      "Your local profile",
      "Manage your profile and workspace preferences.",
    ],
  }[section]
  return (
    <ScrollArea className="min-h-0 flex-1">
      <div className="mx-auto w-full max-w-5xl px-5 py-8 md:px-8 md:py-12">
        <div className="max-w-xl">
          <p className="text-[10px] font-semibold tracking-[0.2em] text-primary uppercase">
            {content[0]}
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em] md:text-4xl">
            {content[1]}
          </h2>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            {content[2]}
          </p>
        </div>
        <Card className="mt-7 gap-0 py-0 shadow-xs">
          <CardContent className="p-0">
            <div className="flex flex-col items-center px-6 py-14 text-center">
              <div className="flex size-12 items-center justify-center rounded-xl bg-muted text-primary">
                <RiSparkling2Line className="size-5" />
              </div>
              <h3 className="mt-4 text-sm font-semibold">Nothing here yet</h3>
              <p className="mt-1 max-w-sm text-xs leading-5 text-muted-foreground">
                Your workspace activity will appear here when it is available.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  )
}

function Logo() {
  return (
    <div className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-[0_8px_18px_-10px_var(--primary)]">
      <RiStackLine className="size-4" />
    </div>
  )
}

function AttachmentChip({
  name,
  onRemove,
}: {
  name: string
  onRemove?: () => void
}) {
  return (
    <div className="flex max-w-[85%] items-center gap-2 rounded-lg border bg-muted/70 px-2.5 py-1.5 text-[11px] text-muted-foreground">
      {name.endsWith(".pdf") ? (
        <RiFilePdfLine className="size-3.5" />
      ) : (
        <RiFileTextLine className="size-3.5" />
      )}
      <span className="truncate">{name}</span>
      {onRemove && (
        <button
          onClick={onRemove}
          aria-label={`Remove ${name}`}
          className="transition-colors hover:text-foreground"
        >
          <RiCloseLine className="size-3.5" />
        </button>
      )}
    </div>
  )
}

function SidebarLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="mb-1.5 px-2.5 text-[10px] font-semibold tracking-[0.18em] text-muted-foreground uppercase">
      {children}
    </h3>
  )
}

function SidebarNavButton({
  icon: Icon,
  label,
  active,
  onClick,
}: {
  icon: typeof RiSettings3Line
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px] font-semibold text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring/40 focus-visible:outline-none",
        active && "bg-sidebar-accent text-sidebar-accent-foreground"
      )}
    >
      <Icon className="size-4" />
      {label}
    </button>
  )
}

function sectionLabel(section: Section) {
  return section === "chat"
    ? "Untitled research"
    : section[0].toUpperCase() + section.slice(1)
}
