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
  RiMenuLine,
  RiSendPlane2Line,
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
  ["Summarize a paper", "Extract the argument, evidence, and limitations."],
  ["Compare sources", "Find where two papers agree and diverge."],
  ["Build a literature review", "Organize themes and identify research gaps."],
]

const libraryFiles = [
  ["neural_nets_v2.pdf", "PDF · 14 pages"],
  ["draft_thesis_intro.docx", "Document · edited today"],
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
    const parsed = stored ? (JSON.parse(stored) as Conversation[]) : []
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
    <div className="flex h-svh overflow-hidden bg-background text-foreground">
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

      <main className="relative flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center justify-between border-b bg-background/85 px-4 backdrop-blur-xl md:px-7">
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
              <h1 className="truncate text-base font-semibold tracking-tight md:text-lg">
                {section === "chat"
                  ? (active?.title ?? "Untitled research")
                  : sectionLabel(section)}
              </h1>
            </div>
          </div>
          <Badge
            variant="outline"
            className="gap-2 rounded-full bg-card px-2.5 py-1 text-[10px] tracking-[0.14em] text-muted-foreground uppercase"
          >
            <span className="size-1.5 rounded-full bg-success shadow-[0_0_0_3px_var(--success-soft)]" />
            <span className="hidden sm:inline">Systems online</span>
          </Badge>
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
            <div className="text-sm font-semibold tracking-tight">
              Cite Mind
            </div>
            <div className="text-[10px] font-medium tracking-[0.18em] text-muted-foreground uppercase">
              Research copilot
            </div>
          </div>
        </div>
        <Button
          onClick={onNewChat}
          className="h-10 w-full justify-start gap-2 rounded-lg px-3 text-sm shadow-sm"
        >
          <RiAddLine /> Start new research
        </Button>
      </div>
      <ScrollArea className="flex-1 px-3">
        <div className="space-y-6 pb-4">
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
          <div>
            <SidebarLabel>Recent</SidebarLabel>
            <div className="space-y-0.5">
              {conversations.slice(0, 5).map((conversation) => (
                <button
                  key={conversation.id}
                  onClick={() => onOpenChat(conversation.id)}
                  className={cn(
                    "flex w-full items-center gap-2.5 truncate rounded-md px-2.5 py-2 text-left text-xs text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
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
          <div>
            <SidebarLabel>Library</SidebarLabel>
            {libraryFiles.map(([label]) => (
              <SidebarFile
                key={label}
                icon={label.endsWith(".pdf") ? RiFilePdfLine : RiFileTextLine}
                label={label}
              />
            ))}
          </div>
        </div>
      </ScrollArea>
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
  return (
    <>
      <ScrollArea className="flex-1">
        <div className="mx-auto w-full max-w-[860px] space-y-8 px-4 py-8 pb-48 md:px-6 md:py-10">
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
    <section className="pt-5 md:pt-14">
      <div className="max-w-xl">
        <Badge
          variant="secondary"
          className="mb-5 h-6 gap-1.5 px-2.5 text-[10px] tracking-[0.15em] text-primary uppercase"
        >
          <RiSparkling2Line className="size-3" /> Academic research assistant
        </Badge>
        <h2 className="text-3xl font-semibold tracking-[-0.045em] md:text-5xl">
          Turn your sources into{" "}
          <span className="text-primary">clear thinking.</span>
        </h2>
        <p className="mt-4 max-w-lg text-sm leading-6 text-muted-foreground md:text-base">
          Ask a research question, attach a paper, or start with one of these
          workflows.
        </p>
      </div>
      <div className="mt-9 grid gap-3 md:grid-cols-3">
        {starterPrompts.map(([title, description]) => (
          <button
            key={title}
            onClick={() => onSelect(`${title}: `)}
            className="group rounded-xl border bg-card p-4 text-left shadow-xs transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md"
          >
            <div className="mb-7 flex size-8 items-center justify-center rounded-lg bg-primary/8 text-primary">
              <RiArrowRightLine className="size-4 transition-transform group-hover:translate-x-0.5" />
            </div>
            <h3 className="text-sm font-semibold">{title}</h3>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              {description}
            </p>
          </button>
        ))}
      </div>
      <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 border-t pt-4 text-[11px] font-medium tracking-[0.12em] text-muted-foreground uppercase">
        <span>Upload papers</span>
        <span>Citation-aware answers</span>
        <span>Private workspace</span>
      </div>
    </section>
  )
}

function UserMessage({ item }: { item: Message }) {
  return (
    <div className="flex flex-col items-end gap-2">
      <div className="max-w-[88%] rounded-2xl rounded-br-md bg-primary px-4 py-3 text-sm leading-6 text-primary-foreground shadow-sm">
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
            <span className="text-sm font-semibold">Cite Mind</span>
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
    <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-background via-background/95 to-transparent px-4 pt-12 pb-4 md:px-6 md:pb-6">
      <div className="pointer-events-auto mx-auto max-w-[860px]">
        {files.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {files.map((file) => (
              <AttachmentChip
                key={file.name}
                name={file.name}
                onRemove={() => onFiles(files.filter((item) => item !== file))}
              />
            ))}
          </div>
        )}
        <div className="rounded-2xl border bg-card p-2 shadow-[0_12px_40px_-18px_color-mix(in_oklch,var(--foreground),transparent_70%)]">
          <Textarea
            value={message}
            onChange={(event) => onMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault()
                onSend()
              }
            }}
            placeholder="Ask a research question..."
            className="min-h-14 resize-none border-0 bg-transparent px-2.5 py-2 text-sm leading-6 shadow-none focus-visible:ring-0 md:text-sm"
          />
          <div className="flex items-center justify-between gap-2 border-t px-0.5 pt-2">
            <div className="flex min-w-0 items-center gap-1">
              <input
                ref={fileInput}
                type="file"
                accept=".pdf,.txt,.md"
                multiple
                hidden
                onChange={(event) =>
                  onFiles([...files, ...Array.from(event.target.files ?? [])])
                }
              />
              <Button
                variant="ghost"
                size="icon"
                onClick={() => fileInput.current?.click()}
                aria-label="Attach files"
                className="text-muted-foreground"
              >
                <RiAttachment2 />
              </Button>
              <Select value={provider} onValueChange={onProvider}>
                <SelectTrigger className="max-w-[150px] border-0 bg-transparent px-1.5 text-[11px] text-muted-foreground shadow-none">
                  <RiEqualizerLine />
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
              size="icon-lg"
              disabled={pending || !message.trim()}
              onClick={onSend}
              className="rounded-xl shadow-sm"
            >
              <RiSendPlane2Line />
            </Button>
          </div>
        </div>
        <p className="mt-2.5 text-center text-[10px] tracking-wide text-muted-foreground">
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
      `${conversations.length} browser-local conversation${conversations.length === 1 ? "" : "s"} saved in this workspace.`,
    ],
    settings: [
      "Settings",
      "Tune your workspace",
      "Manage model providers and research preferences.",
    ],
    account: [
      "Account",
      "Your local profile",
      "Account sync is not enabled in this local-first version.",
    ],
  }[section]
  return (
    <ScrollArea className="flex-1">
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
        <div className="mt-9 grid gap-3 md:grid-cols-3">
          <StatCard
            label="Saved sources"
            value={section === "library" ? "02" : "—"}
            detail="Local workspace"
          />
          <StatCard
            label="Research threads"
            value={String(conversations.length).padStart(2, "0")}
            detail="Browser-local"
          />
          <StatCard
            label="Workspace mode"
            value="Local"
            detail="Private by default"
          />
        </div>
        <Card className="mt-7 gap-0 py-0 shadow-xs">
          <CardContent className="p-0">
            {section === "library" ? (
              libraryFiles.map(([name, meta], index) => (
                <div
                  key={name}
                  className={cn(
                    "flex items-center gap-3 px-4 py-4",
                    index > 0 && "border-t"
                  )}
                >
                  <div className="flex size-9 items-center justify-center rounded-lg bg-muted text-primary">
                    {name.endsWith(".pdf") ? (
                      <RiFilePdfLine className="size-4" />
                    ) : (
                      <RiFileTextLine className="size-4" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{name}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {meta}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Open ${name}`}
                  >
                    <RiArrowRightLine />
                  </Button>
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center px-6 py-14 text-center">
                <div className="flex size-12 items-center justify-center rounded-xl bg-muted text-primary">
                  <RiSparkling2Line className="size-5" />
                </div>
                <h3 className="mt-4 text-sm font-semibold">
                  This space is ready for your work
                </h3>
                <p className="mt-1 max-w-sm text-xs leading-5 text-muted-foreground">
                  The foundation is in place. Start a research conversation to
                  add activity.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  )
}

function StatCard({
  label,
  value,
  detail,
}: {
  label: string
  value: string
  detail: string
}) {
  return (
    <Card className="gap-1 py-4 shadow-xs">
      <CardContent>
        <p className="text-[10px] font-semibold tracking-[0.16em] text-muted-foreground uppercase">
          {label}
        </p>
        <p className="mt-3 text-2xl font-semibold tracking-tight">{value}</p>
        <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
      </CardContent>
    </Card>
  )
}

function Logo() {
  return (
    <div className="flex size-9 items-center justify-center rounded-xl bg-primary text-xs font-bold tracking-tight text-primary-foreground shadow-sm">
      CM
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

function SidebarFile({
  icon: Icon,
  label,
}: {
  icon: typeof RiFilePdfLine
  label: string
}) {
  return (
    <div className="flex items-center gap-2.5 px-2.5 py-1.5 text-xs text-sidebar-foreground/65">
      <Icon className="size-3.5 shrink-0" />
      <span className="truncate">{label}</span>
    </div>
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
        "flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-xs font-medium text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
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
