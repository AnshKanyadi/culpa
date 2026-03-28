import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Key, Plus, Trash2, Copy, Check, ArrowLeft, AlertTriangle } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { cn } from '../lib/utils'

interface ApiKey {
  id: string
  key_prefix: string
  name: string
  created_at: string
  last_used_at?: string
  revoked_at?: string
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    toast.success('Copied to clipboard')
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={copy}
      className="flex items-center gap-1.5 text-xs text-culpa-text-dim hover:text-culpa-text transition-colors"
    >
      {copied ? <Check size={12} className="text-culpa-green" /> : <Copy size={12} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

function NewKeyModal({
  fullKey,
  onClose,
}: {
  fullKey: string
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-culpa-surface border border-culpa-border rounded-2xl p-6 w-full max-w-md">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-culpa-green/15 border border-culpa-green/30 flex items-center justify-center">
            <Key size={14} className="text-culpa-green" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-culpa-text">API key created</h3>
            <p className="text-xs text-culpa-text-dim">Copy it now — this is the only time you'll see it.</p>
          </div>
        </div>

        <div className="bg-culpa-bg border border-culpa-border rounded-lg p-3 mb-4">
          <div className="flex items-center justify-between gap-2">
            <code className="text-xs font-mono text-culpa-green break-all">{fullKey}</code>
            <CopyButton text={fullKey} />
          </div>
        </div>

        <div className="flex items-start gap-2 mb-5 bg-culpa-orange-dim border border-culpa-orange/20 rounded-lg px-3 py-2.5">
          <AlertTriangle size={12} className="text-culpa-orange mt-0.5 shrink-0" />
          <p className="text-xs text-culpa-orange">
            Store this somewhere safe. For security reasons, we don't store the full key — it won't be shown again.
          </p>
        </div>

        <button
          onClick={onClose}
          className="w-full py-2.5 bg-culpa-muted hover:bg-culpa-border text-culpa-text text-sm font-medium
                     rounded-lg transition-colors"
        >
          Done
        </button>
      </div>
    </div>
  )
}

function CreateKeyForm({ onCreated }: { onCreated: (key: string) => void }) {
  const [name, setName] = useState('')
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: () => api.auth.createKey(name || 'Default'),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      onCreated(data.key)
      setName('')
    },
  })

  return (
    <div className="flex items-center gap-2">
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Key name (optional)"
        className="flex-1 px-3 py-2 bg-culpa-bg border border-culpa-border rounded-lg
                   text-sm text-culpa-text placeholder:text-culpa-text-dim
                   focus:outline-none focus:ring-2 focus:ring-culpa-red/30 focus:border-culpa-red/50
                   transition-colors"
        onKeyDown={(e) => e.key === 'Enter' && mutation.mutate()}
      />
      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="flex items-center gap-1.5 px-3 py-2 bg-culpa-red hover:bg-culpa-red/80
                   text-white text-sm font-medium rounded-lg transition-colors
                   disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
      >
        <Plus size={14} />
        {mutation.isPending ? 'Creating...' : 'Create key'}
      </button>
    </div>
  )
}

export function ApiKeys() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [newKey, setNewKey] = useState<string | null>(null)
  const [confirmingRevoke, setConfirmingRevoke] = useState<string | null>(null)
  const revokeTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => api.auth.listKeys(),
  })

  const revokeMutation = useMutation({
    mutationFn: (keyId: string) => api.auth.revokeKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      toast.success('API key revoked')
    },
  })

  const activeKeys = data?.keys?.filter((k: ApiKey) => !k.revoked_at) ?? []

  return (
    <div className="min-h-screen bg-culpa-bg">
      <div className="border-b border-culpa-border bg-culpa-surface">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="text-culpa-text-dim hover:text-culpa-text transition-colors"
            >
              <ArrowLeft size={16} />
            </Link>
            <div>
              <h1 className="text-sm font-semibold text-culpa-text">API Keys</h1>
              <p className="text-xs text-culpa-text-dim">{user?.email}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h2 className="text-xs font-semibold text-culpa-text-dim uppercase tracking-wider mb-3">
            SDK usage
          </h2>
          <div className="bg-culpa-surface border border-culpa-border rounded-xl p-4">
            <pre className="text-xs font-mono text-culpa-blue leading-relaxed">{`export CULPA_API_KEY=culpa_xxxxxxxxxxxx

# or pass directly
culpa.init(api_key="culpa_xxxxxxxxxxxx")`}</pre>
          </div>
        </div>

        <div className="mb-8">
          <h2 className="text-xs font-semibold text-culpa-text-dim uppercase tracking-wider mb-3">
            Create new key
          </h2>
          <CreateKeyForm onCreated={(key) => setNewKey(key)} />
        </div>

        <div>
          <h2 className="text-xs font-semibold text-culpa-text-dim uppercase tracking-wider mb-3">
            Active keys
          </h2>

          {isLoading && (
            <div className="text-sm text-culpa-text-dim py-6 text-center">Loading...</div>
          )}

          {!isLoading && activeKeys.length === 0 && (
            <div className="text-sm text-culpa-text-dim py-8 text-center border border-culpa-border rounded-xl border-dashed">
              No API keys yet. Create one above to start uploading sessions.
            </div>
          )}

          {activeKeys.length > 0 && (
            <div className="space-y-2">
              {activeKeys.map((key: ApiKey) => (
                <div
                  key={key.id}
                  className="bg-culpa-surface border border-culpa-border rounded-xl px-4 py-3
                             flex items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Key size={14} className="text-culpa-text-dim shrink-0" />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-culpa-text">{key.name}</span>
                        <code className="text-xs font-mono text-culpa-text-dim">{key.key_prefix}...</code>
                      </div>
                      <div className="text-xs text-culpa-text-dim mt-0.5">
                        Created {new Date(key.created_at).toLocaleDateString()}
                        {key.last_used_at && (
                          <> · Last used {new Date(key.last_used_at).toLocaleDateString()}</>
                        )}
                        {!key.last_used_at && <> · Never used</>}
                      </div>
                    </div>
                  </div>

                  {confirmingRevoke === key.id ? (
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        onClick={() => {
                          revokeMutation.mutate(key.id)
                          setConfirmingRevoke(null)
                          if (revokeTimerRef.current) clearTimeout(revokeTimerRef.current)
                        }}
                        className="px-2.5 py-1 rounded-lg bg-culpa-red text-white text-xs font-medium
                                   hover:bg-culpa-red/80 transition-colors"
                      >
                        Confirm revoke
                      </button>
                      <button
                        onClick={() => {
                          setConfirmingRevoke(null)
                          if (revokeTimerRef.current) clearTimeout(revokeTimerRef.current)
                        }}
                        className="px-2 py-1 rounded-lg text-xs text-culpa-text-dim hover:text-culpa-text transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => {
                        setConfirmingRevoke(key.id)
                        if (revokeTimerRef.current) clearTimeout(revokeTimerRef.current)
                        revokeTimerRef.current = setTimeout(() => setConfirmingRevoke(null), 5000)
                      }}
                      className={cn(
                        'p-2 rounded-lg text-culpa-text-dim hover:text-culpa-red hover:bg-culpa-red-dim',
                        'transition-colors shrink-0',
                      )}
                      title="Revoke key"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {newKey && (
        <NewKeyModal fullKey={newKey} onClose={() => setNewKey(null)} />
      )}
    </div>
  )
}
