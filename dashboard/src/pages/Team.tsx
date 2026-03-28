import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ArrowLeft, Users, Plus, Trash2, Mail, Crown, Shield } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { cn } from '../lib/utils'

interface Member {
  id: string
  email: string
  name?: string
  role: string
  joined_at: string
}

interface Invite {
  id: string
  email: string
  created_at: string
  team_name?: string
  team_id?: string
}

function RoleBadge({ role }: { role: string }) {
  if (role === 'owner') return (
    <span className="flex items-center gap-1 text-[10px] font-mono text-culpa-orange bg-culpa-orange-dim px-1.5 py-0.5 rounded">
      <Crown size={10} /> owner
    </span>
  )
  if (role === 'admin') return (
    <span className="flex items-center gap-1 text-[10px] font-mono text-culpa-purple bg-culpa-purple-dim px-1.5 py-0.5 rounded">
      <Shield size={10} /> admin
    </span>
  )
  return (
    <span className="text-[10px] font-mono text-culpa-text-dim bg-culpa-muted px-1.5 py-0.5 rounded">
      member
    </span>
  )
}

function CreateTeamForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState('')
  const mutation = useMutation({
    mutationFn: () => api.teams.create(name),
    onSuccess: () => {
      setName('')
      onCreated()
      toast.success('Team created')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="flex items-center gap-2">
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Team name"
        className="flex-1 px-3 py-2 bg-culpa-bg border border-culpa-border rounded-lg
                   text-sm text-culpa-text placeholder:text-culpa-text-dim
                   focus:outline-none focus:ring-2 focus:ring-culpa-red/30 focus:border-culpa-red/50"
        onKeyDown={(e) => e.key === 'Enter' && name.trim() && mutation.mutate()}
      />
      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending || !name.trim()}
        className="flex items-center gap-1.5 px-3 py-2 bg-culpa-red hover:bg-culpa-red/80 text-white text-sm
                   font-medium rounded-lg transition-colors disabled:opacity-50 whitespace-nowrap"
      >
        <Plus size={14} /> Create team
      </button>
    </div>
  )
}

