"use client"

import { useEffect, useState } from "react"
import { Template, templatesApi } from "@/lib/api/templates"
import { TemplateList } from "@/components/templates/template-list"
import { TemplatePreview } from "@/components/templates/template-preview"
import { Button } from "@/components/ui/button"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [previewTemplate, setPreviewTemplate] = useState<Template | null>(null)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | undefined>()

  const loadTemplates = async () => {
    try {
      const data = await templatesApi.list()
      setTemplates(data)
    } catch (error) {
      console.error("Failed to load templates:", error)
      toast.error("Failed to load templates")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      void loadTemplates()
    }, 0)
    return () => clearTimeout(timer)
  }, [])

  const handleRefresh = () => {
    setIsLoading(true)
    void loadTemplates()
  }

  const handleSelectForPreview = (template: Template) => {
    setPreviewTemplate(template)
    setPreviewOpen(true)
  }

  const handleUseTemplate = (template: Template) => {
    setSelectedTemplateId(template.id)
    toast.success(`Selected template: ${template.name}`)
  }

  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Templates</h2>
        <div className="flex items-center space-x-2">
          <Button onClick={handleRefresh} variant="outline" size="sm">
            Refresh
          </Button>
        </div>
      </div>
      
      <p className="text-muted-foreground mb-6">
        Manage and preview your email templates for outreach.
      </p>

      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <TemplateList 
          templates={templates} 
          onSelectTemplate={handleSelectForPreview} 
          selectedTemplateId={selectedTemplateId}
        />
      )}

      <TemplatePreview 
        template={previewTemplate} 
        open={previewOpen} 
        onOpenChange={setPreviewOpen}
        onUseTemplate={handleUseTemplate}
      />
    </div>
  )
}
