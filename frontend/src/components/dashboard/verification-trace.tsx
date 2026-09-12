import React, { useState } from "react";
import { ChevronDown, ChevronRight, ShieldCheck, ShieldAlert, CheckCircle2, XCircle } from "lucide-react";
import { ResolutionEvidence } from "@/services/lead-discovery";

interface Props {
  evidence: ResolutionEvidence;
}

export function VerificationTrace({ evidence }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  
  if (!evidence) return null;
  
  const summary = evidence.verification_summary;
  const isVerified = summary?.overall_status === "VERIFIED";

  return (
    <div className="mt-3 border border-zinc-800 rounded-md bg-zinc-950/50 overflow-hidden text-xs">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-2 hover:bg-zinc-900 transition-colors"
      >
        <div className="flex items-center gap-2">
          {isOpen ? <ChevronDown className="h-4 w-4 text-zinc-400" /> : <ChevronRight className="h-4 w-4 text-zinc-400" />}
          <span className="font-medium text-zinc-300 flex items-center gap-1.5">
            {isVerified ? <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" /> : <ShieldAlert className="h-3.5 w-3.5 text-amber-500" />}
            Verification Trace
          </span>
        </div>
        {summary && (
          <span className="text-zinc-500 font-mono">
            Confidence: {summary.overall_confidence}%
          </span>
        )}
      </button>
      
      {isOpen && (
        <div className="p-3 border-t border-zinc-800 space-y-4">
          
          {/* Rules Summary */}
          {summary?.results && summary.results.length > 0 && (
            <div className="space-y-1.5">
              <h5 className="text-zinc-400 font-medium mb-2">Engine Rules</h5>
              {summary.results.map((r, i) => (
                <div key={i} className="flex items-start gap-2 text-zinc-300">
                  {r.status === "PASS" ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 mt-0.5 shrink-0" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 text-red-500 mt-0.5 shrink-0" />
                  )}
                  <div>
                    <div className="flex gap-2 items-baseline">
                      <span className="font-medium capitalize">{r.entity_type.replace(/_/g, ' ')}</span>
                      <span className="text-[10px] text-zinc-500 font-mono">{r.confidence_score}%</span>
                    </div>
                    <p className="text-zinc-500">{r.evidence_summary}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {/* Socials */}
          {evidence.socials && Object.keys(evidence.socials).length > 0 && (
            <div className="space-y-1.5 pt-2 border-t border-zinc-800/50">
              <h5 className="text-zinc-400 font-medium">Social Profiles</h5>
              <div className="flex flex-wrap gap-2">
                {Object.entries(evidence.socials).map(([platform, url]) => (
                  <a 
                    key={platform} 
                    href={url as string} 
                    target="_blank" 
                    rel="noreferrer" 
                    className="px-2 py-1 bg-zinc-900 border border-zinc-800 rounded capitalize text-blue-400 hover:underline"
                  >
                    {platform}
                  </a>
                ))}
              </div>
            </div>
          )}
          
          {/* Careers Surfaces */}
          {evidence.careers_surfaces && evidence.careers_surfaces.length > 0 && (
            <div className="space-y-1.5 pt-2 border-t border-zinc-800/50">
              <h5 className="text-zinc-400 font-medium">Hiring Surfaces</h5>
              <ul className="space-y-1">
                {evidence.careers_surfaces.map((s, i) => (
                  <li key={i} className="flex justify-between items-center bg-zinc-900/50 px-2 py-1 rounded border border-zinc-800/50">
                    <a href={s.url} target="_blank" rel="noreferrer" className="text-blue-400 hover:underline truncate pr-2 max-w-[70%]">
                      {s.url}
                    </a>
                    <span className="text-zinc-500 capitalize shrink-0">{s.type.replace(/_/g, ' ')}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Extracted Artifacts */}
          {evidence.extracted_contacts && evidence.extracted_contacts.length > 0 && (
            <div className="space-y-1.5 pt-2 border-t border-zinc-800/50">
              <h5 className="text-zinc-400 font-medium">Extracted Contacts</h5>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {evidence.extracted_contacts.map((c, i) => (
                  <div key={i} className="bg-zinc-900 p-2 rounded border border-zinc-800/50">
                    <div className="font-medium text-zinc-300">{c.name}</div>
                    <div className="text-zinc-500 capitalize">{c.role_classification.replace(/_/g, ' ')}</div>
                    <div className="text-zinc-600 text-[10px] truncate mt-1">Src: {c.discovery_source}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
}
