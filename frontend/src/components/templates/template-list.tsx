"use client"

import { Template } from "@/lib/api/templates"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface TemplateListProps {
  templates: Template[]
  onSelectTemplate: (template: Template) => void
  selectedTemplateId?: string
}

export function TemplateList({ templates, onSelectTemplate, selectedTemplateId }: TemplateListProps) {
  if (templates.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center rounded-md border border-dashed">
        <p className="text-sm text-muted-foreground">No templates available.</p>
      </div>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {templates.map((template) => (
        <Card 
          key={template.id} 
          className={`cursor-pointer transition-colors hover:bg-muted/50 ${selectedTemplateId === template.id ? "ring-2 ring-primary" : ""}`}
          onClick={() => onSelectTemplate(template)}
        >
          <CardHeader>
            <CardTitle className="line-clamp-1">{template.name}</CardTitle>
            <CardDescription className="line-clamp-2" title={template.subject}>
              {template.subject}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="line-clamp-3 text-sm text-muted-foreground">
              {template.body}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
