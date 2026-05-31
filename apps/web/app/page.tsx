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
        <header className="flex h-[68px] shrink-0 items-center justify-between border-b bg-background/80 px-4 backdrop-blur-xl md:px-7">
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
            <div className="text-base font-bold tracking-tight">Cite Mind</div>
            <div className="text-[10px] font-medium tracking-[0.18em] text-muted-foreground uppercase">
              Research copilot
            </div>
          </div>
        </div>
        <Button
          onClick={onNewChat}
          className="h-11 w-full justify-start gap-2 rounded-lg px-3 text-[15px] font-semibold shadow-sm"
        >
          <RiAddLine /> Start new research
        </Button>
      </div>
      <ScrollArea className="min-h-0 flex-1 px-3">
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
                    "flex w-full items-center gap-2.5 truncate rounded-md px-2.5 py-2 text-left text-[13px] font-medium text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
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
      <ScrollArea className="min-h-0 flex-1">
        <div className="mx-auto w-full max-w-[860px] space-y-8 px-4 py-8 md:px-6 md:py-10">
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
    <section className="relative pt-3 md:pt-10">
      <div className="pointer-events-none absolute -top-24 right-0 h-72 w-72 rounded-full bg-primary/8 blur-3xl" />
      <div className="relative max-w-2xl">
        <Badge
          variant="secondary"
          className="mb-5 h-7 gap-1.5 rounded-full border border-primary/10 bg-primary/8 px-3 text-[10px] tracking-[0.16em] text-primary uppercase shadow-xs"
        >
          <RiSparkling2Line className="size-3" /> Academic research assistant
        </Badge>
        <h2 className="max-w-2xl text-[2.9rem] leading-[0.96] font-bold tracking-[-0.07em] md:text-[5rem]">
          Research with
          <span className="block bg-gradient-to-r from-primary to-primary/65 bg-clip-text text-transparent">
            a clearer mind.
          </span>
        </h2>
        <p className="mt-5 max-w-2xl text-base leading-7 font-medium text-muted-foreground md:text-lg md:leading-8">
          Bring your sources together, surface the strongest evidence, and turn
          complex material into work you can trust.
        </p>
      </div>
      <div className="mt-9 flex items-center gap-3">
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
                "group relative overflow-hidden rounded-2xl border bg-card/80 p-4 text-left shadow-xs transition-all hover:-translate-y-1 hover:border-primary/35 hover:shadow-lg",
                index === 0 && "md:col-span-1"
              )}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex size-9 items-center justify-center rounded-xl border border-primary/10 bg-primary/8 text-primary">
                  <Icon className="size-4" />
                </div>
                <RiArrowRightLine className="mt-2 size-4 text-muted-foreground transition-all group-hover:translate-x-1 group-hover:text-primary" />
              </div>
              <p className="mt-8 text-[10px] font-semibold tracking-[0.15em] text-primary uppercase">
                {meta}
              </p>
              <h3 className="mt-2 text-base font-bold">{title}</h3>
              <p className="mt-1 text-sm leading-5 text-muted-foreground">
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
    <div className="pointer-events-none shrink-0 bg-gradient-to-t from-background via-background/95 to-transparent px-4 pt-4 pb-4 md:px-6 md:pt-5 md:pb-6">
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
        <div className="rounded-[1.35rem] border bg-card/95 p-2 shadow-[0_18px_55px_-20px_color-mix(in_oklch,var(--foreground),transparent_65%)] backdrop-blur-xl">
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
            className="min-h-16 resize-none border-0 bg-transparent px-2.5 py-2 text-base leading-7 font-medium shadow-none focus-visible:ring-0"
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
              <span className="hidden text-[10px] font-medium tracking-wide text-muted-foreground sm:inline">
                Add sources
              </span>
              <Separator orientation="vertical" className="mx-1 h-4" />
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
              className="rounded-xl shadow-sm transition-transform hover:scale-105"
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
        "flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px] font-semibold text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
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
