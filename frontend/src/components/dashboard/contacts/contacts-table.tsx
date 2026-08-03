"use client";

import { useState } from "react";
import { format } from "date-fns";
import { 
  Building2, 
  Mail, 
  Linkedin, 
  Phone, 
  Globe, 
  Link as LinkIcon, 
  Search, 
  Filter,
  RefreshCw,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Eye
} from "lucide-react";
import { useContacts } from "@/hooks/use-contacts";
import { ContactRead, ContactRoleCategory } from "@/types/contact";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const getMethodIcon = (type: string) => {
  switch (type) {
    case "email": return <Mail className="h-4 w-4" />;
    case "linkedin": return <Linkedin className="h-4 w-4" />;
    case "phone": return <Phone className="h-4 w-4" />;
    case "website": return <Globe className="h-4 w-4" />;
    case "source_page": return <LinkIcon className="h-4 w-4" />;
    default: return <LinkIcon className="h-4 w-4" />;
  }
};

const getRoleCategoryBadge = (category: string) => {
  switch (category) {
    case "hr": return <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/20">HR</Badge>;
    case "recruiter": return <Badge variant="outline" className="bg-green-500/10 text-green-400 border-green-500/20">Recruiter</Badge>;
    case "hiring_manager": return <Badge variant="outline" className="bg-purple-500/10 text-purple-400 border-purple-500/20">Hiring Manager</Badge>;
    case "engineering_manager": return <Badge variant="outline" className="bg-orange-500/10 text-orange-400 border-orange-500/20">Eng Manager</Badge>;
    default: return <Badge variant="outline" className="bg-zinc-500/10 text-zinc-400 border-zinc-500/20">Other</Badge>;
  }
};

