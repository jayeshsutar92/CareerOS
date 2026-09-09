"use client"

import { useEffect, useState } from "react"
import { api } from "@/services/api"
import { Loader2, CheckCircle, XCircle } from "lucide-react"

interface QueueProgressProps {
  taskId: string
  onComplete?: () => void
}

interface TaskProgress {
  total: number
  completed: number
  failed: number
  remaining: number
}

interface TaskStatusResponse {
  status: string
  error?: string
  result?: Record<string, unknown>
  progress?: TaskProgress
}

export function QueueProgress({ taskId, onComplete }: QueueProgressProps) {
  const [status, setStatus] = useState<TaskStatusResponse | null>(null)

  useEffect(() => {
    if (!taskId) return

    const interval = setInterval(async () => {
      try {
        const { data } = await api.get(`/tasks/${taskId}`)
        setStatus(data)
        
        if (data.status === "succeeded" || data.status === "failed") {
          clearInterval(interval)
          if (data.status === "succeeded") {
            onComplete?.()
          }
        }
      } catch (e) {
        console.error("Failed to poll task status", e)
      }
    }, 1500)

    return () => clearInterval(interval)
  }, [taskId, onComplete])

  if (!status) {
    return (
      <div className="flex items-center gap-2 text-zinc-400">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Initializing queue...</span>
      </div>
    )
  }

  const p = status.progress

  if (!p && status.status !== "succeeded" && status.status !== "failed") {
    return (
      <div className="flex items-center gap-2 text-zinc-400">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Processing ({status.status})...</span>
      </div>
    )
  }

  if (status.status === "succeeded") {
    const total = (status.result?.total as number) || (p ? p.total : 0)
    const failed = (status.result?.failed as number) || (p ? p.failed : 0)
    const completed = (status.result?.completed as number) || (p ? p.completed : 0)
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-green-400">
          <CheckCircle className="h-5 w-5" />
          <span className="font-medium">Queue Completed</span>
        </div>
        <div className="flex items-center gap-6 text-sm text-zinc-400">
          <div><span className="text-zinc-200">{completed}</span> Sent</div>
          {failed > 0 && <div><span className="text-red-400">{failed}</span> Failed</div>}
          <div><span className="text-zinc-200">{total}</span> Total</div>
        </div>
      </div>
    )
  }

  if (status.status === "failed") {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-red-400">
          <XCircle className="h-5 w-5" />
          <span className="font-medium">Queue Failed</span>
        </div>
        <div className="text-sm text-zinc-400">{status.error || "An unknown error occurred"}</div>
      </div>
    )
  }

  const progressPercent = p && p.total > 0 ? ((p.completed + p.failed) / p.total) * 100 : 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-zinc-300">
          <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
          <span>Sending Emails...</span>
        </div>
        {p && (
          <div className="text-sm font-mono text-zinc-400">
            {Math.round(progressPercent)}%
          </div>
        )}
      </div>

      <div className="h-2 w-full bg-zinc-800 rounded-full overflow-hidden">
        <div 
          className="h-full bg-blue-500 transition-all duration-500 ease-in-out" 
          style={{ width: `${progressPercent}%` }} 
        />
      </div>

      {p && (
        <div className="grid grid-cols-4 gap-4 pt-2 border-t border-zinc-800/50">
          <div className="flex flex-col">
            <span className="text-xs text-zinc-500 uppercase">Total</span>
            <span className="font-medium text-zinc-200">{p.total}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-zinc-500 uppercase">Completed</span>
            <span className="font-medium text-green-400">{p.completed}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-zinc-500 uppercase">Remaining</span>
            <span className="font-medium text-blue-400">{p.remaining}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-zinc-500 uppercase">Failed</span>
            <span className="font-medium text-red-400">{p.failed}</span>
          </div>
        </div>
      )}
    </div>
  )
}
