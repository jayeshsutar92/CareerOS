"use client"

import { Template } from "@/lib/api/templates"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"

interface TemplatePreviewProps {
  template: Template | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onUseTemplate?: (template: Template) => void
}

export function TemplatePreview({ template, open, onOpenChange, onUseTemplate }: TemplatePreviewProps) {
  if (!template) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>{template.name}</DialogTitle>
          <DialogDescription>
            Preview of the email template.
          </DialogDescription>
        </DialogHeader>
        
        <div className="flex flex-col space-y-4 py-4">
          <div className="space-y-1">
            <h4 className="text-sm font-medium text-muted-foreground">Subject</h4>
            <div className="rounded-md bg-muted p-3 text-sm">
              {template.subject}
            </div>
          </div>
          
          <div className="space-y-1">
            <h4 className="text-sm font-medium text-muted-foreground">Body</h4>
            <ScrollArea className="h-[300px] w-full rounded-md border p-4">
              <div className="whitespace-pre-wrap text-sm">
                {template.body}
              </div>
            </ScrollArea>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          {onUseTemplate && (
            <Button onClick={() => {
              onUseTemplate(template)
              onOpenChange(false)
            }}>
              Select Template
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