function TeamDetail({ teamId }: { teamId: string }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [inviteEmail, setInviteEmail] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['team', teamId],
    queryFn: () => api.teams.get(teamId),
  })

  const inviteMutation = useMutation({
    mutationFn: () => api.teams.invite(teamId, inviteEmail),
    onSuccess: () => {
      setInviteEmail('')
      queryClient.invalidateQueries({ queryKey: ['team', teamId] })
      toast.success('Invite sent')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const removeMutation = useMutation({
    mutationFn: (userId: string) => api.teams.removeMember(teamId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team', teamId] })
      toast.success('Member removed')
    },
  })

  if (isLoading) return <div className="text-sm text-culpa-text-dim py-6 text-center">Loading...</div>
  if (!data) return null

  const team = data.team as { name: string; owner_id: string }
  const members = data.members as Member[]
  const invites = data.pending_invites as Invite[]
  const isOwnerOrAdmin = members.some(
    (m) => m.id === user?.id && (m.role === 'owner' || m.role === 'admin')
  )

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xs font-semibold text-culpa-text-dim uppercase tracking-wider mb-3">
          Members ({members.length})
        </h3>
        <div className="space-y-2">
          {members.map((m) => (
            <div
              key={m.id}
              className="bg-culpa-surface border border-culpa-border rounded-xl px-4 py-3
                         flex items-center justify-between gap-3"
            >
              <div className="flex items-center gap-3 min-w-0">
                <Users size={14} className="text-culpa-text-dim shrink-0" />
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-culpa-text">{m.name || m.email}</span>
                    <RoleBadge role={m.role} />
                  </div>
                  {m.name && <div className="text-xs text-culpa-text-dim">{m.email}</div>}
                </div>
              </div>
              {isOwnerOrAdmin && m.role !== 'owner' && m.id !== user?.id && (
                <button
                  onClick={() => {
                    if (confirm(`Remove ${m.name || m.email} from the team?`))
                      removeMutation.mutate(m.id)
                  }}
                  className="p-2 rounded-lg text-culpa-text-dim hover:text-culpa-red hover:bg-culpa-red-dim transition-colors"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {isOwnerOrAdmin && (
        <div>
          <h3 className="text-xs font-semibold text-culpa-text-dim uppercase tracking-wider mb-3">
            Invite member
          </h3>
          <div className="flex items-center gap-2">
            <div className="flex-1 relative">
              <Mail size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-culpa-text-dim" />
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="colleague@company.com"
                className="w-full pl-9 pr-4 py-2 bg-culpa-bg border border-culpa-border rounded-lg
                           text-sm text-culpa-text placeholder:text-culpa-text-dim
                           focus:outline-none focus:ring-2 focus:ring-culpa-red/30 focus:border-culpa-red/50"
                onKeyDown={(e) => e.key === 'Enter' && inviteEmail && inviteMutation.mutate()}
              />
            </div>
            <button
              onClick={() => inviteMutation.mutate()}
              disabled={inviteMutation.isPending || !inviteEmail}
              className="px-3 py-2 bg-culpa-red hover:bg-culpa-red/80 text-white text-sm font-medium
                         rounded-lg transition-colors disabled:opacity-50 whitespace-nowrap"
            >
              Send invite
            </button>
          </div>
        </div>
      )}

      {invites.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-culpa-text-dim uppercase tracking-wider mb-3">
            Pending invites
          </h3>
          <div className="space-y-2">
            {invites.map((inv) => (
              <div
                key={inv.id}
                className="bg-culpa-surface border border-culpa-border border-dashed rounded-xl px-4 py-3
                           flex items-center justify-between"
              >
                <div className="flex items-center gap-2 text-sm text-culpa-text-dim">
                  <Mail size={14} /> {inv.email}
                </div>
                <span className="text-xs text-culpa-text-dim">
                  {new Date(inv.created_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function Team() {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const { data: teamsData, isLoading } = useQuery({
    queryKey: ['teams'],
    queryFn: () => api.teams.list(),
  })

  const teams = (teamsData?.teams || []) as Array<{ id: string; name: string; role: string }>
  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null)
  const activeTeamId = selectedTeamId || (teams.length > 0 ? teams[0].id : null)

  const isPro = user?.plan === 'pro'

  return (
    <div className="min-h-screen bg-culpa-bg">
      <div className="border-b border-culpa-border bg-culpa-surface">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <div className="flex items-center gap-3">
            <Link to="/" className="text-culpa-text-dim hover:text-culpa-text transition-colors">
              <ArrowLeft size={16} />
            </Link>
            <div>
              <h1 className="text-sm font-semibold text-culpa-text">Team</h1>
              <p className="text-xs text-culpa-text-dim">{user?.email}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-8">
        {!isPro && (
          <div className="mb-8 bg-culpa-orange-dim border border-culpa-orange/30 rounded-xl px-5 py-4">
            <p className="text-sm font-medium text-culpa-text">Team features require a Pro plan.</p>
            <p className="text-xs text-culpa-text-dim mt-1">
              <Link to="/settings/billing" className="text-culpa-orange hover:underline">Upgrade to Pro</Link> to create teams and share sessions.
            </p>
          </div>
        )}

        {isPro && (
          <>
            {teams.length === 0 && (
              <div className="mb-8">
                <h2 className="text-xs font-semibold text-culpa-text-dim uppercase tracking-wider mb-3">
                  Create a team
                </h2>
                <CreateTeamForm onCreated={() => queryClient.invalidateQueries({ queryKey: ['teams'] })} />
              </div>
            )}

            {teams.length > 1 && (
              <div className="flex items-center gap-1 p-1 bg-culpa-surface border border-culpa-border rounded-lg mb-6">
                {teams.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setSelectedTeamId(t.id)}
                    className={cn(
                      'px-3 py-1 rounded text-xs font-medium transition-colors',
                      activeTeamId === t.id
                        ? 'bg-culpa-muted text-culpa-text'
                        : 'text-culpa-text-dim hover:text-culpa-text',
                    )}
                  >
                    {t.name}
                  </button>
                ))}
              </div>
            )}

            {teams.length > 0 && activeTeamId && (
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-culpa-text">
                  {teams.find((t) => t.id === activeTeamId)?.name}
                </h2>
              </div>
            )}

            {activeTeamId && <TeamDetail teamId={activeTeamId} />}

            {teams.length > 0 && (
              <div className="mt-10 pt-6 border-t border-culpa-border">
                <h2 className="text-xs font-semibold text-culpa-text-dim uppercase tracking-wider mb-3">
                  Create another team
                </h2>
                <CreateTeamForm onCreated={() => queryClient.invalidateQueries({ queryKey: ['teams'] })} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
