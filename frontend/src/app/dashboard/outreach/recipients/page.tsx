"use client"

import { Users, Send } from "lucide-react"
import { PageHeader } from "@/components/dashboard/page-header"
import { ContactsTable } from "@/components/dashboard/contacts/contacts-table"
import { useOutreachStore } from "@/store/outreach"
import { Button } from "@/components/ui/button"
import { useRouter } from "next/navigation"
import { toast } from "sonner"

export default function RecipientSelectionPage() {
  const router = useRouter()
  const { selectedRecipientIds, toggleRecipient, selectAllRecipients, deselectAllRecipients } = useOutreachStore()

  const handleProceed = () => {
    if (selectedRecipientIds.length === 0) {
      toast.error("Please select at least one recipient to proceed.")
      return
    }
    router.push("/dashboard/outreach/compose")
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <PageHeader
          title="Recipient Selection"
          description="Select contacts from your discovered list to add them to this outreach campaign."
          icon={Users}
          breadcrumbs={[
            { label: "Dashboard", href: "/dashboard" },
            { label: "Outreach" },
            { label: "Recipients" },
          ]}
        />
        
        <div className="flex items-center gap-3">
          <div className="text-sm font-medium bg-zinc-900 border border-zinc-800 px-3 py-1.5 rounded-md text-zinc-300">
            <span className="text-white">{selectedRecipientIds.length}</span> Selected
          </div>
          <Button onClick={handleProceed} className="gap-2">
            Proceed to Send
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="rounded-xl border border-zinc-800/50 bg-zinc-950/50 p-6 shadow-sm">
        <ContactsTable
          selectionMode={true}
          selectedIds={selectedRecipientIds}
          onSelect={toggleRecipient}
          onSelectAll={(ids, isSelected) => {
            if (isSelected) {
              selectAllRecipients(ids)
            } else {
              // Only deselect if they are clicking deselect. If they want to deselect ALL, they use deselectAllRecipients.
              // To handle page-level deselection correctly, we should remove the current page's ids.
              // For simplicity in this phase, if they uncheck "select all", we just clear all.
              deselectAllRecipients()
            }
          }}
        />
      </div>
    </div>
  )
}
