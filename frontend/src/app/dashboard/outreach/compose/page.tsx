"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Send, LayoutTemplate, Users } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/dashboard/page-header"
import { useOutreachStore } from "@/store/outreach"
import { templatesApi, Template } from "@/lib/api/templates"
import { outreachApi } from "@/lib/api/outreach"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card"
import { QueueProgress } from "@/components/dashboard/outreach/queue-progress"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"

export default function ComposePage() {
  const router = useRouter()
  const { selectedRecipientIds } = useOutreachStore()
  
  const [templates, setTemplates] = useState<Template[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)

  useEffect(() => {
    if (selectedRecipientIds.length === 0) {
      toast.error("No recipients selected.")
      router.push("/dashboard/outreach/recipients")
      return
    }

    const fetchTemplates = async () => {
      try {
        const data = await templatesApi.list()
        setTemplates(data)
      } catch {
        toast.error("Failed to load templates")
      }
    }
    fetchTemplates()
  }, [selectedRecipientIds, router])

  const handleStartCampaign = async () => {
    if (!selectedTemplate) {
      toast.error("Please select a template first.")
      return
    }

    setIsSubmitting(true)
    try {
      const res = await outreachApi.sendBulkEmails({
        template_id: selectedTemplate.id,
        recipient_ids: selectedRecipientIds,
      })
      setTaskId(res.task_id)
      toast.success("Bulk email queue started!")
    } catch {
      toast.error("Failed to start email queue")
      setIsSubmitting(false)
    }
  }

  const handleCloseDialog = () => {
    // If they close the dialog, we might want to redirect them to the recipients page or reset
    setTaskId(null)
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <PageHeader
        title="Compose Campaign"
        description="Select a template for your selected recipients and start the email queue."
        icon={Send}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Outreach", href: "/dashboard/outreach/recipients" },
          { label: "Compose" },
        ]}
      />

      <div className="grid gap-6">
        <Card className="border-zinc-800 bg-zinc-950/50">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-blue-400" />
              <CardTitle>Recipients Selected</CardTitle>
            </div>
            <CardDescription>
              You have selected {selectedRecipientIds.length} recipients for this campaign.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <Button variant="outline" onClick={() => router.push("/dashboard/outreach/recipients")}>
                Change Recipients
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-950/50">
          <CardHeader>
            <div className="flex items-center gap-2">
              <LayoutTemplate className="h-5 w-5 text-purple-400" />
              <CardTitle>Select Template</CardTitle>
            </div>
            <CardDescription>
              Choose a template from your pre-defined list to send to these recipients.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2">
              {templates.map(template => (
                <div 
                  key={template.id} 
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    selectedTemplate?.id === template.id 
                      ? "border-purple-500 bg-purple-500/10" 
                      : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-600"
                  }`}
                  onClick={() => setSelectedTemplate(template)}
                >
                  <h3 className="font-medium text-white mb-1">{template.name}</h3>
                  <p className="text-sm text-zinc-400 truncate">{template.subject}</p>
                </div>
              ))}
            </div>

            {selectedTemplate && (
              <div className="mt-6 space-y-4 pt-6 border-t border-zinc-800">
                <div>
                  <div className="text-sm font-medium text-zinc-500 mb-1">Subject Preview</div>
                  <div className="text-white bg-zinc-900 p-3 rounded-md border border-zinc-800/50">
                    {selectedTemplate.subject}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium text-zinc-500 mb-1">Body Preview</div>
                  <ScrollArea className="h-48 w-full rounded-md border border-zinc-800/50 bg-zinc-900">
                    <div className="p-4 whitespace-pre-wrap text-sm text-zinc-300">
                      {selectedTemplate.body}
                    </div>
                  </ScrollArea>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="flex justify-end pt-4">
        <Button 
          size="lg" 
          onClick={handleStartCampaign} 
          disabled={!selectedTemplate || isSubmitting}
          className="bg-white text-zinc-950 hover:bg-zinc-200"
        >
          {isSubmitting ? "Starting..." : "Start Campaign"}
          {!isSubmitting && <Send className="ml-2 h-4 w-4" />}
        </Button>
      </div>

      <Dialog open={!!taskId} onOpenChange={(open) => !open && handleCloseDialog()}>
        <DialogContent className="bg-zinc-950 border-zinc-800 text-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Sending Emails</DialogTitle>
            <DialogDescription>
              Please wait while your campaign is being processed. You can safely close this dialog, but leaving it open shows live progress.
            </DialogDescription>
          </DialogHeader>
          
          <div className="pt-4">
            {taskId && <QueueProgress taskId={taskId} />}
          </div>
          
          <div className="flex justify-end pt-4">
            <Button variant="outline" onClick={handleCloseDialog} className="border-zinc-800 bg-zinc-900">
              Close Window
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