export function ContactsTable() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [roleCategory, setRoleCategory] = useState<ContactRoleCategory | "all">("all");
  const [selectedContact, setSelectedContact] = useState<ContactRead | null>(null);

  const { data, isLoading, isError, refetch, isRefetching } = useContacts({
    page,
    page_size: 10,
    search: debouncedSearch || undefined,
    role_category: roleCategory === "all" ? undefined : roleCategory,
  });

  // Simple debounce for search
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
    const timeoutId = setTimeout(() => {
      setDebouncedSearch(e.target.value);
      setPage(1);
    }, 500);
    return () => clearTimeout(timeoutId);
  };

  const handleRoleChange = (value: string) => {
    setRoleCategory(value as ContactRoleCategory | "all");
    setPage(1);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
        <div className="flex flex-1 items-center gap-2 w-full sm:max-w-md relative">
          <Search className="absolute left-3 h-4 w-4 text-zinc-500" />
          <Input
            placeholder="Search contacts..."
            value={search}
            onChange={handleSearchChange}
            className="pl-9 bg-zinc-950 border-zinc-800 text-white placeholder:text-zinc-500 focus-visible:ring-zinc-700"
          />
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Select value={roleCategory} onValueChange={handleRoleChange}>
            <SelectTrigger className="w-[180px] bg-zinc-950 border-zinc-800 text-white">
              <Filter className="mr-2 h-4 w-4 text-zinc-500" />
              <SelectValue placeholder="Filter by role" />
            </SelectTrigger>
            <SelectContent className="bg-zinc-950 border-zinc-800 text-white">
              <SelectItem value="all">All Roles</SelectItem>
              <SelectItem value="hr">HR</SelectItem>
              <SelectItem value="recruiter">Recruiter</SelectItem>
              <SelectItem value="hiring_manager">Hiring Manager</SelectItem>
              <SelectItem value="engineering_manager">Eng Manager</SelectItem>
              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="icon"
            onClick={() => refetch()}
            disabled={isRefetching}
            className="border-zinc-800 bg-zinc-950 text-zinc-300 hover:text-white hover:bg-zinc-800"
          >
            <RefreshCw className={`h-4 w-4 ${isRefetching ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      <div className="rounded-md border border-zinc-800 overflow-hidden">
        <Table>
          <TableHeader className="bg-zinc-900/50">
            <TableRow className="border-zinc-800 hover:bg-transparent">
              <TableHead className="text-zinc-400">Name / Role</TableHead>
              <TableHead className="text-zinc-400">Company</TableHead>
              <TableHead className="text-zinc-400">Category</TableHead>
              <TableHead className="text-zinc-400">Methods</TableHead>
              <TableHead className="text-zinc-400">Added</TableHead>
              <TableHead className="w-12"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
                <TableCell colSpan={6} className="h-32 text-center">
                  <Loader2 className="mx-auto h-6 w-6 animate-spin text-zinc-500" />
                </TableCell>
              </TableRow>
            ) : isError ? (
              <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
                <TableCell colSpan={6} className="h-32 text-center text-red-400">
                  Failed to load contacts. Please try again.
                </TableCell>
              </TableRow>
            ) : !data || data.items.length === 0 ? (
              <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
                <TableCell colSpan={6} className="h-32 text-center text-zinc-500">
                  No contacts found.
                </TableCell>
              </TableRow>
            ) : (
              data.items.map((contact: ContactRead) => (
                <TableRow key={contact.id} className="border-zinc-800 hover:bg-zinc-900/50">
                  <TableCell>
                    <div className="font-medium text-white">{contact.name}</div>
                    <div className="text-sm text-zinc-500 line-clamp-1">{contact.role}</div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-zinc-500" />
                      <span className="text-zinc-300">{contact.company_name}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    {getRoleCategoryBadge(contact.role_category)}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {contact.contact_methods.map((method, idx) => (
                        <a
                          key={idx}
                          href={method.type === 'email' ? `mailto:${method.value}` : method.value.startsWith('http') ? method.value : '#'}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center justify-center bg-zinc-800/50 hover:bg-zinc-700 h-6 w-6 rounded text-zinc-300 transition-colors"
                          title={method.value}
                        >
                          {getMethodIcon(method.type)}
                        </a>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-zinc-500 text-sm whitespace-nowrap">
                    {format(new Date(contact.created_at), "MMM d, yyyy")}
                  </TableCell>
                  <TableCell>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-8 w-8 text-zinc-400 hover:text-white hover:bg-zinc-800"
                      onClick={() => setSelectedContact(contact)}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {data && data.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-zinc-500">
            Showing {((page - 1) * data.page_size) + 1} to {Math.min(page * data.page_size, data.total)} of {data.total} contacts
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || isLoading}
              className="border-zinc-800 bg-zinc-950 text-white hover:bg-zinc-800"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <div className="text-sm text-zinc-400 px-2">
              Page {page} of {data.pages}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
              disabled={page === data.pages || isLoading}
              className="border-zinc-800 bg-zinc-950 text-white hover:bg-zinc-800"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      <Dialog open={!!selectedContact} onOpenChange={(open) => !open && setSelectedContact(null)}>
        <DialogContent className="bg-zinc-950 border-zinc-800 text-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Contact Details</DialogTitle>
          </DialogHeader>
          {selectedContact && (
            <div className="space-y-6 pt-4">
              <div>
                <h3 className="text-xl font-semibold">{selectedContact.name}</h3>
                <p className="text-zinc-400">{selectedContact.role} at {selectedContact.company_name}</p>
                <div className="mt-2">{getRoleCategoryBadge(selectedContact.role_category)}</div>
              </div>
              
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-zinc-500">Contact Methods</h4>
                <div className="space-y-2">
                  {selectedContact.contact_methods.map((method, idx) => (
                    <div key={idx} className="flex items-center gap-3 bg-zinc-900 p-3 rounded-md border border-zinc-800/50">
                      <div className="text-zinc-400">{getMethodIcon(method.type)}</div>
                      <div className="flex-1 overflow-hidden">
                        <p className="text-xs text-zinc-500 uppercase tracking-wider mb-0.5">{method.type}</p>
                        <a 
                          href={method.type === 'email' ? `mailto:${method.value}` : method.value.startsWith('http') ? method.value : '#'}
                          target="_blank"
                          rel="noreferrer"
                          className="text-sm text-zinc-200 hover:text-white hover:underline truncate block"
                        >
                          {method.value}
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {selectedContact.source_url && (
                <div className="space-y-1">
                  <h4 className="text-sm font-medium text-zinc-500">Source</h4>
                  <a href={selectedContact.source_url} target="_blank" rel="noreferrer" className="text-sm text-blue-400 hover:underline break-all">
                    {selectedContact.source_url}
                  </a>
                </div>
              )}

              {selectedContact.notes && (
                <div className="space-y-1">
                  <h4 className="text-sm font-medium text-zinc-500">Notes</h4>
                  <p className="text-sm text-zinc-300">{selectedContact.notes}</p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
